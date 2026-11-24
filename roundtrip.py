"""Check that converted Strudel code reproduces the MIDI window it came from.

    node js/query.mjs < data/strudel.jsonl > data/strudel.events.jsonl
    uv run python roundtrip.py data/strudel.jsonl data/strudel.events.jsonl

Compares (lane, 16th step, pitch-or-drum) onset sets, so it measures the encoder and the
parser, not the grid: off-grid timing in the source is reported separately as `offgrid`.
"""
import json
import sys
from statistics import mean

from convert import DRUMS, STEPS


def ref_set(row):
    lane = {r: i for i, r in enumerate(row['roles'])}
    return {(lane[e['role']], e['step'], DRUMS[e['pitch']] if e['role'] == 'drums' else e['pitch'])
            for e in row['ref']}


def code_set(events):
    return {(e['lane'], round(e['begin'] * STEPS), e['s'] if e['midi'] is None else e['midi']) for e in events}


def main(rows_path, events_path):
    rows = {r['id']: r for r in map(json.loads, open(rows_path))}
    f1s, bad, offgrid = [], [], []
    for ev in map(json.loads, open(events_path)):
        row = rows[ev['id']]
        offgrid.append(mean(e['err'] > 0.25 for e in row['ref']))
        if not ev['ok']:
            bad.append((ev['id'], ev['error'])); continue
        a, b = ref_set(row), code_set(ev['events'])
        tp = len(a & b)
        f1 = 2 * tp / (len(a) + len(b)) if a or b else 1.0
        f1s.append(f1)
        if f1 < 0.999:
            bad.append((ev['id'], f'f1={f1:.3f} missing={sorted(a - b)[:3]} extra={sorted(b - a)[:3]}'))
    print(f'rows={len(f1s) + sum(1 for _, e in bad if not e.startswith("f1"))} parsed={len(f1s)} '
          f'mean_f1={mean(f1s):.4f} exact={sum(f > 0.999 for f in f1s)} '
          f'offgrid_notes={mean(offgrid):.3f}')
    for b in bad[:10]:
        print('  ', *b)


if __name__ == '__main__':
    main(*sys.argv[1:3])
