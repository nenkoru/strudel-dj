"""Evaluate a local MLX model (optionally with a LoRA adapter) on held-out captions.

    uv run python eval_local.py --model mlx-community/Qwen2.5-Coder-0.5B-Instruct-bf16 \
        --adapter adapters/qwen-coder-0.5b --n 60
Same metrics as baseline.py, plus generation speed. Writes data/eval/<name>.jsonl.
"""
import argparse
import json
import random
import time
from pathlib import Path

from mlx_lm import generate, load
from mlx_lm.sample_utils import make_sampler

from evalkit import SYSTEM_SHORT, clean, lane_roles, metrics, prompt, query, summarize

ap = argparse.ArgumentParser()
ap.add_argument('--model', required=True)
ap.add_argument('--adapter')
ap.add_argument('--n', type=int, default=60)
ap.add_argument('--temperature', type=float, default=0.7)
ap.add_argument('--name')
ap.add_argument('--vlm', action='store_true', help='load through mlx-vlm (LFM3)')
args = ap.parse_args()

rows = [json.loads(l) for l in open('data/strudel.jsonl')]
test = random.Random(0).sample([r for r in rows if r['test']], args.n)  # n=30 is baseline.py's sample

if args.vlm:  # LFM3: the released mlx-lm cannot load it yet (ml-explore/mlx-lm#2016), mlx-vlm can
    import mlx_vlm
    from mlx_vlm.prompt_utils import apply_chat_template
    model, proc = mlx_vlm.load(args.model, adapter_path=args.adapter)
    tok = getattr(proc, 'tokenizer', proc)

    def run(msgs):
        text = apply_chat_template(proc, model.config, msgs, num_images=0)
        out = mlx_vlm.generate(model, proc, text, max_tokens=1500, temperature=args.temperature, top_p=0.95, verbose=False)
        return getattr(out, 'text', out)
else:
    model, tok = load(args.model, adapter_path=args.adapter)
    sampler = make_sampler(temp=args.temperature, top_p=0.95)

    def run(msgs):
        text = tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
        return generate(model, tok, text, max_tokens=1500, sampler=sampler)

gens = []
for row in test:
    msgs = [{'role': 'system', 'content': SYSTEM_SHORT}, {'role': 'user', 'content': prompt(row)}]
    t = time.time()
    raw = run(msgs)
    sec = time.time() - t
    gens.append({'id': row['id'], 'raw': raw, 'code': clean(raw), 'sec': round(sec, 2),
                 'tokens': len(tok.encode(raw))})

gen_q = query(gens)
by_id = {r['id']: r for r in test}
name = args.name or Path(args.adapter or args.model).name
out = Path('data/eval'); out.mkdir(parents=True, exist_ok=True)
ms = []
with open(out / f'{name}.jsonl', 'w') as f:
    for g in gens:
        m = metrics(by_id[g['id']], gen_q[g['id']]); ms.append(m)
        f.write(json.dumps({**g, 'metrics': m, 'roles': lane_roles(g['code'])}, ensure_ascii=False) + '\n')
secs = sorted(g['sec'] for g in gens)
tps = sum(g['tokens'] for g in gens) / sum(g['sec'] for g in gens)
print(name, summarize(ms), f'median_sec {secs[len(secs) // 2]} tok/s {tps:.0f}')
errors = [m['error'] for m in ms if not m['valid']]
for e in sorted(set(errors))[:8]:
    print('  invalid:', errors.count(e), e)
