// The tiny pattern model (tiny/train.py) in plain JavaScript: a character-level transformer, ~5M
// parameters, int8 weights dequantized at load. Generation runs in short slices that yield to
// the event loop, so the guest decks' scheduler (every 40 ms, 250 ms ahead) never starves.

function bytes(b64) {
  const s = atob(b64), out = new Uint8Array(s.length);
  for (let i = 0; i < s.length; i++) out[i] = s.charCodeAt(i);
  return out.buffer;
}

function tensor(t) {
  if (t.f) return new Float32Array(bytes(t.f));
  const q = new Int8Array(bytes(t.q)), s = new Float32Array(bytes(t.s));
  const [rows, cols] = t.shape, w = new Float32Array(rows * cols);
  for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) w[r * cols + c] = q[r * cols + c] * s[r];
  return w;
}

// y = W x + b, W row-major [out, in]
function linear(W, b, x, out, n, m) {
  for (let r = 0; r < n; r++) {
    let acc = b ? b[r] : 0;
    const o = r * m;
    for (let c = 0; c < m; c++) acc += W[o + c] * x[c];
    out[r] = acc;
  }
  return out;
}

function layerNorm(x, g, b, out) {
  const n = x.length;
  let mean = 0; for (let i = 0; i < n; i++) mean += x[i]; mean /= n;
  let v = 0; for (let i = 0; i < n; i++) v += (x[i] - mean) ** 2; v /= n;
  const inv = 1 / Math.sqrt(v + 1e-5);
  for (let i = 0; i < n; i++) out[i] = (x[i] - mean) * inv * g[i] + b[i];
  return out;
}

// One channel, waiters in order: two generations at once (a guest's order and the AI deck) each get
// their turn instead of one replacing the other's handler and never resuming.
const channel = typeof MessageChannel === 'undefined' ? null : new MessageChannel();
const waiting = [];
if (channel) { channel.port1.onmessage = () => waiting.shift()?.(); channel.port1.unref?.(); }
const yieldTask = () => new Promise((r) => {
  if (!channel) return setTimeout(r, 0);
  waiting.push(r);
  channel.port2.postMessage(0);
});

const gelu = (x) => 0.5 * x * (1 + Math.tanh(0.7978845608028654 * (x + 0.044715 * x * x * x)));

export class Tiny {
  constructor(json) {
    const c = json.config;
    this.cfg = c; this.vocab = [...c.vocab];
    this.index = Object.fromEntries(this.vocab.map((ch, i) => [ch, i]));
    const w = (name) => tensor(json.tensors[name]);
    this.tok = w('tok.weight'); this.pos = w('pos.weight');
    this.lnG = w('ln.weight'); this.lnB = w('ln.bias');
    this.blocks = Array.from({ length: c.layers }, (_, i) => {
      const p = `blocks.${i}.`;
      return Object.fromEntries(['ln1.weight', 'ln1.bias', 'ln2.weight', 'ln2.bias', 'qkv.weight', 'qkv.bias', 'proj.weight', 'proj.bias',
        'up.weight', 'up.bias', 'down.weight', 'down.bias'].map((k) => [k, w(p + k)]));
    });
  }

  static async load(url) { return new Tiny(await fetch(url).then((r) => r.json())); }

  // Logits for the next character after feeding `id` at position `t`; keys and values are cached.
  step(id, t, cache) {
    const { dim: D, heads: H } = this.cfg, hd = D / H, V = this.vocab.length;
    const x = new Float32Array(D), h = new Float32Array(D), qkv = new Float32Array(3 * D);
    const a = new Float32Array(D), o = new Float32Array(D), u = new Float32Array(4 * D), att = new Float32Array(t + 1);
    for (let i = 0; i < D; i++) x[i] = this.tok[id * D + i] + this.pos[t * D + i];
    this.blocks.forEach((b, l) => {
      layerNorm(x, b['ln1.weight'], b['ln1.bias'], h);
      linear(b['qkv.weight'], b['qkv.bias'], h, qkv, 3 * D, D);
      const { k, v } = cache[l];
      k.set(qkv.subarray(D, 2 * D), t * D); v.set(qkv.subarray(2 * D), t * D);
      const scale = 1 / Math.sqrt(hd);
      for (let hh = 0; hh < H; hh++) {
        const off = hh * hd;
        let max = -Infinity;
        for (let s = 0; s <= t; s++) {
          let dot = 0;
          for (let i = 0; i < hd; i++) dot += qkv[off + i] * k[s * D + off + i];
          att[s] = dot * scale; if (att[s] > max) max = att[s];
        }
        let sum = 0;
        for (let s = 0; s <= t; s++) { att[s] = Math.exp(att[s] - max); sum += att[s]; }
        for (let i = 0; i < hd; i++) {
          let acc = 0;
          for (let s = 0; s <= t; s++) acc += att[s] * v[s * D + off + i];
          a[off + i] = acc / sum;
        }
      }
      linear(b['proj.weight'], b['proj.bias'], a, o, D, D);
      for (let i = 0; i < D; i++) x[i] += o[i];
      layerNorm(x, b['ln2.weight'], b['ln2.bias'], h);
      linear(b['up.weight'], b['up.bias'], h, u, 4 * D, D);
      for (let i = 0; i < 4 * D; i++) u[i] = gelu(u[i]);
      linear(b['down.weight'], b['down.bias'], u, o, D, 4 * D);
      for (let i = 0; i < D; i++) x[i] += o[i];
    });
    layerNorm(x, this.lnG, this.lnB, h);
    return linear(this.tok, null, h, new Float32Array(V), V, D);
  }

  newCache() {
    const n = this.cfg.ctx * this.cfg.dim;
    return this.blocks.map(() => ({ k: new Float32Array(n), v: new Float32Array(n) }));
  }

  // Continue '\n' + prompt until the next '\n'. Returns the generated text (without the prompt).
  async generate(prompt, { temperature = 0.8, topK = 12, maxLen = 420, slice = 12, random = Math.random } = {}) {
    const ids = ['\n', ...prompt].map((ch) => {
      if (!(ch in this.index)) throw Error(`character ${JSON.stringify(ch)} not in the model's vocabulary`);
      return this.index[ch];
    });
    const cache = this.newCache();
    let logits, t = 0, out = '', t0 = performance.now();
    // yield through a MessageChannel: setTimeout(0) is clamped to 1 s in a background tab
    const pause = async () => { if (performance.now() - t0 > slice) { await yieldTask(); t0 = performance.now(); } };
    for (const id of ids) { logits = this.step(id, t++, cache); await pause(); }
    while (out.length < maxLen && t < this.cfg.ctx) {
      const order = [...logits.keys()].sort((x, y) => logits[y] - logits[x]).slice(0, topK);
      const p = order.map((i) => Math.exp((logits[i] - logits[order[0]]) / temperature));
      let r = random() * p.reduce((s, x) => s + x, 0), pick = order[0];
      for (let j = 0; j < order.length; j++) { r -= p[j]; if (r <= 0) { pick = order[j]; break; } }
      const ch = this.vocab[pick];
      if (ch === '\n') return out;
      out += ch;
      logits = this.step(pick, t++, cache);
      await pause();
    }
    return out;
  }
}
