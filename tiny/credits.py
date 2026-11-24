"""The Jamendo and Freesound parts of the training data with a credit and a licence on every item, for the
public dataset: their audio is under per-track / per-sound Creative Commons licences, so the corpus files
(no provenance) can't be published as they are.

Runs tiny/prep_midi.py's conversion (`job`, with PIECES=1) over the same MIDI folder again and keeps the
programs and lines that are in the corpus files that were trained on (`<prefix>-{pieces,train,valid}.txt.gz`),
each with the file it came from. Items under a NoDerivatives (or any other unlisted) licence are dropped.
Writes JSON lines {text, kind: program|line, split, source, credit, url, license}; prints how much of the
corpus it found again.

    python3 tiny/credits.py jamendo data/raw/dl/jamendo/midi tiny/data/jamendo-clean audio_licenses.txt out.jsonl
    python3 tiny/credits.py loops data/raw/dl/freesound/midi tiny/data/loops data/raw/dl/freesound/meta.jsonl out.jsonl

audio_licenses.txt is MTG-Jamendo's per-track list (github.com/MTG/mtg-jamendo-dataset, data/).
"""
import collections
import gzip
import json
import os
import re
import sys
from multiprocessing import Pool
from pathlib import Path

os.environ['PIECES'] = '1'  # prep_midi reads it at import
sys.path.insert(0, str(Path(__file__).parent))
import prep_midi  # noqa: E402

_read = prep_midi.read_notes_bpm
# The corpus files were made (2026-11-07) before prep_midi passed the tempo on: no setcps line, and the
# piece's random draws come out differently with one. Reproduce that (the Pool's forked workers inherit it).
prep_midi.read_notes_bpm = lambda data: (*_read(data)[:3], None)

SEP = '\n\x1e\n'
ALLOWED = {'publicdomain/zero', 'licenses/by', 'licenses/by-sa', 'licenses/by-nc', 'licenses/by-nc-sa'}


def family(url):  # 'http://creativecommons.org/licenses/by-nc-sa/3.0/de/' -> 'licenses/by-nc-sa'
    m = re.search(r'creativecommons\.org/((?:licenses|publicdomain)/[a-z+-]+)', url)
    return m.group(1) if m else url


def reference(prefix):
    with gzip.open(f'{prefix}-pieces.txt.gz', 'rt') as f:
        docs = {d for d in f.read().split(SEP) if d.strip()}
    lines = {}
    for split in ('train', 'valid'):
        with gzip.open(f'{prefix}-{split}.txt.gz', 'rt') as f:
            for ln in f.read().splitlines():
                lines.setdefault(ln, split)
    return docs, lines


def jamendo_credits(path):
    """MTG-Jamendo's audio_licenses.txt: blocks of `NN/ID.mp3`, `<title> by <artist> from Jamendo: <url>`,
    `Available under a ... license: <licence url>`."""
    out = {}
    for block in Path(path).read_text().split('\n\n'):
        ls = [x.strip() for x in block.strip().splitlines()]
        if len(ls) >= 3 and ls[0].endswith('.mp3'):
            out[ls[0]] = {'source': 'jamendo:' + ls[0].split('/')[-1][:-4], 'credit': ls[1],
                          'url': ls[1].rsplit(': ', 1)[-1], 'license': ls[2].rsplit(': ', 1)[-1]}
    return out


def freesound_credits(path):
    out = {}
    for row in map(json.loads, open(path)):
        url = f"https://freesound.org/s/{row['id']}/"
        out[row['file']] = {'source': f"freesound:{row['id']}", 'credit': f"{row['name']} by {row['author']} from Freesound: {url}",
                            'url': url, 'license': row['license']}
    return out


def main(kind, folder, prefix, credits_file, out):
    folder = Path(folder)
    meta = [json.loads(ln) for ln in open(folder / 'meta.jsonl')]
    credits = jamendo_credits(credits_file) if kind == 'jamendo' else freesound_credits(credits_file)
    info = {r['midi']: (r, credits.get(r['path'])) for r in meta}
    min_parts = 2 if kind == 'jamendo' else 1  # as prep_midi.main: loops are one part a file
    docs, lines = reference(prefix)
    names = [p.name for p in sorted(folder.rglob('*.mid')) if p.name in info]
    jobs = [(n, (folder / n).read_bytes(), {'style': info[n][0]['style'], 'nodrums': True}, min_parts) for n in names]
    seen_sig, found_docs, found_lines = set(), set(), set()
    dropped, kept, no_credit = collections.Counter(), collections.Counter(), 0
    with Pool(int(os.environ.get('PREP_WORKERS', 6))) as pool, open(out, 'w') as f:
        for name, (test, ls, sig, ds) in zip(names, pool.imap(prep_midi.job, jobs, chunksize=16)):
            if sig is None or sig in seen_sig:
                continue
            seen_sig.add(sig)
            items = [('program', d, 'train') for d in dict.fromkeys(ds) if d in docs and d not in found_docs]
            items += [('line', ln, lines[ln]) for ln in dict.fromkeys(ls) if ln in lines and ln not in found_lines]
            found_docs.update(d for k, d, _ in items if k == 'program')
            found_lines.update(ln for k, ln, _ in items if k == 'line')
            cred = info[name][1]
            if cred is None:
                no_credit += len(items)
                continue
            fam = family(cred['license'])
            if fam not in ALLOWED:
                dropped[fam] += len(items)
                continue
            for k, text, split in items:
                kept[k] += 1
                f.write(json.dumps({'text': text, 'kind': k, 'split': split, **cred}, ensure_ascii=False) + '\n')
    print(f'{kind}: {len(names)} files; corpus found again: programs {len(found_docs)}/{len(docs)}, '
          f'lines {len(found_lines)}/{len(lines)}')
    print(f'kept {dict(kept)}; dropped by licence {dict(dropped)}; without a credit {no_credit}')


if __name__ == '__main__':
    main(*sys.argv[1:6])
