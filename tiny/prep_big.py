"""The pretraining corpus for a bigger tiny model: every 4/4 MidiCaps file (all of Lakh MIDI with
captions, key and genre) cut into many 4-bar windows instead of one, plus the Groove MIDI drum
performances. One lane per line, in the same prompt format as the style corpus:

    bass f# minor edm mid><[f#2 ~ f#2 ...] ...>
    drums groove hi>[bd ~ ~ bd ...], ...

The level (lo / mid / hi) is the lane's onsets per bar against thresholds per role, so the prompt
carries density the way the page's energy does; up to two of the file's MidiCaps moods (dark, epic,
energetic, ...) follow on 70% of lines, so a free-text prompt mapped to these words can steer it.
Pitched lanes appear in their key and two random transpositions. MIDI files are read straight from
the archives (no 6 GB of extracted files). Writes tiny/data/big-{train,valid}.txt (valid = MidiCaps
test set + 2% of Groove).

With --hear, each lane also says what the other parts of the same window play, in the words the pages
take from a track's audio (deckc/hear.py): `on kick low mid top` (kick: a bass drum on most beats; low:
a bassline; mid: chords or a lead; top: hats, rides, cymbals), on 85% of lines, so a part learns to
fill what the track leaves open. Writes tiny/data/big-hear-{train,valid}.txt.

    uv run python tiny/prep_big.py data/raw/dl/midicaps.tar.gz data/raw/dl/groove.zip [--hear]
"""
import csv
import io
import random
import tarfile
import zipfile
from collections import defaultdict
import re
import sys
from multiprocessing import Pool
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
import mido  # noqa: E402
from convert import BARS, STEPS, assign_roles, lane_code, quantize, DRUMS  # noqa: E402
from prep import key_name, transpose  # noqa: E402

OUT = Path(__file__).parent / 'data'
MAXLEN = 400
WINDOWS = 12  # at most this many 4-bar windows per file, spread over the song
LEVELS = {'bass': (3, 7), 'lead': (3, 7), 'chords': (2, 5), 'drums': (6, 14)}  # onsets per bar: lo below a, hi from b
MOODS = ['melodic', 'happy', 'relaxing', 'dark', 'energetic', 'meditative', 'motivational', 'epic', 'space',
         'emotional', 'inspiring', 'dream', 'action', 'romantic', 'retro', 'uplifting']


try:
    import symusic  # C++ MIDI parser: mido spent 90% of the conversion time reading files
except ImportError:
    symusic = None


def read_notes(data):
    """convert.read_notes for MIDI bytes: (ticks_per_beat, notes, meter_ok)."""
    return read_notes_bpm(data)[:3]


def read_notes_bpm(data):
    """read_notes plus the first tempo in BPM (None when the file has none or mido reads it). With
    symusic a part is a track (drums on channel 9, the others numbered by track); with mido it is a
    (channel, program)."""
    if symusic is not None:
        sc = symusic.Score.from_midi(data)
        meter_ok = all((t.numerator, t.denominator) == (4, 4) for t in sc.time_signatures)
        notes = []
        for i, tr in enumerate(sc.tracks):
            ch = 9 if tr.is_drum else (i if i < 9 else i + 1)
            a = tr.notes.numpy()
            notes += [(int(t), int(t + d), int(p), ch, tr.program) for t, d, p in zip(a['time'], a['duration'], a['pitch'])]
        bpm = float(sc.tempos[0].qpm) if len(sc.tempos) else None
        return sc.ticks_per_quarter, notes, meter_ok, bpm
    mid = mido.MidiFile(file=io.BytesIO(data))
    notes, meter_ok = [], True
    for track in mid.tracks:
        t, program, on = 0, defaultdict(int), {}
        for msg in track:
            t += msg.time
            if msg.type == 'time_signature' and (msg.numerator, msg.denominator) != (4, 4):
                meter_ok = False
            elif msg.type == 'program_change':
                program[msg.channel] = msg.program
            elif msg.type == 'note_on' and msg.velocity > 0:
                on.setdefault((msg.channel, msg.note), []).append(t)
            elif msg.type in ('note_off', 'note_on'):
                starts = on.get((msg.channel, msg.note))
                if starts:
                    notes.append((starts.pop(0), t, msg.note, msg.channel, program[msg.channel]))
    return mid.ticks_per_beat, notes, meter_ok, None


def level(role, notes):
    per_bar = len({n['step'] for n in notes if role != 'drums' or DRUMS.get(n['pitch']) != 'bd'}) / BARS
    lo, hi = LEVELS[role]
    return 'lo' if per_bar < lo else 'mid' if per_bar < hi else 'hi'


def heard(roles, me):
    """What the other parts of a window play, as `on` words (empty when nothing counts)."""
    words = []
    drums = [DRUMS.get(n['pitch']) for n in roles.get('drums', [])] if me != 'drums' else []
    if drums.count('bd') >= 2 * BARS:
        words.append('kick')
    if me != 'bass' and 'bass' in roles:
        words.append('low')
    if any(r in roles for r in ('chords', 'lead') if r != me):
        words.append('mid')
    if sum(d in ('hh', 'oh', 'rd', 'cr') for d in drums) >= 2 * BARS:
        words.append('top')
    return ' '.join(words)


def windows(data, seed, drums_only=False, min_parts=2, parsed=None):
    """[(role, level, mini, heard)] from up to WINDOWS non-overlapping 4-bar windows with 2+ parts."""
    tpb, notes, meter_ok = parsed or read_notes(data)
    if not meter_ok or not notes:
        return []
    q = quantize(notes, tpb)
    last = max(n['step'] for n in q) // STEPS
    starts = list(range(0, max(1, last - BARS + 1), BARS))
    random.Random(seed).shuffle(starts)
    out = []
    for b in starts:
        if len(out) >= WINDOWS * 3:
            break
        start, end = b * STEPS, (b + BARS) * STEPS
        win = [n for n in q if start <= n['step'] < end and (n['ch'] == 9 and n['pitch'] in DRUMS or n['ch'] != 9)]
        roles = assign_roles(win)
        if drums_only:
            roles = {k: v for k, v in roles.items() if k == 'drums'}
        elif len(roles) < min_parts:
            continue
        for role, ns in roles.items():
            code = lane_code(role, ns, start)
            m = code and re.match(r'(?:note|s)\("([^"]*)"\)', code)
            if m and len(m[1]) <= MAXLEN:
                out.append((role, level(role, ns), m[1], heard(roles, role)))
    return out


def midicaps_job(args):
    name, data, (key, style, test, moods), hear = args
    try:
        lanes = windows(data, name)
    except Exception:  # corrupt MIDI in Lakh is common
        return test, []
    rng, lines = random.Random(name), []
    for role, lv, mini, on in lanes:
        tags = f' {lv}' + (''.join(' ' + m for m in moods) if rng.random() < 0.7 else '')
        if hear and on and rng.random() < 0.85:
            tags += ' on ' + on
        if role == 'drums':
            lines.append(f'drums {style}{tags}>{mini}')
            continue
        for k in [0] + ([] if test else rng.sample([-5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6], 2)):
            try:
                lines.append(f'{role} {key_name(key, k)} {style}{tags}>{transpose(mini, k)}')
            except ValueError:
                pass
    return test, lines


def groove_job(args):
    name, data, test = args
    try:
        return test, [f'drums groove {lv}>{mini}' for role, lv, mini, on in windows(data, name, drums_only=True)]
    except Exception:
        return test, []


def midicaps_files(tar, meta, hear):
    with tarfile.open(tar, 'r|gz') as tf:  # one sequential pass, nothing extracted
        for m in tf:
            if m.isfile() and m.name in meta:
                yield m.name, tf.extractfile(m).read(), meta[m.name], hear


def main(lmd_tar, groove_zip, hear=False):
    caps = pd.read_parquet(ROOT / 'data' / 'raw' / 'midicaps.parquet')
    meta = {}
    for r in caps.itertuples():
        if not isinstance(r.key, str) or r.time_signature != '4/4' or r.key.split()[-1] not in ('major', 'minor'):
            continue
        style = 'edm' if 'electronic' in list(r.genre) else 'any'
        moods = [m for m in r.mood if m in MOODS][:2]
        meta[r.location] = (r.key, style, bool(r.test_set), moods)
    with zipfile.ZipFile(groove_zip) as z:
        rows = list(csv.DictReader(io.TextIOWrapper(z.open('groove/info.csv'))))
        gjobs = [(r['midi_filename'], z.read('groove/' + r['midi_filename']), random.Random(r['midi_filename']).random() < 0.02)
                 for r in rows if r['time_signature'] == '4-4']
    print(len(meta), 'MidiCaps files,', len(gjobs), 'Groove files', flush=True)
    seen, split = set(), {False: [], True: []}
    def keep(results):
        for test, lines in results:
            for ln in lines:
                if ln not in seen:
                    seen.add(ln); split[test].append(ln)

    with Pool(10) as pool:
        # batches: Pool.imap would pull the whole archive into memory ahead of the workers
        batch, done = [], 0
        for item in midicaps_files(lmd_tar, meta, hear):
            batch.append(item)
            if len(batch) == 2000:
                keep(pool.imap_unordered(midicaps_job, batch, chunksize=32)); done += len(batch); batch = []
                print(done, len(split[False]), len(split[True]), flush=True)
        keep(pool.imap_unordered(midicaps_job, batch, chunksize=32))
        keep(pool.imap_unordered(groove_job, gjobs, chunksize=16))
    random.seed(0)
    for test, name in ((False, 'train'), (True, 'valid')):
        random.shuffle(split[test])
        (OUT / f'big{"-hear" if hear else ""}-{name}.txt').write_text('\n'.join(split[test]) + '\n')
        print(name, len(split[test]), 'lines', sum(map(len, split[test])) // 1000000, 'M chars')


if __name__ == '__main__':
    main(*sys.argv[1:3], hear='--hear' in sys.argv)
