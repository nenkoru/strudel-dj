"""Recompute tempo and bar line of analysed tracks from their cached drum stems (no Demucs rerun)
and rewrite them in <name>.json. For grid fixes in track2midi.grid.

    uv run python regrid.py ../deckc/tracks/analysis/*.json [--keep-tempo]
"""
import json
import sys
from collections import Counter

import numpy as np

import track2midi as T

for path in [a for a in sys.argv[1:] if not a.startswith('--')]:
    if path.endswith('.loop.json'):
        continue
    info = json.load(open(path))
    hits = T.drum_hits(info['stems']['drums'])
    period, bar0 = T.grid(np.asarray(info['beats']), np.asarray(info['downbeats']), hits, info['tempo'] if '--keep-tempo' in sys.argv else None)
    kicks = T.kick_attacks(info['stems']['drums'])
    before = bar0
    bar0 = T.refine_phase(period, bar0, kicks)
    steps = {k: Counter(int(round((t - bar0) / (period / 4))) % 16 for t, kk in hits if kk == k) for k in (36, 38)}
    print(f"{info['name'][:32]:32} bpm {info['tempo']:.3f} -> {60 / period:.3f}  bar0 {info['bar0']:.4f} -> {bar0:.4f}",
          '| kicks', [s for s, _ in steps[36].most_common(4)], 'snares', [s for s, _ in steps[38].most_common(3)])
    print(f'    kick-attack phase correction {1000 * (bar0 - before):+.0f} ms from {len(kicks)} kicks')
    info['tempo'], info['bar0'], info['kicks'] = round(60 / period, 3), float(bar0), [round(float(k), 4) for k in kicks]
    json.dump(info, open(path, 'w'))
