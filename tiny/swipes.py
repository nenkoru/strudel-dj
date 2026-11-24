"""Lines the owner (and anyone rating with them) liked on the rating page, for fine-tuning: every swipe
or single rating marked "good" and every A/B winner, as `prompt>draft` (the draft as the model wrote
it, effect words included), from rows exported from the artifact's db (one JSON file per row).
Repeats and cross-checks count once. Writes tiny/data/swiped-good.txt.

    python3 tiny/swipes.py <dir of exported rows>
"""
import glob
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
good = []
for f in glob.glob(sys.argv[1] + '/*.json'):
    r = json.load(open(f))
    r = r.get('data', r)
    if r.get('repeatOf') or r.get('crossOf') or not r.get('prompt'):
        continue
    if r.get('verdict') == 'good' and r.get('draft'):
        good.append(r['prompt'] + r['draft'])
    elif r.get('winner') in ('a', 'b'):
        good.append(r['prompt'] + r[r['winner']]['draft'])
good = list(dict.fromkeys(g.replace('\n', '') for g in good))
(HERE / 'data' / 'swiped-good.txt').write_text('\n'.join(good) + '\n')
print(len(good), 'liked lines')
