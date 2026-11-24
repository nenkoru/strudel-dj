"""A base model (v2, BPE: tiny/<name>.safetensors) as a small HTTP service on the GPU, so deckc/batch.mjs
on the Mac can compose a swipe batch with it (through an ssh tunnel) while the browser model is not
exported yet. Requests are served one at a time.

    GET  /info      -> the model's json (layers, dim, step, valid_loss...)
    POST /generate  {"prompt", "temperature", "top_k", "max_tokens", "stop"} -> {"text"}: the continuation
                    of "\\n" + prompt up to `stop` (default a newline), without either

    venv/bin/python tiny/serve.py base130ft [port]     (ssh -N -L 8787:localhost:8787 <gpu-server>)
"""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import torch
import torch.nn.functional as F
from tokenizers import Tokenizer

from evalft import AMP, DEV, HERE, load

NAME = sys.argv[1]
model, cfg = load(NAME)
cfg = {**cfg, 'name': NAME}
tok = Tokenizer.from_file(str(HERE / f'{cfg["tokenizer"]}.tokenizer.json'))
lock = threading.Lock()


@torch.no_grad()
def generate(prompt, temperature=0.9, top_k=40, max_tokens=300, stop='\n'):
    ids = tok.encode('\n' + prompt).ids
    start = len(ids)
    for _ in range(max_tokens):
        x = torch.tensor([ids[-cfg['ctx']:]], device=DEV)
        with torch.autocast(**AMP):
            logits = model(x)[0, -1].float() / max(temperature, 1e-3)
        v, _ = logits.topk(top_k)
        logits[logits < v[-1]] = -1e9
        ids.append(torch.multinomial(F.softmax(logits, -1), 1).item())
        text = tok.decode(ids[start:])
        if stop in text:
            return text.split(stop)[0]
    raise ValueError('no stop within max_tokens')


class Handler(BaseHTTPRequestHandler):
    def reply(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self.reply(200, cfg) if self.path == '/info' else self.reply(404, {})

    def do_POST(self):
        try:
            q = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            with lock:
                text = generate(q['prompt'], q.get('temperature', 0.9), q.get('top_k', 40), q.get('max_tokens', 300), q.get('stop', '\n'))
            self.reply(200, {'text': text})
        except Exception as e:
            self.reply(500, {'error': str(e)})

    def log_message(self, *a):
        pass


if __name__ == '__main__':
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8787
    print(f'{NAME} on 127.0.0.1:{port}', flush=True)
    ThreadingHTTPServer(('127.0.0.1', port), Handler).serve_forever()
