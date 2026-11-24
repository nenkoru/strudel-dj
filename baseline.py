"""Zero/few-shot baseline: an OpenAI-compatible model writes loops for held-out captions.

    uv run python baseline.py --model qwen3.8-27b-auto --n 30 --shots 3
Writes data/baseline/<model>.jsonl (generations + metrics) and prints a summary next to the
reference loops' own metrics.
"""
import argparse
import json
import os
import random
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from evalkit import SYSTEM, clean, metrics, prompt, query, summarize, lane_roles

ap = argparse.ArgumentParser()
ap.add_argument('--model', default='qwen3.8-27b-auto')
ap.add_argument('--n', type=int, default=30)
ap.add_argument('--shots', type=int, default=3)
ap.add_argument('--temperature', type=float, default=0.7)
args = ap.parse_args()

rows = [json.loads(l) for l in open('data/strudel.jsonl')]
rnd = random.Random(0)
test = rnd.sample([r for r in rows if r['test']], args.n)
shots = rnd.sample([r for r in rows if not r['test'] and 400 <= len(r['code']) <= 700], args.shots)
fewshot = [m for s in shots for m in ({'role': 'user', 'content': prompt(s)}, {'role': 'assistant', 'content': s['code']})]


def generate(row):
    body = json.dumps({'model': args.model, 'temperature': args.temperature, 'max_tokens': 4000,
                       'messages': [{'role': 'system', 'content': SYSTEM}, *fewshot,
                                    {'role': 'user', 'content': prompt(row)}]}).encode()
    req = urllib.request.Request(os.environ['OPENAI_BASE_URL'].rstrip('/') + '/chat/completions', body,
                                 {'Content-Type': 'application/json',
                                  'Authorization': f"Bearer {os.environ.get('OPENAI_API_KEY', '')}"})
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=300) as res:
            raw = json.load(res)['choices'][0]['message']['content'] or ''
    except Exception as e:
        raw = f'ERROR {type(e).__name__}: {e}'
    return {'id': row['id'], 'raw': raw, 'code': clean(raw), 'sec': round(time.time() - t, 1)}


with ThreadPoolExecutor(6) as pool:
    gens = list(pool.map(generate, test))

gen_q, ref_q = query(gens), query(test)
by_id = {r['id']: r for r in test}
out = Path('data/baseline'); out.mkdir(parents=True, exist_ok=True)
gm, rm = [], []
with open(out / f'{args.model}.jsonl', 'w') as f:
    for g in gens:
        m = metrics(by_id[g['id']], gen_q[g['id']]); gm.append(m)
        rm.append(metrics(by_id[g['id']], ref_q[g['id']]))
        f.write(json.dumps({**g, 'metrics': m, 'roles': lane_roles(g['code'])}, ensure_ascii=False) + '\n')
print('model    ', args.model, summarize(gm), 'median_sec', sorted(g['sec'] for g in gens)[len(gens) // 2])
print('reference', summarize(rm))
errors = [m['error'] for m in gm if not m['valid']]
for e in sorted(set(errors))[:8]:
    print('  invalid:', errors.count(e), e)
