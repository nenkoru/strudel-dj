"""Even levels for a swipe batch: every part rendered offline (js/render.mjs, 8 bars through superdough
with the page's kit), its loudness measured (BS.1770 integrated, pyloudnorm), and a gain `norm` stored on
the part that brings it to its role's level; the rating page multiplies it in (deckc/rate/index.html).

The owner heard the level jump from part to part. Measured on the batch of 2026-11-07 (400 parts): median
-24.3 LUFS, 10th to 90th percentile -34.7 to -18.2, voices from vowelpad at -44.8 to fmbell at -12. The
tracks are already levelled (mine.py's `trim`). The targets keep the batch's median where the owner rated
it and give a role its place under the track: leading parts a little above it, beds below. Corrections
are clamped to +-12 dB; a part that renders silent is dropped from the batch.

    uv run --with pyloudnorm --with soundfile --with numpy python deckc/loudness.py [deckc/mine/batch.json]
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pyloudnorm as pyln
import soundfile as sf

HERE = Path(__file__).parent
TARGET = {'lead': -21, 'solo': -21, 'acid': -21, 'bass': -21, 'seq': -22, 'chords': -23, 'stab': -23, 'arp': -23,
          'drums': -23, 'gate': -23, 'fill': -24, 'pad': -26, 'drone': -26, 'vox': -25}
MAX_DB = 12


def main(path=HERE / 'mine' / 'batch.json'):
    doc = json.loads(Path(path).read_text())
    bpm = {t['id']: t['bpm'] for t in json.loads((HERE / 'mine' / 'mine.json').read_text())['tracks']}
    tmp = Path(tempfile.mkdtemp(prefix='loud-'))
    kit = tmp / 'kit'
    kit.mkdir()
    (kit / 'strudel.json').write_text((HERE / 'site' / 'kit.json').read_text())
    for d in (HERE / 'site' / 'samples').iterdir():
        (kit / d.name).symlink_to(d.resolve())
    rows = []
    for it in doc['items']:
        for w in 'ab':
            code = it[w]['code']
            if 'chop' not in code and 'trackhat' not in code:  # cut from the playing track: no offline source
                rows.append({'id': f"{it['pairId']}{w}", 'code': code, 'tempo': bpm.get(it['track'], 124)})
    (tmp / 'parts.jsonl').write_text('\n'.join(json.dumps(r) for r in rows))
    subprocess.run(['node', 'render.mjs', str(tmp / 'parts.jsonl'), str(tmp / 'wav'), '--bars', '8', '--samples', str(kit),
                    '--jobs', '6'], cwd=HERE.parent / 'js', check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    meter, lufs = pyln.Meter(44100), {}
    for r in rows:
        f = tmp / 'wav' / f"{r['id']}.wav"
        if f.exists():
            y, _ = sf.read(f)
            lufs[r['id']] = meter.integrated_loudness(y)
    keep, dropped, moves = [], 0, []
    for it in doc['items']:
        ok = True
        for w in 'ab':
            l = lufs.get(f"{it['pairId']}{w}")
            if l is None:  # not rendered (a track cut): leave it as it is
                continue
            if not np.isfinite(l) or l < -60:
                ok = False
                continue
            db = float(np.clip(TARGET.get(it['role'], -23) - l, -MAX_DB, MAX_DB))
            it[w]['lufs'], it[w]['norm'] = round(l, 1), round(10 ** (db / 20), 3)
            moves.append(db)
        if ok:
            keep.append(it)
        else:
            dropped += 1
    doc['items'] = keep
    Path(path).write_text(json.dumps(doc))
    after = [it[w]['lufs'] + 20 * np.log10(it[w]['norm']) for it in keep for w in 'ab' if 'norm' in it[w]]
    print(f'{len(moves)} parts levelled (moves {np.percentile(moves, 10):+.1f} to {np.percentile(moves, 90):+.1f} dB), '
          f'{dropped} silent items dropped; after: p10 {np.percentile(after, 10):.1f}, p90 {np.percentile(after, 90):.1f} LUFS')


if __name__ == '__main__':
    main(*sys.argv[1:2])
