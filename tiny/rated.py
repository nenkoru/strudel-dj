"""Rated parts -> training lines: every part rated "good" on the rating page (ratings exported from the
artifact's db as JSON files), as `prompt>mini` in the model's own notation, written to
tiny/data/rated-good.txt and mixed into tiny/data/style-rated.txt (style corpus + rated lines x20).

    python tiny/rated.py <dir of rating JSON files>
"""
import glob
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
KIT = {'tight_hat': 'hh', 'open_hat': 'oh', 'clap': 'cp', 'tom': 'lt', 'ride': 'rd'}  # page kit -> model names
VOCAB = set("\n #*,-0123456789<>@[]abcdefghijlmnoprstuy~")

rows = [json.load(open(f)) for f in glob.glob(sys.argv[1] + '/*.json')]
good = []
for r in (r.get('data', r) for r in rows):
    if r['verdict'] != 'good':
        continue
    mini = r['mini']
    if r['role'] == 'drums':
        for k, v in KIT.items():
            mini = mini.replace(k, v)
    if not set(r['prompt'] + mini) - VOCAB:
        good.append(r['prompt'] + mini)
(HERE / 'data' / 'rated-good.txt').write_text('\n'.join(good) + '\n')
style = (HERE / 'data' / 'style.txt').read_text().splitlines()
(HERE / 'data' / 'style-rated.txt').write_text('\n'.join(style + good * 20) + '\n')
print(len(rows), 'ratings,', len(good), 'good lines')
