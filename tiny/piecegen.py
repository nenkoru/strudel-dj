"""Generate whole Strudel programs ("pieces") with a base model on the server GPU, for a list of
key/style headers, and slice each into its role parts. Appends one JSON line per program to an
out.jsonl pool that the Mac-side batch composer reads later. Resumable: skips needs already done.

Torch/evalft/tokenizers are imported only on the CLI path, so `import piecegen` works without CUDA.
The GPU is chosen by the caller, not in code (evalft uses 'cuda'):

    CUDA_VISIBLE_DEVICES=1 nice -n 19 taskset -c 0-9 venv/bin/python tiny/piecegen.py base130ft3 needs.json pool-ft3.jsonl

(run from ~/strudel-lm/tiny, like serve.py, so `from evalft import ...` resolves)
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

LANE = re.compile(r'^\s*(note|s)\("([^"]*)"\)((?:\.[A-Za-z_]+\([^()]*\))*)\s*,?\s*//\s*(\w+)\s*$')
SOUND = re.compile(r'\.s\("([^"]*)"\)')
BANK = re.compile(r'\.bank\("([^"]*)"\)')
BPM = re.compile(r'setcps\((\d+(?:\.\d+)?)/60/4\)')


def _balanced(mini):
    return mini.count('[') == mini.count(']') and mini.count('<') == mini.count('>')


def parts_of(text):
    """Role lanes of a piece: one dict per `note("MINI")`/`s("MINI")` line carrying a `// ROLE`.
    Only text before the first '\x1e' is considered; lanes with unbalanced []/<> or an empty /
    ~-only MINI are skipped. Order of appearance is kept."""
    out = []
    for line in text.split('\x1e')[0].split('\n'):
        m = LANE.match(line)
        if not m:
            continue
        kind, mini, chain, role = m.groups()
        if not _balanced(mini):
            continue
        if mini.replace('~', '').strip() == '':
            continue
        sm, bm = SOUND.search(chain), BANK.search(chain)
        sound = sm.group(1) if sm else (bm.group(1) if bm else None)
        out.append({'role': role, 'kind': kind, 'mini': mini, 'sound': sound})
    return out


def header(key, mode, style, bars=4, parts=4):
    return f'// key: {key} {mode} | style: {style} | bars: {bars} | parts: {parts}\n'


def bpm_of(text):
    m = BPM.search(text)
    return float(m.group(1)) if m else None


def cut(text):
    """A sampled program: cut at the first '\x1e' and drop the header line."""
    body = text.split('\x1e')[0]
    if '\n' in body:
        body = body.split('\n', 1)[1]
    return body


def LastHead(head):
    """The output head on the last position only: sampling needs no other logits, and B x T x 4096 of them
    (330 MB at a batch of 8) did not fit next to the owner's LLM (about 1.3 GB free per GPU)."""
    import torch

    class Last(torch.nn.Module):
        def __init__(self, h):
            super().__init__()
            self.h = h

        def forward(self, x):
            return self.h(x[:, -1:])
    return Last(head)


def read_needs(path):
    return json.loads(Path(path).read_text())


def done_counts(path):
    counts = {}
    p = Path(path)
    if not p.exists():
        return counts
    for line in p.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            k = (r['key'], r['mode'], r['style'])
            counts[k] = counts.get(k, 0) + 1
    return counts


def gen_need(model, tok, ctx, need, args, temps, parts_list, done, f):
    from evalft import sample
    key, mode, style = need['key'], need['mode'], need['style']
    n0 = done.get((key, mode, style), 0)
    remaining = args.per - n0
    if remaining <= 0:
        return
    prompts = [header(key, mode, style, args.bars, parts_list[i % len(parts_list)])
               for i in range(n0, n0 + remaining)]
    groups = {}
    for i, p in enumerate(prompts):
        groups.setdefault(len(tok.encode(p).ids), []).append(i)
    batch_no = written = 0
    for group in groups.values():
        for j in range(0, len(group), args.batch):
            part = group[j:j + args.batch]
            temp = temps[batch_no % len(temps)]
            batch_no += 1
            t0 = time.time()
            t, d = sample(model, tok, [prompts[i] for i in part], ctx, temperature=temp, max_new=args.max_new)
            parts_sum = 0
            for i, ti, di in zip(part, t, d):
                body = cut(ti)
                parts = parts_of(body)
                parts_sum += len(parts)
                rec = {'model': args.model, 'key': key, 'mode': mode, 'style': style,
                       'bars': args.bars, 'temperature': temp, 'ended': di, 'bpm': bpm_of(body),
                       'text': body, 'parts': parts,
                       'id': f'{args.model}-{key}{mode[0]}-{style}-{n0 + i}'}
                f.write(json.dumps(rec) + '\n')
            f.flush()
            written += len(part)
            print(f'{key} {mode} {style}: {n0 + written}/{args.per} {time.time() - t0:.1f}s '
                  f'{parts_sum / len(part):.1f} parts', flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Generate Strudel pieces into a JSONL pool.')
    ap.add_argument('model')
    ap.add_argument('needs')
    ap.add_argument('out')
    ap.add_argument('--per', type=int, default=48)
    ap.add_argument('--batch', type=int, default=16)
    ap.add_argument('--temps', default='0.9,1.0')
    ap.add_argument('--bars', type=int, default=4)
    ap.add_argument('--parts', default='3,4')
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--half', action='store_true', help='fp16 weights (for a GPU with ~1 GB free)')
    ap.add_argument('--max-new', type=int, default=1000, help='tokens per program at most (4-bar pieces take 300-600)')
    args = ap.parse_args(argv)

    from tokenizers import Tokenizer
    from train_torch import HERE
    import torch
    from evalft import load
    torch.manual_seed(args.seed)
    temps = [float(x) for x in args.temps.split(',')]
    parts_list = [int(x) for x in args.parts.split(',')]
    needs = read_needs(args.needs)
    done = done_counts(args.out)

    tok = Tokenizer.from_file(str(HERE / 'tok4k.tokenizer.json'))
    model, cfg = load(args.model)
    model.head = LastHead(model.head)
    if args.half:  # fp16 weights: half the memory; autocast runs the matmuls in fp16 anyway
        model.half()
    with open(args.out, 'a') as f:
        for need in needs:
            gen_need(model, tok, cfg['ctx'], need, args, temps, parts_list, done, f)


if __name__ == '__main__':
    main()
