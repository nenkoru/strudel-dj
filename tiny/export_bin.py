"""A checkpoint -> model.int8.bin + model.int8.json for the browser runtime (space/model.mjs).

Every 2-D weight becomes int8 with one float32 scale per row (as tiny/export.py does), vectors stay float32.
The .bin holds the segments back to back, each padded to 4 bytes so Float32Array views need no copy; the
.json holds the config, the tokenizer (vocabulary and merges) and each tensor's shape and byte ranges.

    python3 tiny/export_bin.py base130ft3 out/ft3      # reads tiny/base130ft3.{safetensors,json}
"""
import json
import sys
from pathlib import Path

import numpy as np
from safetensors.numpy import load_file

HERE = Path(__file__).parent


def quantize(w):
    scale = (np.abs(w).max(axis=1, keepdims=True) / 127 + 1e-12).astype(np.float32)
    q = np.clip(np.round(w / scale), -127, 127).astype(np.int8)
    return q, scale.ravel()


def tokenizer(name):
    t = json.loads((HERE / f'{name}.tokenizer.json').read_text())['model']
    vocab = [None] * len(t['vocab'])
    for tok, i in t['vocab'].items():
        vocab[i] = tok
    return {'vocab': vocab, 'merges': [m if isinstance(m, str) else ' '.join(m) for m in t['merges']]}


def main(name, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    cfg = json.loads((HERE / f'{name}.json').read_text())
    tensors, err, pos = {}, 0.0, 0
    with open(out / 'model.int8.bin', 'wb') as f:
        def put(a):
            nonlocal pos
            b = np.ascontiguousarray(a).tobytes()
            f.write(b + b'\0' * (-len(b) % 4))
            at, pos = pos, pos + len(b) + (-len(b) % 4)
            return [at, len(b)]
        for key, w in sorted(load_file(str(HERE / f'{name}.safetensors')).items()):
            w = w.astype(np.float32)
            if w.ndim == 2:
                q, s = quantize(w)
                err = max(err, float(np.abs(q * s[:, None] - w).max()))
                tensors[key] = {'shape': list(w.shape), 'q': put(q), 's': put(s)}
            else:
                tensors[key] = {'shape': list(w.shape), 'f': put(w)}
    doc = {'config': cfg, 'source': name, 'tensors': tensors, 'tokenizer': tokenizer(cfg['tokenizer'])}
    (out / 'model.int8.json').write_text(json.dumps(doc))
    print(f'{out}: {pos / 1e6:.1f} MB bin, {len(tensors)} tensors, max int8 error {err:.4f}')


if __name__ == '__main__':
    main(*sys.argv[1:3])
