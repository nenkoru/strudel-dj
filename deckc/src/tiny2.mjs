// The base model (tiny/train_torch.py --arch v2, BPE tokens) in plain JavaScript: TinyLMv2 — parameter-free
// RMS norms, rotary positions, RMS-normed queries and keys, a squared-ReLU MLP, value embeddings in the
// first and last three layers, U-net skips and a soft-capped untied head — over byte-level BPE tokens
// (tiny/tokenizer.py). Weights come int8 with a scale per row (tiny/export.py). Generation runs in short
// slices that yield to the event loop, like tiny.mjs, so the guest decks' scheduler never starves.

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

// y = W x, W row-major [out, in]
function linear(W, x, out, n, m) {
  for (let r = 0; r < n; r++) {
    let acc = 0;
    const o = r * m;
    for (let c = 0; c < m; c++) acc += W[o + c] * x[c];
    out[r] = acc;
  }
  return out;
}

const EPS = 1.1920928955078125e-7;  // torch's F.rms_norm default for float32
function rmsNorm(x, out, from = 0, n = x.length - from) {
  let ss = 0;
  for (let i = 0; i < n; i++) ss += x[from + i] * x[from + i];
  const inv = 1 / Math.sqrt(ss / n + EPS);
  for (let i = 0; i < n; i++) out[from + i] = x[from + i] * inv;
  return out;
}

// GPT-2's byte <-> printable character map, as the tokenizers library's ByteLevel uses it
function byteMap() {
  const bs = [];
  for (let b = 33; b <= 126; b++) bs.push(b);
  for (let b = 161; b <= 172; b++) bs.push(b);
  for (let b = 174; b <= 255; b++) bs.push(b);
  const cs = [...bs];
  let n = 0;
  for (let b = 0; b < 256; b++) if (!bs.includes(b)) { bs.push(b); cs.push(256 + n++); }
  const enc = {}, dec = {};
  bs.forEach((b, i) => { enc[b] = String.fromCharCode(cs[i]); dec[String.fromCharCode(cs[i])] = b; });
  return { enc, dec };
}

export class BPE {
  constructor({ vocab, merges }) {
    this.vocab = vocab;  // id -> token (in the byte map's characters)
    this.ids = new Map(vocab.map((t, i) => [t, i]));
    this.ranks = new Map(merges.map((m, i) => [m, i]));
    const { enc, dec } = byteMap();
    this.enc = enc; this.dec = dec;
    this.utf8 = new TextEncoder(); this.text = new TextDecoder();
  }

  // a line (or the newline) at a time, as the Python pre-tokenizer splits; merges by rank within it
  encode(s) {
    const out = [];
    for (const word of s.split(/(\n)/)) {
      if (!word) continue;
      let parts = [...this.utf8.encode(word)].map((b) => this.enc[b]);
      while (parts.length > 1) {
        let best = -1, rank = Infinity;
        for (let i = 0; i < parts.length - 1; i++) {
          const r = this.ranks.get(parts[i] + ' ' + parts[i + 1]);
          if (r !== undefined && r < rank) { rank = r; best = i; }
        }
        if (best < 0) break;
        parts = [...parts.slice(0, best), parts[best] + parts[best + 1], ...parts.slice(best + 2)];
      }
      for (const p of parts) out.push(this.ids.get(p));
    }
    return out;
  }

  decode(ids) {
    const bs = [];
    for (const id of ids) for (const ch of this.vocab[id]) bs.push(this.dec[ch]);
    return this.text.decode(new Uint8Array(bs));
  }
}

const channel = typeof MessageChannel === 'undefined' ? null : new MessageChannel();
const waiting = [];
if (channel) { channel.port1.onmessage = () => waiting.shift()?.(); channel.port1.unref?.(); }
const yieldTask = () => new Promise((r) => {
  if (!channel) return setTimeout(r, 0);
  waiting.push(r);
  channel.port2.postMessage(0);
});

export class Tiny2 {
  constructor(json) {
    const c = json.config;
    this.cfg = c;
    this.bpe = new BPE(json.tokenizer);
    const w = (name) => tensor(json.tensors[name]);
    this.tok = w('tok.weight'); this.head = w('head.weight'); this.skip = w('skip');
    this.ve = [0, 1, 2].map((i) => w(`ve.${i}.weight`));
    const L = c.layers;
    this.blocks = Array.from({ length: L }, (_, i) => {
      const p = `blocks.${i}.`, b = {};
      for (const k of ['qkv.weight', 'proj.weight', 'up.weight', 'down.weight', 'mix']) b[k] = w(p + k);
      if (json.tensors[p + 'vmix']) b.vmix = w(p + 'vmix')[0];
      b.ve = i < 3 ? i : i >= L - 3 ? i - (L - 3) : -1;
      return b;
    });
    const hd = c.dim / c.heads, half = hd / 2;
    this.freq = Float32Array.from({ length: half }, (_, j) => 1 / 10000 ** (j / half));
  }

  static async load(url) { return new Tiny2(await fetch(url).then((r) => r.json())); }

  newCache() {
    const n = this.cfg.ctx * this.cfg.dim;
    return this.blocks.map(() => ({ k: new Float32Array(n), v: new Float32Array(n) }));
  }

  rope(x, t) {  // in place on each head of x (length dim)
    const { dim: D, heads: H } = this.cfg, hd = D / H, half = hd / 2;
    for (let h = 0; h < H; h++) {
      const o = h * hd;
      for (let j = 0; j < half; j++) {
        const ang = t * this.freq[j], c = Math.cos(ang), s = Math.sin(ang);
        const a = x[o + j], b = x[o + half + j];
        x[o + j] = a * c - b * s; x[o + half + j] = a * s + b * c;
      }
    }
  }

  // Logits for the next token after feeding `id` at position `t`; keys and values are cached.
  step(id, t, cache) {
    const { dim: D, heads: H } = this.cfg, hd = D / H, L = this.blocks.length, V = this.bpe.vocab.length;
    const x0 = rmsNorm(this.tok.subarray(id * D, id * D + D), new Float32Array(D));
    let x = Float32Array.from(x0);
    const h = new Float32Array(D), qkv = new Float32Array(3 * D), a = new Float32Array(D), o = new Float32Array(D);
    const u = new Float32Array(4 * D), att = new Float32Array(t + 1), skips = [];
    this.blocks.forEach((b, i) => {
      if (i >= L - Math.floor(L / 2)) { const s = skips.pop(), wgt = this.skip[L - 1 - i]; for (let j = 0; j < D; j++) x[j] += wgt * s[j]; }
      for (let j = 0; j < D; j++) x[j] = b.mix[0] * x[j] + b.mix[1] * x0[j];
      rmsNorm(x, h);
      linear(b['qkv.weight'], h, qkv, 3 * D, D);
      const q = qkv.subarray(0, D), k = qkv.subarray(D, 2 * D), v = qkv.subarray(2 * D);
      for (let hh = 0; hh < H; hh++) { rmsNorm(q, q, hh * hd, hd); rmsNorm(k, k, hh * hd, hd); }
      this.rope(q, t); this.rope(k, t);
      if (b.ve >= 0) { const e = this.ve[b.ve], m = b.vmix; for (let j = 0; j < D; j++) v[j] = (1 - m) * v[j] + m * e[id * D + j]; }
      const { k: K, v: Vc } = cache[i];
      K.set(k, t * D); Vc.set(v, t * D);
      const scale = 1 / Math.sqrt(hd);
      for (let hh = 0; hh < H; hh++) {
        const off = hh * hd;
        let max = -Infinity;
        for (let s = 0; s <= t; s++) {
          let dot = 0;
          for (let j = 0; j < hd; j++) dot += q[off + j] * K[s * D + off + j];
          att[s] = dot * scale; if (att[s] > max) max = att[s];
        }
        let sum = 0;
        for (let s = 0; s <= t; s++) { att[s] = Math.exp(att[s] - max); sum += att[s]; }
        for (let j = 0; j < hd; j++) {
          let acc = 0;
          for (let s = 0; s <= t; s++) acc += att[s] * Vc[s * D + off + j];
          a[off + j] = acc / sum;
        }
      }
      linear(b['proj.weight'], a, o, D, D);
      for (let j = 0; j < D; j++) x[j] += o[j];
      rmsNorm(x, h);
      linear(b['up.weight'], h, u, 4 * D, D);
      for (let j = 0; j < 4 * D; j++) u[j] = u[j] > 0 ? u[j] * u[j] : 0;
      linear(b['down.weight'], u, o, D, 4 * D);
      for (let j = 0; j < D; j++) x[j] += o[j];
      if (i < Math.floor(L / 2)) skips.push(Float32Array.from(x));
    });
    rmsNorm(x, h);
    const logits = linear(this.head, h, new Float32Array(V), V, D);
    for (let j = 0; j < V; j++) logits[j] = 15 * Math.tanh(logits[j] / 15);
    return logits;
  }

  // Continue the prompt until `stop` appears in the output (a newline for a part's line, the \x1e that
  // ends a program for a piece). Returns the generated text without the prompt or the stop.
  async generate(prompt, { stop = '\n', temperature = 0.8, topK = 40, maxTokens = 600, slice = 12, random = Math.random } = {}) {
    const ids = this.bpe.encode(prompt), cache = this.newCache();
    let logits, t = 0, t0 = performance.now();
    const out = [];
    const pause = async () => { if (performance.now() - t0 > slice) { await yieldTask(); t0 = performance.now(); } };
    for (const id of ids) { logits = this.step(id, t++, cache); await pause(); }
    while (out.length < maxTokens && t < this.cfg.ctx) {
      const order = [...logits.keys()].sort((x, y) => logits[y] - logits[x]).slice(0, topK);
      const p = order.map((i) => Math.exp((logits[i] - logits[order[0]]) / temperature));
      let r = random() * p.reduce((s, x) => s + x, 0), pick = order[0];
      for (let j = 0; j < order.length; j++) { r -= p[j]; if (r <= 0) { pick = order[j]; break; } }
      out.push(pick);
      const text = this.bpe.decode(out), at = text.indexOf(stop);
      if (at >= 0) return text.slice(0, at);
      logits = this.step(pick, t++, cache);
      await pause();
    }
    return this.bpe.decode(out);
  }
}
