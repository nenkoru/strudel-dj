"""Many drafts per prompt from a trained model, on the GPU with a KV cache, for the critic loop
(tiny/rest.sh): reads JSONL rows with a "prompt", writes them back with "drafts" (n per prompt).

    uv run python tiny/sample.py big-ft prompts.jsonl samples.jsonl [--n 8] [--temperature 0.9]
"""
import argparse
import json
import math
from pathlib import Path

import mlx.core as mx
import mlx.nn as nn

from train import HERE, TinyLM


def forward(model, x, cache, offset):
    """Logits of the last position for new tokens x, appending their keys and values to cache."""
    B, T = x.shape
    h = model.tok(x) + model.pos(mx.arange(offset, offset + T))
    mask = nn.MultiHeadAttention.create_additive_causal_mask(T).astype(h.dtype) if T > 1 else None
    for i, b in enumerate(model.blocks):
        q, k, v = mx.split(b.qkv(b.ln1(h)), 3, axis=-1)
        q, k, v = (t.reshape(B, T, b.heads, -1).transpose(0, 2, 1, 3) for t in (q, k, v))
        if cache[i] is not None:
            k, v = mx.concatenate([cache[i][0], k], axis=2), mx.concatenate([cache[i][1], v], axis=2)
        cache[i] = (k, v)
        D = h.shape[-1]
        a = mx.fast.scaled_dot_product_attention(q, k, v, scale=1 / math.sqrt(D // b.heads), mask=mask)
        h = h + b.proj(a.transpose(0, 2, 1, 3).reshape(B, T, D))
        h = h + b.down(nn.gelu_approx(b.up(b.ln2(h))))
    return model.tok.as_linear(model.ln(h[:, -1]))


def sample(model, vocab, prompt, n, temperature, top_k, ctx):
    idx = {c: i for i, c in enumerate(vocab)}
    ids = [idx['\n']] + [idx[c] for c in prompt]
    cache = [None] * len(model.blocks)
    logits = forward(model, mx.array([ids] * n), cache, 0)
    out, done = [[] for _ in range(n)], [False] * n
    for pos in range(len(ids), ctx):
        kth = mx.sort(logits, axis=-1)[:, -top_k][:, None]
        logits = mx.where(logits < kth, -1e9, logits / temperature)
        tok = mx.random.categorical(logits).tolist()
        for j, t in enumerate(tok):
            if not done[j]:
                if vocab[t] == '\n':
                    done[j] = True
                else:
                    out[j].append(vocab[t])
        if all(done):
            break
        logits = forward(model, mx.array(tok)[:, None], cache, pos)
    return [''.join(o) for o, d in zip(out, done) if d]  # unfinished drafts ran out of context


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('name')
    ap.add_argument('prompts')
    ap.add_argument('out')
    ap.add_argument('--n', type=int, default=8)
    ap.add_argument('--temperature', type=float, default=0.9)
    ap.add_argument('--top-k', type=int, default=12)
    args = ap.parse_args()
    cfg = json.loads((HERE / f'{args.name}.json').read_text())
    vocab = cfg['vocab']
    model = TinyLM(len(vocab), cfg['layers'], cfg['dim'], cfg['heads'], cfg['ctx'])
    model.load_weights(str(HERE / f'{args.name}.safetensors'))
    mx.random.seed(0)
    rows = [json.loads(line) for line in open(args.prompts)]
    with open(args.out, 'w') as f:
        for i, r in enumerate(rows):
            r['drafts'] = sample(model, vocab, r['prompt'], args.n, args.temperature, args.top_k, cfg['ctx'])
            f.write(json.dumps(r) + '\n')
            if i % 50 == 0:
                print(i, len(rows), flush=True)


if __name__ == '__main__':
    main()
