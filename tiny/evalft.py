"""Did the genre fine-tune help? Compares base models (tiny/<name>.safetensors, v2, BPE) on the GPU:

- loss on held-out text: the genre programs and lines (packed alone by ft.sh as ev-genre-pieces and
  ev-genre-lines: their valid split is the fine-tune corpus's) and the general pretraining data (baseB),
  where a fine-tune that forgot would get worse
- programs sampled for house, techno and progressive headers: how many end on their own, have balanced
  brackets, how many parts, and the share of pitched notes in the header's key (natural scale)
- one-part lines for the rating page's prompts (role key style level [section] [on words]>): the share
  that come out as a pattern (a bracketed mini of 20+ characters), with a section word and without (the
  first fine-tunes mostly answered an empty line when one was there)

Writes eval-<name>.json and ft-samples-<name>.txt (the programs, for checking with the page's dialect on
the Mac: node deckc/checkft.mjs).

    venv/bin/python tiny/evalft.py base130 base130ft
"""
import json
import random
import re
import sys

import numpy as np
import torch
import torch.nn.functional as F
from safetensors.torch import load_file
from tokenizers import Tokenizer

from train_torch import HERE, TinyLMv2

D = HERE / 'data'
PC = {'c': 0, 'd': 2, 'e': 4, 'f': 5, 'g': 7, 'a': 9, 'b': 11}
KEYS = ['c', 'c#', 'd', 'eb', 'e', 'f', 'f#', 'g', 'ab', 'a', 'bb', 'b']
STYLES = ['house', 'techno', 'prog']
DEV = 'cuda' if torch.cuda.is_available() else 'mps'
AMP = dict(device_type='cuda', dtype=torch.float16) if DEV == 'cuda' else dict(device_type='cpu', enabled=False)


def load(name):
    cfg = json.loads((HERE / f'{name}.json').read_text())
    m = TinyLMv2(cfg['vocab_size'], cfg['layers'], cfg['dim'], cfg['heads'], cfg['ctx'])
    m.load_state_dict(load_file(str(HERE / f'{name}.safetensors')))
    return m.to(DEV).eval(), cfg


@torch.no_grad()
def loss_on(model, path, ctx, windows=64, per=8):
    va = np.fromfile(path, np.uint16)
    s = np.random.default_rng(1).integers(0, len(va) - ctx - 1, windows)
    total = 0.0
    for i in range(0, windows, per):
        x = torch.from_numpy(np.stack([va[j:j + ctx] for j in s[i:i + per]]).astype(np.int64)).to(DEV)
        y = torch.from_numpy(np.stack([va[j + 1:j + ctx + 1] for j in s[i:i + per]]).astype(np.int64)).to(DEV)
        with torch.autocast(**AMP):
            logits = model(x)
        total += F.cross_entropy(logits.float().view(-1, logits.shape[-1]), y.view(-1)).item() * len(x)
    return total / windows


@torch.no_grad()
def sample(model, tok, prompts, ctx, temperature=0.9, top_k=40, max_new=1600):
    ids = [tok.encode(p).ids for p in prompts]  # all the same length (main groups them): no padding
    done = [False] * len(ids)
    for _ in range(max_new):
        if all(done):
            break
        x = torch.tensor(ids, device=DEV)[:, -ctx:]
        with torch.autocast(**AMP):
            logits = model(x)[:, -1].float() / temperature
        v, _ = logits.topk(top_k)
        logits[logits < v[:, -1:]] = -1e9
        nxt = torch.multinomial(F.softmax(logits, -1), 1)[:, 0].tolist()
        for i, t in enumerate(nxt):  # finished rows keep growing (one tensor), their text is cut at the end mark
            ids[i].append(t)
            done[i] = done[i] or '\x1e' in tok.decode(ids[i][-3:])
    return [tok.decode(r) for r in ids], done


@torch.no_grad()
def sample_lines(model, tok, prompts, ctx, temperature=0.9, top_k=40, max_new=160):
    """The continuation of each prompt up to the end of its line (prompts of one token length)."""
    ids = [tok.encode('\n' + p).ids for p in prompts]
    start, done = len(ids[0]), [False] * len(ids)
    for _ in range(max_new):
        if all(done):
            break
        x = torch.tensor(ids, device=DEV)[:, -ctx:]
        with torch.autocast(**AMP):
            logits = model(x)[:, -1].float() / temperature
        v, _ = logits.topk(top_k)
        logits[logits < v[:, -1:]] = -1e9
        for i, t in enumerate(torch.multinomial(F.softmax(logits, -1), 1)[:, 0].tolist()):
            ids[i].append(t)
            done[i] = done[i] or '\n' in tok.decode(ids[i][start:])
    return [tok.decode(r[start:]).split('\n')[0] for r in ids]


def line_check(model, tok, ctx, rng):
    roles, levels = ['chords', 'bass', 'lead', 'drums'], ['lo', 'mid', 'hi']
    ons = ['', ' on kick low top', ' on kick top', ' on kick low mid top', ' on low mid']
    asks = []
    for i in range(64):
        role, sec = roles[i % 4], ['build', 'drop', 'break', 'groove'][i % 4] if i % 2 else None
        key = '' if role == 'drums' else f' {rng.choice(KEYS)} {rng.choice(["minor", "major"])}'
        asks.append((sec is not None, f'{role}{key} {STYLES[i % 3]} {rng.choice(levels)}{" " + sec if sec else ""}{rng.choice(ons)}>'))
    groups, ok = {}, {True: [0, 0], False: [0, 0]}
    for i, (_, p) in enumerate(asks):
        groups.setdefault(len(tok.encode('\n' + p).ids), []).append(i)
    for group in groups.values():
        outs = sample_lines(model, tok, [asks[i][1] for i in group], ctx)
        for i, out in zip(group, outs):
            ok[asks[i][0]][0] += len(out) >= 20 and ('[' in out or '<' in out)
            ok[asks[i][0]][1] += 1
    return {'with_section': round(ok[True][0] / ok[True][1], 2), 'without': round(ok[False][0] / ok[False][1], 2)}


def check(text, key, minor):
    body = text.split('\n', 1)[1] if '\n' in text else ''
    body = body.split('\x1e')[0]
    balanced = all(body.count(a) == body.count(b) for a, b in ('()', '[]', '<>')) and body.count('"') % 2 == 0
    parts = len(re.findall(r'// \w+', body))
    scale = {(KEYS.index(key) + s) % 12 for s in ((0, 2, 3, 5, 7, 8, 10) if minor else (0, 2, 4, 5, 7, 9, 11))}
    notes = [PC[n] + {'#': 1, 'b': -1}.get(acc, 0) for m in re.findall(r'note\("([^"]*)"\)', body)
             for n, acc in re.findall(r'(?<![a-z])([a-g])(#|b)?-?\d', m)]
    inkey = sum(n % 12 in scale for n in notes) / len(notes) if notes else None
    return dict(balanced=balanced, parts=parts, notes=len(notes), inkey=inkey)


def main(*names):
    tok = Tokenizer.from_file(str(HERE / 'tok4k.tokenizer.json'))
    rng = random.Random(0)
    asks = []
    for i in range(48):
        key, minor = rng.choice(KEYS), rng.random() < 0.75
        asks.append((key, minor, f'// key: {key} {"minor" if minor else "major"} | style: {STYLES[i % 3]} | bars: '
                     f'{rng.choice([4, 8, 8, 16])} | parts: {rng.choice([2, 3, 4, 5])}\n'))
    for name in names:
        model, cfg = load(name)
        res = {'name': name, 'step': cfg.get('step'), 'loss': {}}
        for ev in ('ev-genre-pieces', 'ev-genre-lines', 'baseB'):
            path = D / f'{ev}-valid.bin'
            if path.exists():
                res['loss'][ev] = round(loss_on(model, path, cfg['ctx']), 4)
        print(name, res['loss'], flush=True)
        texts, ended = [None] * len(asks), [None] * len(asks)
        groups = {}
        for i, a in enumerate(asks):
            groups.setdefault(len(tok.encode(a[2]).ids), []).append(i)
        for group in groups.values():
            for j in range(0, len(group), 16):
                part = group[j:j + 16]
                t, d = sample(model, tok, [asks[i][2] for i in part], cfg['ctx'])
                for i, ti, di in zip(part, t, d):
                    texts[i], ended[i] = ti, di
        checks = [check(t, k, mi) for t, (k, mi, _) in zip(texts, asks)]
        ink = [c['inkey'] for c in checks if c['inkey'] is not None]
        res['samples'] = {'n': len(texts), 'ended': sum(ended), 'balanced': sum(c['balanced'] for c in checks),
                          'parts': round(sum(c['parts'] for c in checks) / len(checks), 2),
                          'inkey': round(sum(ink) / max(1, len(ink)), 3)}
        print(name, res['samples'], flush=True)
        res['lines'] = line_check(model, tok, cfg['ctx'], random.Random(1))
        print(name, 'page-prompt lines', res['lines'], flush=True)
        (HERE.parent / f'eval-{name}.json').write_text(json.dumps(res, indent=1))
        (HERE.parent / f'ft-samples-{name}.txt').write_text(''.join(t.split('\x1e')[0].rstrip() + '\n\x1e\n' for t in texts))
        del model
        torch.cuda.empty_cache()


if __name__ == '__main__':
    main(*sys.argv[1:])
