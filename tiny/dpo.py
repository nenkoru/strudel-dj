"""Preference fine-tuning (DPO) on pairs of drafts for the same prompt: the model is pushed to give the
chosen draft more probability than the rejected one, relative to where it started (a frozen copy), so
it learns from what lost as well as from what won. A little plain next-character loss on the
fine-tune corpus keeps it from drifting off the music it knows.

Pairs come from the rating page (A/B, exported from the artifact's "pairs" collection as JSON files,
one per row) and/or from the critic (`node tiny/critic.mjs pairs ...`: best vs worst of 8 drafts).

    uv run python tiny/dpo.py bigrest2 --out bigdpo --page ratings-pairs/ [--pairs work/cpairs.jsonl] [--steps 300]
"""
import argparse
import glob
import json
import random
from pathlib import Path

import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
import numpy as np

from train import HERE, TinyLM


def page_pairs(folder):
    """Rows exported from the rating page -> {prompt, chosen, rejected}: A/B picks ('both' and 'none' say
    nothing about order), and swiped twins (the two parts of one moment) that one rater gave different
    verdicts. A swipe repeated to measure noise, or one rater checking another's, counts once."""
    out, twins = [], {}
    for f in glob.glob(f'{folder}/*.json'):
        r = json.load(open(f))
        r = r.get('data', r)
        if r.get('winner') in ('a', 'b'):
            w, l = (r['a'], r['b']) if r['winner'] == 'a' else (r['b'], r['a'])
            if w['draft'] != l['draft']:
                out.append({'prompt': r['prompt'], 'chosen': w['draft'], 'rejected': l['draft'], 'source': 'page'})
        elif r.get('mode') == 'swipe' and not r.get('repeatOf') and not r.get('crossOf') and r.get('verdict') in ('good', 'bad'):
            twins.setdefault((r.get('rater'), r['pairId']), {})[r['slot']] = r  # one person's verdicts on both twins
    for t in twins.values():
        if len(t) == 2 and t['a']['verdict'] != t['b']['verdict']:
            w, l = (t['a'], t['b']) if t['a']['verdict'] == 'good' else (t['b'], t['a'])
            out.append({'prompt': w['prompt'], 'chosen': w['draft'], 'rejected': l['draft'], 'source': 'swipe'})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('init', help='the model to start from (and the frozen reference)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--page', help='folder of pairs exported from the rating page')
    ap.add_argument('--pairs', nargs='*', default=[], help='JSONL files of {prompt, chosen, rejected}')
    ap.add_argument('--page-weight', type=int, default=3, help='times each page pair repeats (a person outranks the critic)')
    ap.add_argument('--anchor', default='rest2', help='tiny/data/<anchor>-train.txt for the next-character loss')
    # cautious defaults: beta 0.1, 0.2 anchor and 9 passes over critic pairs drove the held-out loss to
    # 0.002 and broke the notation; one pass, a stiffer beta and an equal anchor keep it in its lane
    ap.add_argument('--anchor-weight', type=float, default=1.0)
    ap.add_argument('--beta', type=float, default=0.3)
    ap.add_argument('--steps', type=int, default=0, help='0 = one pass over the training pairs')
    ap.add_argument('--batch', type=int, default=16)
    ap.add_argument('--lr', type=float, default=1e-5)
    args = ap.parse_args()

    cfg = json.loads((HERE / f'{args.init}.json').read_text())
    vocab, T = cfg['vocab'], cfg['ctx']
    idx = {c: i for i, c in enumerate(vocab)}
    page = page_pairs(args.page) if args.page else []
    rows = page * args.page_weight + [json.loads(l) for f in args.pairs for l in open(f)]
    rows = [r for r in rows if set(r['prompt'] + r['chosen'] + r['rejected']) <= set(vocab)
            and len(r['prompt']) + max(len(r['chosen']), len(r['rejected'])) + 2 <= T]
    rng = random.Random(0)
    rng.shuffle(rows)
    hold = max(1, len(rows) // 10)
    valid, train = rows[:hold], rows[hold:]
    print(f'{len(page)} page pairs (x{args.page_weight}), {len(rows)} usable rows: {len(train)} train, {len(valid)} held out', flush=True)

    def encode(batch):
        """Each row twice (chosen, rejected): ids '\\n' + prompt + draft + '\\n', and a mask over the draft's targets."""
        seqs, starts = [], []
        for r in batch:
            for d in (r['chosen'], r['rejected']):
                s = '\n' + r['prompt'] + d + '\n'
                seqs.append([idx[c] for c in s]); starts.append(len(r['prompt']))  # target index of the draft's first char
        L = max(map(len, seqs))
        x = np.full((len(seqs), L), idx['\n'], np.int32); m = np.zeros((len(seqs), L - 1), np.float32)
        for i, (s, st) in enumerate(zip(seqs, starts)):
            x[i, :len(s)] = s; m[i, st:len(s) - 1] = 1
        return mx.array(x), mx.array(m)

    def seq_logp(model, x, m):
        logits = model(x[:, :-1])
        lp = logits - mx.logsumexp(logits, axis=-1, keepdims=True)
        tok = mx.take_along_axis(lp, x[:, 1:, None], axis=-1)[..., 0]
        return (tok * m).sum(axis=1)

    model, ref = (TinyLM(len(vocab), cfg['layers'], cfg['dim'], cfg['heads'], T) for _ in range(2))
    for mdl in (model, ref):
        mdl.load_weights(str(HERE / f'{args.init}.safetensors'))
    ref.freeze()

    anchor = (HERE / 'data' / f'{args.anchor}-train.txt').read_text()[:20_000_000]
    lut = np.zeros(256, np.int32); lut[[ord(c) for c in vocab]] = np.arange(len(vocab))
    anchor = lut[np.frombuffer(anchor.encode('ascii'), np.uint8)]
    arng = np.random.default_rng(0)

    def anchor_batch():
        s = arng.integers(0, len(anchor) - T - 1, 8)
        return mx.array(np.stack([anchor[i:i + T + 1] for i in s]))

    def loss_fn(mdl, x, m, ref_lp, a):
        lp = seq_logp(mdl, x, m)
        margin = (lp[0::2] - ref_lp[0::2]) - (lp[1::2] - ref_lp[1::2])
        dpo = -nn.log_sigmoid(args.beta * margin).mean()
        ce = nn.losses.cross_entropy(mdl(a[:, :-1]), a[:, 1:], reduction='mean')
        return dpo + args.anchor_weight * ce, (dpo, ce, (margin > 0).astype(mx.float32).mean())

    def accuracy(mdl, data):
        """Share of pairs where the model prefers the chosen draft more than the reference does."""
        hits = []
        for i in range(0, len(data), 32):
            x, m = encode(data[i:i + 32])
            lp, rl = seq_logp(mdl, x, m), seq_logp(ref, x, m)
            hits += (((lp[0::2] - rl[0::2]) - (lp[1::2] - rl[1::2])) > 0).tolist()
        return sum(hits) / max(1, len(hits))

    def raw_pref(mdl, data):
        """Share of pairs where the model itself gives the chosen draft more probability per character."""
        hits = []
        for i in range(0, len(data), 32):
            x, m = encode(data[i:i + 32])
            lp, n = seq_logp(mdl, x, m), m.sum(axis=1)
            hits += ((lp[0::2] / n[0::2]) > (lp[1::2] / n[1::2])).tolist()
        return sum(hits) / max(1, len(hits))

    args.steps = args.steps or max(1, len(train) // args.batch)
    print(f'start: held-out chosen preferred per char {raw_pref(model, valid):.2f}; {args.steps} steps', flush=True)
    opt = optim.AdamW(learning_rate=args.lr, weight_decay=0.0)
    grad_fn = nn.value_and_grad(model, loss_fn)
    for step in range(1, args.steps + 1):
        batch = [train[(step * args.batch + j) % len(train)] for j in range(args.batch)]
        x, m = encode(batch)
        ref_lp = mx.stop_gradient(seq_logp(ref, x, m))
        (loss, (dpo, ce, acc)), g = grad_fn(model, x, m, ref_lp, anchor_batch())
        g, _ = optim.clip_grad_norm(g, 1.0)
        opt.update(model, g)
        mx.eval(model.parameters(), opt.state)
        if step % 50 == 0 or step == args.steps:
            print(f'step {step}  dpo {dpo.item():.3f}  ce {ce.item():.3f}  train acc {acc.item():.2f}  held-out acc {accuracy(model, valid):.2f}', flush=True)
    print(f'end: held-out chosen preferred per char {raw_pref(model, valid):.2f}', flush=True)
    model.save_weights(str(HERE / f'{args.out}.safetensors'))
    (HERE / f'{args.out}.json').write_text(json.dumps({**cfg, 'dpo': {'from': args.init, 'pairs': len(rows), 'page': len(page), 'beta': args.beta}}))


if __name__ == '__main__':
    main()
