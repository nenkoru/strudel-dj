"""Pretraining lines from any MIDI collection, in the format of the Lakh corpus (tiny/prep_big.py --hear):
the same 4-bar windows, roles, levels and `on` words, the key estimated from the notes
(prep_extra.key_of), two random transpositions of pitched lanes, and the style `edm` for files a
collection tags as electronic, else `any`. For growing the corpus past Lakh (see README, "More data").

Reads .mid files straight from a .zip, a .tar.gz (a path, or an https URL read as a stream and never stored,
resuming after a dropped connection), or a folder, and keeps those a filter allows:

- pdmx: PDMX (CC BY 4.0, public-domain MuseScore scores): the subsets without a license conflict,
  de-duplicated and valid, via PDMX.csv next to the archive
- midicaps: Lakh through MidiCaps (data/raw/midicaps.parquet next to the archive, or in data/raw):
  style edm for the electronic genre, its captions and moods go into the pieces' headers
- jamendo: MTG-Jamendo dance tracks transcribed by tiny/audio2midi.py (a folder with meta.jsonl): the
  style from their tags (house, techno, prog, edm), drums left out (the band-onset transcription mixes
  claps with hats and drops kicks), the notes cleaned (clean_transcribed: basic-pitch's octave jumps in
  the bass, overtones and bleed in the other stem)
- loops: Freesound loops transcribed by tiny/loops2midi.py (a folder with meta.jsonl, as jamendo), each
  file one part, so windows with a single part are kept
- all: every file
- edm-solo: every file, styled `edm`, windows with a single part kept (chord-progression and loop
  collections such as WaivOps NRG-CP, where each file is one part)

Transpositions and the `on` coin are seeded by the lane's notes, not the file name, so the same part
found in two collections (they overlap: Discover, GigaMIDI and LAMD all hold Lakh) gives the same lines
and exact-line dedup when mixing drops it. Files whose quantised notes were already seen in this run are
skipped. Lines are written as they come (train.py samples random spans, so order does not matter), gzipped:
a collection like Discover gives far more text than fits in memory or on this disk uncompressed.
SHARD=k/n splits a collection between machines: each reads it all and converts the files whose name
hashes to k. Writes tiny/data/<name>-{train,valid}.txt.gz (valid = 2% of files), and with PIECES=1 also
tiny/data/<name>-pieces.txt.gz: the base model's general format (tiny/piece.py), whole programs of 4 to
16 bars with every part, separated by a \x1e line.

    uv run python tiny/prep_midi.py pdmx data/raw/dl/pdmx/mid.tar.gz pdmx
    uv run python tiny/prep_midi.py all https://huggingface.co/datasets/.../x.tar.gz discover
"""
import gzip
import json
import hashlib
import os
import random
import signal
import sys
import tarfile
import time
import zipfile
import urllib.request
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).parent
PIECES = os.environ.get('PIECES') == '1'
sys.path.insert(0, str(HERE))
from prep_big import windows, read_notes_bpm, quantize  # noqa: E402
from piece import pieces  # noqa: E402
from prep_extra import NAMES as KEY_NAMES, key_of  # noqa: E402
from prep import key_name, transpose  # noqa: E402


def pdmx_meta(archive):
    import pandas as pd
    d = pd.read_csv(Path(archive).parent / 'PDMX.csv', usecols=['mid', 'genres', 'subset:no_license_conflict', 'subset:deduplicated', 'subset:all_valid'])
    d = d[d['subset:no_license_conflict'] & d['subset:deduplicated'] & d['subset:all_valid']]
    return {m.lstrip('./'): {'style': 'edm' if 'electronic' in str(g) else 'any'} for m, g in zip(d.mid, d.genres)}


def jamendo_meta(folder):
    rows = (json.loads(l) for l in open(Path(folder) / 'meta.jsonl'))
    return {r['midi']: {'style': r['style'], 'nodrums': True} for r in rows}


def midicaps_meta(archive):
    import pandas as pd
    here = Path(archive).parent / 'midicaps.parquet'
    d = pd.read_parquet(here if here.exists() else HERE.parent / 'data' / 'raw' / 'midicaps.parquet',
                        columns=['location', 'caption', 'genre', 'mood'])
    return {loc: {'style': 'edm' if 'electronic' in list(g) else 'any', 'caption': cap, 'moods': list(m)[:2]}
            for loc, cap, g, m in zip(d.location, d.caption, d.genre, d.mood)}


def loopify(part, sixteenth):
    """A transcribed part as the loop it plays: dance tracks repeat a 2-bar cycle, the transcription's
    onsets wander from one repeat to the next. In each 8 bars, a note stays on a 16th of the cycle when
    that pitch sounds there in at least half the cycles that have notes, and it then sounds in all of
    them (at its median length)."""
    blocks = {}
    for n in part:
        st = round(n[0] / sixteenth)
        blocks.setdefault(st // 128, []).append((st // 32 % 4, st % 32, n))
    out = []
    for blk, items in blocks.items():
        cycles = sorted({c for c, _, _ in items})
        need = max(2, (len(cycles) + 1) // 2)
        at = {}
        for c, pos, n in items:
            at.setdefault((pos, n[2]), {})[c] = n
        for (pos, pitch), seen in at.items():
            if len(seen) >= need:
                length = sorted(n[1] - n[0] for n in seen.values())[len(seen) // 2]
                ch, prog = next(iter(seen.values()))[3:5]
                for c in cycles:
                    t = (blk * 128 + c * 32 + pos) * sixteenth
                    out.append((t, t + length, pitch, ch, prog))
    return sorted(out)


def clean_transcribed(notes, tpb):
    """audio2midi.py's notes made playable: the bass (program 38) folded into the octave around its
    median and kept to one note per 16th (basic-pitch jumped an octave on every few notes, and two onsets
    in one 16th became [a1,a2] chords); the other stem (81) kept between C3 and C6 (the C7s were
    overtones), to the key's scale, one note per pitch class and at most four per 16th (those nearest the
    stem's median: [f3,f4,f5] was one note and its overtones) and none shorter than half a 16th; then each
    part as the loop it repeats (loopify). The base model's loss on the raw transcriptions was 3.0 per token, 1.3 on real MIDI."""
    sixteenth = tpb // 4
    bass = [n for n in notes if n[4] == 38]
    other = [n for n in notes if n[4] == 81 and 48 <= n[2] <= 84 and n[1] - n[0] >= sixteenth // 2]
    if bass:
        mid = sorted(n[2] for n in bass)[len(bass) // 2]
        bass = [(a, b, p - 12 * round((p - mid) / 12), ch, pr) for a, b, p, ch, pr in bass]
        one = {}
        for n in sorted(bass, key=lambda n: n[0] - n[1]):  # the longest note of each 16th
            one.setdefault(round(n[0] / sixteenth), n)
        bass = sorted(one.values())
    key = key_of(bass + other)
    if key:
        root, mode = KEY_NAMES.index(key.split()[0]), key.split()[1]
        scale = {(root + i) % 12 for i in ((0, 2, 4, 5, 7, 9, 11) if mode == 'major' else (0, 2, 3, 5, 7, 8, 10))}
        other = [n for n in other if n[2] % 12 in scale]
    steps = {}
    mid = sorted(n[2] for n in other)[len(other) // 2] if other else 60
    for n in sorted(other, key=lambda n: (abs(n[2] - mid), n[0] - n[1])):  # nearest the stem's register first
        at = steps.setdefault(round(n[0] / sixteenth), [])
        if len(at) < 4 and all(m[2] % 12 != n[2] % 12 for m in at):  # an octave doubling is an overtone
            at.append(n)
    other = sorted(n for at in steps.values() for n in at)
    return loopify(bass, sixteenth) + loopify(other, sixteenth)


def job(args):
    name, data, info, min_parts = args
    style = info.get('style', 'any')
    signal.alarm(30)  # a pathological file (millions of events) once held a whole batch for 30 minutes
    try:
        tpb, notes, meter_ok, bpm = read_notes_bpm(data)
        if info.get('nodrums'):
            notes = clean_transcribed([n for n in notes if n[3] != 9], tpb)
        parsed = (tpb, notes, meter_ok)
        key = key_of(notes)
        lanes = windows(data, name, min_parts=min_parts, parsed=parsed)  # pitched lanes need the key (below); drums do not
        q = quantize(notes, tpb)
        sig = hashlib.blake2b(repr(sorted((n['step'], n['pitch']) for n in q)).encode(), digest_size=8).digest()
        docs = pieces(q, key, style, bpm, name, min_parts, info.get('caption'), info.get('moods', ())) \
            if PIECES and meter_ok else []
    except Exception:  # broken files are common in scraped collections; Timeout too
        return False, [], None, []
    finally:
        signal.alarm(0)
    lines = []
    for role, lv, mini, on in lanes:
        rng = random.Random(mini)
        tags = f' {style} {lv}' + (' on ' + on if on and rng.random() < 0.85 else '')
        if role == 'drums':
            lines.append(f'drums{tags}>{mini}')
            continue
        if not key:
            continue
        for k in [0] + rng.sample([-5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6], 2):
            try:
                lines.append(f'{role} {key_name(key, k)}{tags}>{transpose(mini, k)}')
            except ValueError:
                pass
    return random.Random(name).random() < 0.02, lines, sig, docs


class Timeout(Exception):
    pass


def _timeout(signum, frame):
    raise Timeout()


signal.signal(signal.SIGALRM, _timeout)


class Stream:
    """A file-like read of an https URL that reconnects with a Range header when the connection drops,
    including a clean close before the end (the server's Content-Length says where the end is)."""

    def __init__(self, url):
        self.url, self.pos, self.r, self.size = url, 0, None, None

    def read(self, n=-1):
        for attempt in range(30):
            try:
                if self.r is None:
                    req = urllib.request.Request(self.url, headers={'Range': f'bytes={self.pos}-'} if self.pos else {})
                    self.r = urllib.request.urlopen(req, timeout=120)
                    if self.size is None:
                        self.size = int(self.r.headers['Content-Length'])
                b = self.r.read(n)
                if not b and self.pos < self.size:
                    raise IOError('closed early')
                self.pos += len(b)
                return b
            except Exception as e:  # OSError, http.client.IncompleteRead, a closed socket
                print('reconnect at', self.pos, 'of', self.size, repr(e)[:80], flush=True)
                self.r = None
                time.sleep(min(60, 2 ** min(attempt, 6)))
        raise IOError('gave up on ' + self.url)


def files(source, meta):
    if source.startswith('https://'):
        tf = tarfile.open(fileobj=Stream(source), mode='r|gz')
    else:
        source = Path(source)
        if source.suffix == '.zip':
            with zipfile.ZipFile(source) as z:
                for n in z.namelist():
                    if n.lower().endswith(('.mid', '.midi')) and (meta is None or n in meta):
                        yield n, z.read(n), (meta or {}).get(n, {})
            return
        tf = None if source.is_dir() else tarfile.open(source, 'r|gz')
    if tf is None:
        for p in sorted(source.rglob('*.mid')):
            rel = str(p.relative_to(source))
            if meta is None or rel in meta:
                yield rel, p.read_bytes(), (meta or {}).get(rel, {})
        return
    with tf:  # one sequential pass, nothing extracted
        for m in tf:
            if m.isfile() and m.name.lower().endswith(('.mid', '.midi')) and (meta is None or m.name in meta):
                yield m.name, tf.extractfile(m).read(), (meta or {}).get(m.name, {})


def main(kind, source, name):
    meta = pdmx_meta(source) if kind == 'pdmx' else midicaps_meta(source) if kind == 'midicaps' \
        else jamendo_meta(source) if kind in ('jamendo', 'loops') else None
    out = {t: gzip.open(HERE / 'data' / f'{name}-{p}.txt.gz', 'wt', compresslevel=6) for t, p in ((False, 'train'), (True, 'valid'))}
    docs_out = gzip.open(HERE / 'data' / f'{name}-pieces.txt.gz', 'wt', compresslevel=6) if PIECES else None
    sigs, done, skipped, kept, chars, pchars = set(), 0, 0, 0, 0, 0
    with Pool(int(os.environ.get('PREP_WORKERS', 6))) as pool:  # 12 on the GPU server (16 cores)
        batch = []
        def flush():
            nonlocal skipped, kept, chars, pchars
            for test, lines, sig, docs in pool.imap_unordered(job, batch, chunksize=32):
                if sig is None or sig in sigs:
                    skipped += sig is not None
                    continue
                sigs.add(sig)
                lines = list(dict.fromkeys(lines))
                out[test].write(''.join(ln + '\n' for ln in lines))
                kept += 1; chars += sum(map(len, lines))
                if docs_out and docs:
                    docs_out.write(''.join(d + '\n\x1e\n' for d in docs)); pchars += sum(map(len, docs))
        solo = kind == 'edm-solo'
        one = solo or kind == 'loops' or 'drums-only' in source or 'groove' in source  # GigaMIDI's drums-only and Groove files, the loops: one part
        shard = os.environ.get('SHARD')  # k/n: this machine converts the files whose name hashes to k (of n)
        k, n = map(int, shard.split('/')) if shard else (0, 1)
        for name, data, info in files(source, meta):
            if n > 1 and int(hashlib.md5(name.encode()).hexdigest(), 16) % n != k:
                continue
            batch.append((name, data, {**info, 'style': 'edm'} if solo else info, 1 if one else 2))
            if len(batch) == 2000:
                flush(); done += len(batch); batch = []
                if done >= int(os.environ.get('PREP_LIMIT', 10 ** 9)):  # a sample (the tokenizer's)
                    break
                print(f'{done} files, {kept} kept, {skipped} duplicates, {chars // 1000000} M chars, '
                      f'{pchars // 1000000} M piece chars', flush=True)
        flush()
    for f in [*out.values(), docs_out]:
        if f:
            f.close()
    print(f'done: {done + len(batch)} files, {kept} kept, {skipped} duplicates, {chars // 1000000} M chars, '
          f'{pchars // 1000000} M piece chars')


if __name__ == '__main__':
    main(*sys.argv[1:4])
