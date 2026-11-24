"""tiny.safetensors → deckc/site/tiny.json: weight matrices as int8 with one float32 scale per
row, vectors and scalars as float32, all base64. JSON because the artifact serves .json (not .bin).
Reads MLX's and PyTorch's checkpoints alike (plain safetensors). A BPE model (tiny/train_torch.py with a
tokenizer) also carries its vocabulary and merges, for deckc/src/tiny2.mjs.

    uv run python tiny/export.py [name] [out]     # default: tiny -> deckc/site/tiny.json
"""
import base64
import sys
import json
from pathlib import Path

import numpy as np
from safetensors.numpy import load_file

HERE = Path(__file__).parent
OUT = HERE.parent / 'deckc' / 'site' / 'tiny.json'


def b64(a):
    return base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()


def main(name='tiny', out=None):
    global OUT
    OUT = Path(out) if out else OUT
    cfg = json.loads((HERE / f'{name}.json').read_text())
    tensors = {}
    err = 0.0
    for name, w in load_file(str(HERE / f'{name}.safetensors')).items():
        w = w.astype(np.float32)
        if w.ndim == 2:
            scale = np.abs(w).max(axis=1, keepdims=True) / 127 + 1e-12
            q = np.clip(np.round(w / scale), -127, 127).astype(np.int8)
            err = max(err, float(np.abs(q * scale - w).max()))
            tensors[name] = {'shape': list(w.shape), 'q': b64(q), 's': b64(scale.astype(np.float32).ravel())}
        else:
            tensors[name] = {'shape': list(w.shape), 'f': b64(w.astype(np.float32))}
    doc = {'config': cfg, 'tensors': tensors}
    if cfg.get('tokenizer'):
        t = json.loads((HERE / f"{cfg['tokenizer']}.tokenizer.json").read_text())['model']
        vocab = [None] * len(t['vocab'])
        for tok, i in t['vocab'].items():
            vocab[i] = tok
        doc['tokenizer'] = {'vocab': vocab, 'merges': [m if isinstance(m, str) else ' '.join(m) for m in t['merges']]}
    OUT.write_text(json.dumps(doc))
    print(f'{OUT.name}: {OUT.stat().st_size / 1e6:.1f} MB, {len(tensors)} tensors, max int8 error {err:.4f}')


if __name__ == '__main__':
    main(*sys.argv[1:3])
