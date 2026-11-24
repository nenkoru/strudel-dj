"""Compare lead instruments by laying only the transcribed melody over the original bars.

    uv run python leadmix.py out/<name>.json sax_vib gm_tenor_sax gm_shakuhachi ...

Needs <name>.loop.json and <name>.orig.wav from ab.py. Writes <name>.<lead>.overorig.wav per
instrument and <name>.leads-ab.wav: the original alone, then each instrument over it, in the
order given, with a second of silence between sections.
"""
import json
import subprocess
import sys
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

from ab import ROOT, track_sound

SR = 44100


def main(info_path, leads):
    info_path = Path(info_path)
    info = json.loads(info_path.read_text())
    base = info_path.with_suffix('')
    loop = json.loads(info_path.with_suffix('.loop.json').read_text())
    if 'lead' not in loop['roles']:
        raise SystemExit('this loop has no lead lane')
    rows = []
    for lead in leads:
        code = track_sound(loop['code'], loop['roles'], False, lead=lead)
        line = [l.strip().rstrip(',') for l in code.split('\n') if 'note(' in l and lead in l][0]
        rows.append({'id': lead, 'code': line, 'tempo': info['tempo']})
    tmp = base.parent / f'{base.name}.leads.jsonl'
    tmp.write_text(''.join(json.dumps(r) + '\n' for r in rows))
    rdir = base.parent / f'{base.name}.leads.render'
    out = subprocess.run(['node', str(ROOT / 'js/render.mjs'), str(tmp), str(rdir)], capture_output=True, text=True)
    for line in out.stdout.splitlines():
        r = json.loads(line)
        print(r['id'], 'ok' if r.get('ok') else r.get('error'), 'failed notes', r.get('failed'))

    orig, _ = librosa.load(base.parent / f'{base.name}.orig.wav', sr=SR, mono=False)
    orig = 0.7 * orig / (np.abs(orig).max() + 1e-9)
    gap = np.zeros((2, SR))
    sections = [orig, gap]
    for lead in leads:
        y, _ = librosa.load(rdir / f'{lead}.wav', sr=SR, mono=False)
        y = np.vstack([y, y]) if y.ndim == 1 else y
        n = min(orig.shape[1], y.shape[1])
        mix = orig[:, :n] + 0.45 * y[:, :n] / (np.abs(y).max() + 1e-9)
        mix /= max(1.0, np.abs(mix).max() / 0.98)
        sf.write(base.parent / f'{base.name}.{lead}.overorig.wav', mix.T, SR)
        sections += [mix, gap]
    sf.write(base.parent / f'{base.name}.leads-ab.wav', np.concatenate(sections, axis=1).T, SR)
    print('order: original,', ', '.join(leads))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
