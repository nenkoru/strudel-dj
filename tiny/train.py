"""A character-level transformer (about 5M parameters) trained from scratch on tiny/data, small
enough to ship inside the page (int8, ~5 MB) and run in plain JavaScript (tiny/export.py,
deckc/src/tiny.mjs). Lines are packed into a stream separated by '\\n'; generation starts
from '\\n' + prompt and stops at the next '\\n'.

    uv run python tiny/train.py [--steps 3000]
    uv run python tiny/train.py --data big --layers 8 --dim 320 --out big --steps 14000   # pretraining
"""
import argparse
import json
import math
import time
from functools import partial
from pathlib import Path

import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
import numpy as np

HERE = Path(__file__).parent
CFG = dict(layers=6, dim=256, heads=8, ctx=448)


class Block(nn.Module):
    def __init__(self, dim, heads):
        super().__init__()
        self.heads = heads
        self.ln1, self.ln2 = nn.LayerNorm(dim), nn.LayerNorm(dim)
        self.qkv, self.proj = nn.Linear(dim, 3 * dim), nn.Linear(dim, dim)
        self.up, self.down = nn.Linear(dim, 4 * dim), nn.Linear(4 * dim, dim)

    def __call__(self, x, mask):
        B, T, D = x.shape
        q, k, v = mx.split(self.qkv(self.ln1(x)), 3, axis=-1)
        q, k, v = (t.reshape(B, T, self.heads, -1).transpose(0, 2, 1, 3) for t in (q, k, v))
        a = mx.fast.scaled_dot_product_attention(q, k, v, scale=1 / math.sqrt(D // self.heads), mask=mask)
        x = x + self.proj(a.transpose(0, 2, 1, 3).reshape(B, T, D))
        return x + self.down(nn.gelu_approx(self.up(self.ln2(x))))


class TinyLM(nn.Module):
    def __init__(self, vocab, layers, dim, heads, ctx):
        super().__init__()
        self.tok, self.pos = nn.Embedding(vocab, dim), nn.Embedding(ctx, dim)
        self.blocks = [Block(dim, heads) for _ in range(layers)]
        self.ln = nn.LayerNorm(dim)

    def __call__(self, ids):
        T = ids.shape[1]
        x = self.tok(ids) + self.pos(mx.arange(T))
        mask = nn.MultiHeadAttention.create_additive_causal_mask(T).astype(x.dtype)
        for b in self.blocks:
            x = b(x, mask)
        return self.tok.as_linear(self.ln(x))  # output head tied to the embedding


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--steps', type=int, default=3000)
    ap.add_argument('--batch', type=int, default=64)
    ap.add_argument('--resume', action='store_true', help='start from tiny.safetensors (weights only)')
    ap.add_argument('--extra', help='more lines (tiny/data/style.txt); 1000 held out for validation')
    ap.add_argument('--extra-weight', type=int, default=2, help='times the extra lines repeat in training')
    ap.add_argument('--data', default='', help="corpus prefix: '' = data/{train,valid}.txt, 'big' = data/big-*.txt")
    ap.add_argument('--out', default='tiny', help='weights and config name: tiny/<out>.safetensors, .json')
    ap.add_argument('--init', help='start from these weights (a name in tiny/) instead of --out')
    ap.add_argument('--layers', type=int, default=CFG['layers'])
    ap.add_argument('--dim', type=int, default=CFG['dim'])
    ap.add_argument('--lr', type=float, default=1e-3)
    ap.add_argument('--muon', type=float, default=0, help="Muon's learning rate for the blocks' weight matrices (AdamW keeps the rest); 0 = AdamW only")
    ap.add_argument('--bf16', action='store_true', help='weights and activations in bfloat16 (faster on Apple GPUs); the loss in float32')
    args = ap.parse_args()
    CFG.update(layers=args.layers, dim=args.dim)
    pre = args.data + '-' if args.data else ''
    train = (HERE / 'data' / f'{pre}train.txt').read_text()
    valid = (HERE / 'data' / f'{pre}valid.txt').read_text()[:2_000_000]
    if args.extra:
        # MidiCaps stays in the mix (general music), the extra lines repeat to weigh in
        extra = Path(args.extra).read_text().splitlines()
        lines = train.splitlines() + extra[1000:] * args.extra_weight
        np.random.default_rng(2).shuffle(lines)
        train = '\n'.join(lines) + '\n'
        valid = valid + '\n'.join(extra[:1000]) + '\n'
    vocab = sorted(set(train) | set(valid))
    if args.init:  # fine-tuning: the pretrained model's vocabulary, lines with other characters dropped
        cfg0 = json.loads((HERE / f'{args.init}.json').read_text())
        CFG.update({k: cfg0[k] for k in ('layers', 'dim', 'heads', 'ctx')})
        known = set(cfg0['vocab'])
        keep = lambda text: '\n'.join(ln for ln in text.split('\n') if set(ln) <= known) + '\n'
        train, valid, vocab = keep(train), keep(valid), cfg0['vocab']
    lut = np.zeros(256, np.uint8)  # uint8 ids: the 1.2 GB corpus stays 1.2 GB in memory  # chars -> ids in numpy: a Python loop over 300M chars takes minutes
    lut[[ord(c) for c in vocab]] = np.arange(len(vocab))
    tr = lut[np.frombuffer(train.encode('ascii'), np.uint8)]
    va = lut[np.frombuffer(valid.encode('ascii'), np.uint8)]
    del train
    T = CFG['ctx']
    model = TinyLM(len(vocab), **CFG)
    if args.resume or args.init:
        model.load_weights(str(HERE / f'{args.init or args.out}.safetensors'))
    if args.bf16:
        model.set_dtype(mx.bfloat16)
    mx.eval(model.parameters())
    n = sum(v.size for _, v in nn.utils.tree_flatten(model.parameters()))
    print(f'vocab {len(vocab)}  params {n / 1e6:.2f}M  train {len(tr) / 1e6:.1f}M chars', flush=True)
    sched = optim.join_schedules([optim.linear_schedule(1e-5, args.lr, 200), optim.cosine_decay(args.lr, max(1, args.steps - 200), 1e-5)], [200])
    opt = optim.AdamW(learning_rate=sched, weight_decay=0.05)
    if args.muon:  # Muon (the nanoGPT speedruns' optimizer) on the 2-D weights inside the blocks; embeddings, norms, biases stay on AdamW
        msched = optim.join_schedules([optim.linear_schedule(args.muon * 0.01, args.muon, 200),
                                       optim.cosine_decay(args.muon, max(1, args.steps - 200), args.muon * 0.01)], [200])
        hidden = lambda path, w: path.startswith('blocks') and path.endswith('weight') and w.ndim == 2
        opt = optim.MultiOptimizer([optim.Muon(learning_rate=msched, weight_decay=0.0), opt], [hidden])

    def loss_fn(m, x, y):
        return nn.losses.cross_entropy(m(x).astype(mx.float32), y, reduction='mean')

    grad_fn = nn.value_and_grad(model, loss_fn)
    state = [model.state, opt.state]

    @partial(mx.compile, inputs=state, outputs=state)
    def step_fn(x, y):
        loss, g = grad_fn(model, x, y)
        g, _ = optim.clip_grad_norm(g, 1.0)
        opt.update(model, g)
        return loss

    def batch(data, rng):
        s = rng.integers(0, len(data) - T - 1, args.batch)
        x = np.stack([data[i:i + T] for i in s]); y = np.stack([data[i + 1:i + T + 1] for i in s])
        return mx.array(x.astype(np.int32)), mx.array(y.astype(np.int32))

    rng, vrng = np.random.default_rng(0), np.random.default_rng(1)
    vbatches = [batch(va, vrng) for _ in range(8)]
    t0, best = time.time(), 9.0
    for step in range(1, args.steps + 1):
        x, y = batch(tr, rng)
        loss = step_fn(x, y)
        mx.eval(state, loss)
        if step == 20:
            print(f'20 steps in {time.time() - t0:.1f}s', flush=True)
        if step % 100 == 0 or step == args.steps:
            vl = sum(loss_fn(model, vx, vy).item() for vx, vy in vbatches) / len(vbatches)
            print(f'step {step}  train {loss.item():.3f}  valid {vl:.3f}  {time.time() - t0:.0f}s', flush=True)
            if vl < best:
                best = vl
                model.save_weights(str(HERE / f'{args.out}.safetensors'))
                (HERE / f'{args.out}.json').write_text(json.dumps({**CFG, 'vocab': ''.join(vocab), 'valid_loss': round(vl, 4), 'step': step}))


if __name__ == '__main__':
    main()
