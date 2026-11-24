"""tiny/train.py for NVIDIA cards (the owner's two V100 32 GB), in PyTorch: the same model with the same
weight names, so a checkpoint goes back and forth with MLX and through tiny/export.py unchanged; the
same schedule, AdamW and Muon. What differs is for the size of the corpus and the cards:

- `pack` turns any number of lines files (.txt or .txt.gz, each repeated --weight times) into one
  file of uint8 ids, read through a memory map: 10-20 B characters never sit in memory as text.
- fp16 autocast with a loss scaler (V100 has no bfloat16), weights and optimiser state in float32.
- one process per card with torchrun (DistributedDataParallel); --accum splits a batch into smaller
  ones when another program (the owner's LLM) holds most of a card's memory.

    python tiny/train_torch.py pack --out data/corpus --vocab tiny/big24.json data/big-hear-train.txt ...
    torchrun --nproc_per_node 2 tiny/train_torch.py train --bin data/corpus --layers 12 --dim 576 \\
        --muon 0.02 --steps 20000 --out big50
"""
import argparse
import gzip
import json
import math
import os
import time
import zlib
from pathlib import Path

import numpy as np
import torch
import torch.distributed as dist
import torch.nn as nn
import torch.nn.functional as F

HERE = Path(__file__).parent
CFG = dict(layers=6, dim=256, heads=8, ctx=448)
ATTN = None  # --flash: flash_attn_legacy.flash_attention (FlashAttention-2 for V100, github.com/sirCamp/flash-attention-legacy)


class Block(nn.Module):
    def __init__(self, dim, heads):
        super().__init__()
        self.heads = heads
        self.ln1, self.ln2 = nn.LayerNorm(dim), nn.LayerNorm(dim)
        self.qkv, self.proj = nn.Linear(dim, 3 * dim), nn.Linear(dim, dim)
        self.up, self.down = nn.Linear(dim, 4 * dim), nn.Linear(4 * dim, dim)

    def forward(self, x):
        B, T, D = x.shape
        q, k, v = (t.view(B, T, self.heads, -1).transpose(1, 2) for t in self.qkv(self.ln1(x)).split(D, dim=-1))
        a = ATTN(q, k, v, causal=True) if ATTN else F.scaled_dot_product_attention(q, k, v, is_causal=True)
        x = x + self.proj(a.transpose(1, 2).reshape(B, T, D))
        return x + self.down(F.gelu(self.up(self.ln2(x)), approximate='tanh'))  # MLX gelu_approx


class TinyLM(nn.Module):
    def __init__(self, vocab, layers, dim, heads, ctx):
        super().__init__()
        self.tok, self.pos = nn.Embedding(vocab, dim), nn.Embedding(ctx, dim)
        self.blocks = nn.ModuleList(Block(dim, heads) for _ in range(layers))
        self.ln = nn.LayerNorm(dim)
        # GPT-2's initialisation, not MLX's: with MLX's N(0, 1) embeddings the tied output head starts with
        # logits of std ~sqrt(dim) and a 50M model's loss went to 150 before it recovered
        for name, p in self.named_parameters():
            if name.endswith('bias'):
                nn.init.zeros_(p)
            elif p.ndim == 2:
                std = 0.02 / math.sqrt(2 * layers) if name.endswith(('proj.weight', 'down.weight')) else 0.02
                nn.init.normal_(p, std=std)

    def forward(self, ids):
        x = self.tok(ids) + self.pos(torch.arange(ids.shape[1], device=ids.device))
        for b in self.blocks:
            x = b(x)
        return self.ln(x) @ self.tok.weight.T  # output head tied to the embedding


def rope(x, cos, sin):
    a, b = x.chunk(2, dim=-1)
    return torch.cat((a * cos - b * sin, a * sin + b * cos), dim=-1)


class BlockV2(nn.Module):
    """A block with what the modded-nanogpt speedrun found trains faster: parameter-free RMS norms,
    rotary positions, RMS-normed queries and keys, a squared-ReLU MLP, zero-initialised output
    projections, a value embedding mixed into v (when the model hands one over) and a learned mix of
    the stream with the embedding x0."""

    def __init__(self, dim, heads, ve=False):
        super().__init__()
        self.heads = heads
        self.qkv, self.proj = nn.Linear(dim, 3 * dim, bias=False), nn.Linear(dim, dim, bias=False)
        self.up, self.down = nn.Linear(dim, 4 * dim, bias=False), nn.Linear(4 * dim, dim, bias=False)
        self.mix = nn.Parameter(torch.tensor([1.0, 0.0]))  # x <- mix0 * x + mix1 * x0
        self.vmix = nn.Parameter(torch.tensor(0.5)) if ve else None  # v <- (1 - vmix) * v + vmix * ve

    def forward(self, x, x0, ve, cos, sin):
        B, T, D = x.shape
        x = self.mix[0] * x + self.mix[1] * x0
        q, k, v = (t.view(B, T, self.heads, -1).transpose(1, 2) for t in self.qkv(F.rms_norm(x, (D,))).split(D, dim=-1))
        q, k = rope(F.rms_norm(q, (q.shape[-1],)), cos, sin), rope(F.rms_norm(k, (k.shape[-1],)), cos, sin)
        dt = v.dtype  # fp16 under autocast; the norms and the mix come out in float32
        if ve is not None:
            v = (1 - self.vmix) * v + self.vmix * ve.view(B, T, self.heads, -1).transpose(1, 2)
        q, k, v = q.to(dt), k.to(dt), v.to(dt)
        a = ATTN(q, k, v, causal=True) if ATTN else F.scaled_dot_product_attention(q, k, v, is_causal=True)
        x = x + self.proj(a.transpose(1, 2).reshape(B, T, D))
        # ReLU² scaled by 1/256 before the down projection and by 256 after it, in float32: on the V100
        # (fp16, no bf16) the down projection's output reached 28288 of fp16's 65504 by step 4000 and
        # passed it soon after (a 50M model went to nan twice). The same function, 256x the headroom.
        h = (F.relu(self.up(F.rms_norm(x, (D,)))) * (1 / 16)).square()
        return x + self.down(h).float() * 256


class TinyLMv2(nn.Module):
    """--arch v2: BlockV2 layers in a U-net (the first half's outputs are added back, weighted, into
    the second half in reverse), three value-embedding tables shared by the first and last three
    layers, and an untied output head with logits soft-capped at 15."""

    def __init__(self, vocab, layers, dim, heads, ctx):
        super().__init__()
        self.tok, self.head = nn.Embedding(vocab, dim), nn.Linear(dim, vocab, bias=False)
        self.ve = nn.ModuleList(nn.Embedding(vocab, dim) for _ in range(3))
        self.blocks = nn.ModuleList(BlockV2(dim, heads, ve=i < 3 or i >= layers - 3) for i in range(layers))
        self.skip = nn.Parameter(torch.ones(layers // 2))
        hd = dim // heads
        f = 1 / 10000 ** (torch.arange(0, hd // 2, dtype=torch.float32) / (hd // 2))
        ang = torch.outer(torch.arange(ctx, dtype=torch.float32), f)
        self.register_buffer('cos', ang.cos()[None, None], persistent=False)
        self.register_buffer('sin', ang.sin()[None, None], persistent=False)
        for name, p in self.named_parameters():
            if name.endswith(('proj.weight', 'down.weight')) or name == 'head.weight':
                nn.init.zeros_(p)
            elif name.endswith('qkv.weight') or name.endswith('up.weight'):
                nn.init.normal_(p, std=0.5 / math.sqrt(p.shape[1]))
            elif p.ndim == 2:  # embeddings
                nn.init.normal_(p, std=1.0)

    def forward(self, ids):
        T, L = ids.shape[1], len(self.blocks)
        x = x0 = F.rms_norm(self.tok(ids), (self.tok.embedding_dim,))
        ves = [e(ids) for e in self.ve]
        ve_at = {0: ves[0], 1: ves[1], 2: ves[2], L - 3: ves[0], L - 2: ves[1], L - 1: ves[2]}
        cos, sin, skips = self.cos[:, :, :T], self.sin[:, :, :T], []
        for i, b in enumerate(self.blocks):
            if i >= L - L // 2:
                x = x + self.skip[L - 1 - i] * skips.pop()
            x = b(x, x0, ve_at.get(i), cos, sin)
            if i < L // 2:
                skips.append(x)
        logits = self.head(F.rms_norm(x, (x.shape[-1],)))
        return 15 * torch.tanh(logits / 15)


def newton_schulz(g, steps=5):
    """The orthogonalisation inside Muon (Keller Jordan's quintic iteration), as MLX's optim.Muon does it."""
    a, b, c = 3.4445, -4.7750, 2.0315
    x = g.float()
    tall = x.shape[0] > x.shape[1]
    if tall:
        x = x.T
    x = x / (x.norm() + 1e-7)
    for _ in range(steps):
        A = x @ x.T
        x = a * x + (b * A + c * A @ A) @ x
    return x.T if tall else x


class Muon(torch.optim.Optimizer):
    """Muon for 2-D weight matrices: momentum (Nesterov, 0.95), then its orthogonalised direction,
    scaled by sqrt(max(1, rows / cols)) as in MLX."""

    def __init__(self, params, lr, momentum=0.95):
        super().__init__(params, dict(lr=lr, momentum=momentum))

    @torch.no_grad()
    def step(self):
        for group in self.param_groups:
            for p in group['params']:
                if p.grad is None:
                    continue
                buf = self.state[p].setdefault('buf', torch.zeros_like(p))
                buf.mul_(group['momentum']).add_(p.grad, alpha=1 - group['momentum'])
                g = p.grad.lerp(buf, group['momentum'])  # Nesterov
                u = newton_schulz(g)
                p.add_(u, alpha=-group['lr'] * max(1, p.shape[0] / p.shape[1]) ** 0.5)


def schedule(step, top, steps, floor, decay=-1.0):
    """MLX's join of a 200-step linear warm-up and a cosine decay to `floor`; with `decay` >= 0 instead
    warm-up, stable, then a linear decay over the last `decay` share of the steps (WSD: a stage that
    more data will continue keeps decay 0, the last stage decays)."""
    if step < 200:
        return floor + (top - floor) * step / 200
    if decay >= 0:
        start = steps * (1 - decay)
        return top if step < start else top + (floor - top) * (step - start) / max(1, steps - start)
    t = min(1.0, (step - 200) / max(1, steps - 200))
    return floor + (top - floor) * 0.5 * (1 + math.cos(math.pi * t))


def pack(args):
    """Text files (.txt or .txt.gz) -> <out>.bin, <out>-valid.bin, <out>.json. Two encodings:

    - --tokenizer NAME (tiny/NAME.tokenizer.json, tiny/tokenizer.py): BPE ids as uint16, the base model's
    - --vocab MODEL.json: one uint8 id per character, the old character models'

    A file named *pieces* holds documents (programs, tiny/piece.py) ended by a \\x1e line; any other file
    holds one document per line. Valid = the start of each file's first pass, up to 2 M ids in all.
    With --dedup, a file's first pass drops documents already seen in an earlier file or in --seen-in
    (the hashes an earlier stage saved with --seen-out), so collections that contain one another
    (Discover, GigaMIDI and LAMD all hold Lakh) count once; repeats from --weight are kept. The hashes
    are Python's own: run with PYTHONHASHSEED=0. A .gz still being written is read up to where it ends."""
    if args.dedup and os.environ.get('PYTHONHASHSEED') != '0':
        raise SystemExit('--dedup: run with PYTHONHASHSEED=0 so document hashes match across stages')
    if args.tokenizer:
        from tokenizers import Tokenizer
        tok = Tokenizer.from_file(str(HERE / f'{args.tokenizer}.tokenizer.json'))
        encode = lambda docs: np.fromiter((i for e in tok.encode_batch(docs) for i in e.ids), np.uint16)
        meta0 = {'tokenizer': args.tokenizer, 'vocab_size': tok.get_vocab_size(), 'dtype': 'uint16'}
    else:
        vocab = json.loads(Path(args.vocab).read_text())['vocab']
        lut = np.full(256, 255, np.uint8)
        lut[[ord(c) for c in vocab]] = np.arange(len(vocab))
        def encode(docs):
            ok = [d for d in docs if (lut[np.frombuffer(d.encode('latin-1', 'replace'), np.uint8)] != 255).all()]
            return lut[np.frombuffer(''.join(ok).encode('latin-1', 'replace'), np.uint8)] if ok else np.zeros(0, np.uint8)
        meta0 = {'vocab': vocab, 'dtype': 'uint8'}
    weights = [int(w) for w in (args.weight or '').split(',') if w] or [1] * len(args.files)
    seen = set(np.load(args.seen_in).tolist()) if args.seen_in else set()
    out = Path(args.out)
    tr, va, dups, vids, total = open(f'{out}.bin', 'wb'), [], 0, 0, 0

    def chunks(fh, sep):
        while True:
            try:
                chunk = fh.read(1 << 25)
                while chunk and not chunk.endswith(sep):
                    more = fh.readline()
                    if not more:
                        break
                    chunk += more
            except (EOFError, OSError, zlib.error):  # the end of a .gz that is still being written
                return
            if not chunk:
                return
            end = chunk.rfind(sep)
            if end < 0:
                return
            yield chunk[:end + len(sep)]

    for f, w in zip(args.files, weights):
        held = 0
        opener = gzip.open if f.endswith('.gz') else open
        sep = b'\n\x1e\n' if 'pieces' in Path(f).name else b'\n'
        for rep in range(w):
            with opener(f, 'rb') as fh:
                n = 0
                for chunk in chunks(fh, sep):
                    docs = [d + sep for d in chunk.split(sep)[:-1] if d.strip()]
                    if args.dedup and rep == 0:
                        keep = []
                        for d in docs:
                            h = hash(d)
                            if h in seen:
                                dups += 1
                            else:
                                seen.add(h); keep.append(d)
                        docs = keep
                    if not docs:
                        continue
                    ids = encode([d.decode('utf-8', 'replace') for d in docs])
                    if rep == 0 and n == 0 and vids < 2_000_000:  # the start of each file's first pass: validation
                        held = min(len(ids) // 200, 2_000_000 - vids)
                        va.append(ids[:held]); vids += held; ids = ids[held:]
                    elif n == 0:  # and never trained on in a repeat (exactly so without --dedup)
                        ids = ids[held:]
                    tr.write(ids.tobytes()); total += len(ids); n += 1
            print(f'{f} x{rep + 1}: {total / 1e9:.3f} B ids so far, {dups} duplicates', flush=True)
    tr.close()
    np.concatenate(va).tofile(f'{out}-valid.bin')
    if args.seen_out:
        np.save(args.seen_out, np.fromiter(seen, np.int64, len(seen)))
    Path(f'{out}.json').write_text(json.dumps({**meta0, 'train': total, 'valid': vids, 'files': args.files,
                                               'weights': weights, 'duplicates': dups}))
    print(f'packed {total / 1e9:.3f} B train ids, {vids / 1e6:.1f} M valid, {dups} duplicates')


def train(args):
    ddp = 'RANK' in os.environ
    if ddp:
        dist.init_process_group('nccl')
        rank, world = dist.get_rank(), dist.get_world_size()
        torch.cuda.set_device(int(os.environ['LOCAL_RANK']))
    else:
        rank, world = 0, 1
    dev = 'cuda' if torch.cuda.is_available() else 'mps' if torch.backends.mps.is_available() else 'cpu'
    meta = json.loads(Path(f'{args.bin}.json').read_text())
    dtype = np.dtype(meta.get('dtype', 'uint8'))
    vocab = meta.get('vocab') or meta['vocab_size']  # characters (old models) or the BPE vocabulary's size
    nvocab = vocab if isinstance(vocab, int) else len(vocab)
    CFG.update(layers=args.layers, dim=args.dim, heads=args.heads, ctx=args.ctx)
    if args.arch == 'v2':
        CFG['arch'] = 'v2'
    if args.init:
        cfg0 = json.loads((HERE / f'{args.init}.json').read_text())
        CFG.update({k: cfg0[k] for k in ('layers', 'dim', 'heads', 'ctx', 'arch') if k in cfg0})
        assert cfg0.get('tokenizer') == meta.get('tokenizer') and (meta.get('tokenizer') or cfg0['vocab'] == ''.join(vocab)), \
            'packed with another vocabulary'
    if args.flash:
        global ATTN
        from flash_attn_legacy import flash_attention as ATTN
    tr = np.memmap(f'{args.bin}.bin', dtype, mode='r')
    va = np.fromfile(f'{args.bin}-valid.bin', dtype)
    T = CFG['ctx']
    torch.manual_seed(0)
    arch = CFG.pop('arch', 'gpt2')
    model = (TinyLMv2 if arch == 'v2' else TinyLM)(nvocab, **CFG).to(dev)
    if arch == 'v2':
        CFG['arch'] = 'v2'
    if args.init:
        from safetensors.torch import load_file
        model.load_state_dict({k: v for k, v in load_file(str(HERE / f'{args.init}.safetensors')).items()})
    raw = model
    if ddp:
        model = nn.parallel.DistributedDataParallel(model, device_ids=[torch.cuda.current_device()])
    if args.compile:
        model = torch.compile(model, mode=args.compile_mode)
    n = sum(p.numel() for p in raw.parameters())
    if rank == 0:
        print(f'vocab {nvocab}  params {n / 1e6:.2f}M  train {len(tr) / 1e9:.2f} B ids  ctx {T}  cards {world}', flush=True)
    hidden = [p for name, p in raw.named_parameters() if name.startswith('blocks') and name.endswith('weight') and p.ndim == 2]
    rest = [p for name, p in raw.named_parameters() if not (name.startswith('blocks') and name.endswith('weight') and p.ndim == 2)]
    embeds = [p for name, p in raw.named_parameters() if name.startswith(('tok.', 've.'))]
    others = [p for p in (rest if args.muon else list(raw.parameters())) if all(p is not e for e in embeds)]
    groups = [dict(params=others, lr=args.lr, top=args.lr)]
    if args.embed_lr:  # embeddings on their own (higher) rate, as in the speedrun
        groups.append(dict(params=embeds, lr=args.embed_lr, top=args.embed_lr))
    else:
        groups[0]['params'] = others + embeds
    adam = torch.optim.AdamW(groups, weight_decay=0.05, eps=1e-8)
    muon = Muon(hidden, lr=args.muon) if args.muon else None
    scaler = torch.amp.GradScaler(enabled=dev == 'cuda')
    amp = dict(device_type='cuda', dtype=torch.float16) if dev == 'cuda' else dict(device_type=dev, enabled=False)

    def batch(data, rng, size):
        s = rng.integers(0, len(data) - T - 1, size)
        x = np.stack([data[i:i + T] for i in s]).astype(np.int64)
        y = np.stack([data[i + 1:i + T + 1] for i in s]).astype(np.int64)
        return torch.from_numpy(x).to(dev, non_blocking=True), torch.from_numpy(y).to(dev, non_blocking=True)

    def loss_of(m, x, y):
        with torch.autocast(**amp):
            logits = m(x)
        return F.cross_entropy(logits.float().view(-1, logits.shape[-1]), y.view(-1))

    rng, vrng = np.random.default_rng(1000 + rank), np.random.default_rng(1)
    per = args.batch // world // args.accum  # one card's micro-batch; the global batch stays --batch
    vbatches = [batch(va, vrng, per) for _ in range(8 * max(1, args.batch // per // 8))]  # in micro-batches: no memory spike
    t0, best = time.time(), 9.0
    for step in range(1, args.steps + 1):
        for g in adam.param_groups:
            g['lr'] = schedule(step - 1, g['top'], args.steps, g['top'] * 0.01, args.decay)
        if muon:
            for g in muon.param_groups:
                g['lr'] = schedule(step - 1, args.muon, args.steps, args.muon * 0.01, args.decay)
        for a in range(args.accum):
            x, y = batch(tr, rng, per)
            ctx = model.no_sync() if ddp and a < args.accum - 1 else torch.enable_grad()
            with ctx:
                loss = loss_of(model, x, y)
                scaler.scale(loss / args.accum).backward()
        scaler.unscale_(adam)
        if muon:
            scaler.unscale_(muon)
        torch.nn.utils.clip_grad_norm_(raw.parameters(), 1.0)
        scaler.step(adam)
        if muon:
            scaler.step(muon)
        scaler.update()
        adam.zero_grad(set_to_none=True)
        if muon:
            muon.zero_grad(set_to_none=True)
        if rank == 0 and step == 20:
            print(f'20 steps in {time.time() - t0:.1f}s', flush=True)
        if rank == 0 and (step % args.every == 0 or step == args.steps):
            raw.eval()
            with torch.no_grad():
                vl = sum(loss_of(raw, vx, vy).item() for vx, vy in vbatches) / len(vbatches)
            raw.train()
            print(f'step {step}  train {loss.item():.3f}  valid {vl:.3f}  {time.time() - t0:.0f}s', flush=True)
            if not math.isfinite(vl):
                raise SystemExit('diverged: valid loss is not finite; the best weights are the last ones saved')
            if vl < best:
                best = vl
                from safetensors.torch import save_file
                save_file({k: v.float().contiguous().cpu() for k, v in raw.state_dict().items()}, str(HERE / f'{args.out}.safetensors'))
                voc = {'tokenizer': meta['tokenizer'], 'vocab_size': nvocab} if meta.get('tokenizer') else {'vocab': ''.join(vocab)}
                (HERE / f'{args.out}.json').write_text(json.dumps({**CFG, **voc, 'valid_loss': round(vl, 4), 'step': step}))
    if ddp:
        dist.destroy_process_group()


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('pack')
    p.add_argument('files', nargs='+')
    p.add_argument('--out', required=True)
    p.add_argument('--vocab', help='a character model json (tiny/big24.json) whose vocabulary to use')
    p.add_argument('--tokenizer', help='a BPE tokenizer in tiny/ (tok4k): uint16 ids for the base model')
    p.add_argument('--weight', help='times each file repeats, comma-separated (default 1 each)')
    p.add_argument('--dedup', action='store_true', help='drop lines seen before (needs PYTHONHASHSEED=0)')
    p.add_argument('--seen-in', help='.npy of line hashes an earlier stage packed (with --dedup)')
    p.add_argument('--seen-out', help='save the hashes of all lines seen so far (.npy)')
    t = sub.add_parser('train')
    t.add_argument('--bin', required=True, help='a packed corpus (without .bin)')
    t.add_argument('--steps', type=int, default=3000)
    t.add_argument('--batch', type=int, default=64, help='global batch, split over the cards')
    t.add_argument('--accum', type=int, default=1, help='micro-batches per step on each card')
    t.add_argument('--every', type=int, default=100)
    t.add_argument('--out', default='tiny')
    t.add_argument('--init', help='start from these weights (a name in tiny/)')
    t.add_argument('--layers', type=int, default=CFG['layers'])
    t.add_argument('--dim', type=int, default=CFG['dim'])
    t.add_argument('--heads', type=int, default=CFG['heads'])
    t.add_argument('--ctx', type=int, default=CFG['ctx'], help='context in ids (characters or BPE tokens)')
    t.add_argument('--arch', default='gpt2', choices=['gpt2', 'v2'], help='gpt2: the model the page runs today; v2: TinyLMv2 (speedrun techniques)')
    t.add_argument('--embed-lr', type=float, default=0, help='AdamW rate for the embeddings (default: --lr)')
    t.add_argument('--lr', type=float, default=1e-3)
    t.add_argument('--muon', type=float, default=0)
    t.add_argument('--decay', type=float, default=-1, help='WSD: share of steps decaying at the end (0 = none); default cosine')
    t.add_argument('--compile', action='store_true')
    t.add_argument('--flash', action='store_true', help='FlashAttention-2 for V100 (flash_attn_legacy) instead of PyTorch SDPA')
    t.add_argument('--compile-mode', default=None, help='torch.compile mode: max-autotune, max-autotune-no-cudagraphs, reduce-overhead')
    args = ap.parse_args()
    pack(args) if args.cmd == 'pack' else train(args)


if __name__ == '__main__':
    main()
