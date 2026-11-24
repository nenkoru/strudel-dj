// strudel-dj-129m in the browser: TinyLMv2 (tiny/train_torch.py --arch v2) in plain JavaScript over int8
// weights with one scale per row (tiny/export_bin.py), multiplied in int8 directly so the 129M weights
// take about 130 MB of memory, not 516. Same maths as deckc/src/tiny2.mjs: parameter-free RMS norms,
// rotary positions, RMS-normed queries and keys, a squared-ReLU MLP, value embeddings in the first and
// last three layers, U-net skips and a soft-capped untied head; byte-level BPE tokens.

const EPS = 1.1920928955078125e-7;  // torch's F.rms_norm default for float32

function rmsNorm(x, out, from = 0, n = x.length - from) {
  let ss = 0;
  for (let i = 0; i < n; i++) ss += x[from + i] * x[from + i];
  const inv = 1 / Math.sqrt(ss / n + EPS);
  for (let i = 0; i < n; i++) out[from + i] = x[from + i] * inv;
  return out;
}

// The int8 matrix-vector product in WebAssembly SIMD (space/linear.wat, assembled with wabt): about 4x the
// plain JS loop below, which stays as the fallback for browsers without SIMD.
const KERNEL = 'AGFzbQEAAAABCgFgBn9/f39/fwADAgEABQMBAAEHEAIDbWVtAgAGbGluZWFyAAAK1wIB1AICBH8FewJAA0AgBiAETw0B/QwAAAAAAAAAAAAAAAAAAAAAIQv9DAAAAAAAAAAAAAAAAAAAAAAhDP0MAAAAAAAAAAAAAAAAAAAAACEN/QwAAAAAAAAAAAAAAAAAAAAAIQ4gACAGIAVsaiEIIAIhCUEAIQcCQANAIAcgBU8NASAI/QEDACEKIAsgCv2nAf36ASAJ/QAEAP3mAf3kASELIAwgCv2oAf36ASAJ/QAEEP3mAf3kASEMIAj9AQMIIQogDSAK/acB/foBIAn9AAQg/eYB/eQBIQ0gDiAK/agB/foBIAn9AAQw/eYB/eQBIQ4gCEEQaiEIIAlBwABqIQkgB0EQaiEHDAALCyALIAz95AEgDSAO/eQB/eQBIQsgAyAGQQJ0aiABIAZBAnRqKgIAIAv9HwAgC/0fAZIgC/0fAiAL/R8DkpKUOAIAIAZBAWohBgwACwsL';

function kernel() {
  try {
    const bytes = Uint8Array.from(atob(KERNEL), (c) => c.charCodeAt(0));
    return WebAssembly.validate(bytes) ? new WebAssembly.Instance(new WebAssembly.Module(bytes)).exports : null;
  } catch {
    return null;
  }
}

// out = diag(W.s) W.q x, W.q int8 row-major [n, m], m a multiple of 4
function linearJS(W, x, out, n, m) {
  const q = W.q, s = W.s;
  for (let r = 0; r < n; r++) {
    const o = r * m;
    let a0 = 0, a1 = 0, a2 = 0, a3 = 0;
    for (let c = 0; c < m; c += 4) {
      a0 += q[o + c] * x[c]; a1 += q[o + c + 1] * x[c + 1];
      a2 += q[o + c + 2] * x[c + 2]; a3 += q[o + c + 3] * x[c + 3];
    }
    out[r] = (a0 + a1 + a2 + a3) * s[r];
  }
  return out;
}

function row(W, id, D, out) {  // one embedding row, dequantized
  const q = W.q, s = W.s[id], o = id * D;
  for (let j = 0; j < D; j++) out[j] = q[o + j] * s;
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

export function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6D2B79F5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export const END = '\x1e';  // a program ends with a line holding only this character

export class StrudelLM {
  // doc: the parsed model.int8.json; buf: the ArrayBuffer of model.int8.bin
  constructor(doc, buf, { wasm = true } = {}) {
    const c = doc.config;
    this.cfg = c;
    this.bpe = new BPE(doc.tokenizer);
    const k = wasm ? kernel() : null;
    if (k) {  // weights live in the kernel's memory, followed by room for one input and one output vector
      const at = Math.ceil(buf.byteLength / 64) * 64, room = 4 * 4 * c.dim + 4 * c.vocab_size;
      k.mem.grow(Math.ceil((at + room) / 65536));
      new Uint8Array(k.mem.buffer).set(new Uint8Array(buf));
      buf = k.mem.buffer;
      this.k = k; this.X = new Float32Array(buf, at, 4 * c.dim); this.O = new Float32Array(buf, at + 16 * c.dim, c.vocab_size);
    }
    this.backend = k ? 'wasm-simd' : 'js';
    const w = (name) => {
      const t = doc.tensors[name];
      if (t.f) return new Float32Array(buf, t.f[0], t.f[1] / 4);
      return { q: new Int8Array(buf, t.q[0], t.q[1]), s: new Float32Array(buf, t.s[0], t.s[1] / 4), qo: t.q[0], so: t.s[0] };
    };
    this.tok = w('tok.weight'); this.head = w('head.weight'); this.skip = w('skip');
    this.ve = [0, 1, 2].map((i) => w(`ve.${i}.weight`));
    const L = c.layers;
    this.blocks = Array.from({ length: L }, (_, i) => {
      const p = `blocks.${i}.`, b = {};
      for (const k of ['qkv.weight', 'proj.weight', 'up.weight', 'down.weight', 'mix']) b[k] = w(p + k);
      if (doc.tensors[p + 'vmix']) b.vmix = w(p + 'vmix')[0];
      b.ve = i < 3 ? i : i >= L - 3 ? i - (L - 3) : -1;
      return b;
    });
    const hd = c.dim / c.heads, half = hd / 2;
    this.freq = Float64Array.from({ length: half }, (_, j) => 1 / 10000 ** (j / half));
  }

  // Load from a folder URL holding model.int8.json and model.int8.bin; onProgress({loaded, total}).
  // With `cache` (a Cache Storage name) the files are kept for the next visit.
  static async load(base, { onProgress = () => {}, cache = null } = {}) {
    const get = async (name, progress) => {
      const url = base + name;
      const store = cache && typeof caches !== 'undefined' ? await caches.open(cache).catch(() => null) : null;
      const hit = store && await store.match(url).catch(() => null);
      if (hit) return hit.arrayBuffer();
      const res = await fetch(url);
      if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
      const total = +res.headers.get('content-length') || 0;
      let data;
      if (progress && res.body) {
        const reader = res.body.getReader(), chunks = [];
        let loaded = 0;
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          chunks.push(value); loaded += value.length;
          onProgress({ loaded, total });
        }
        data = new Uint8Array(loaded);
        let at = 0;
        for (const ch of chunks) { data.set(ch, at); at += ch.length; }
        data = data.buffer;
      } else {
        data = await res.arrayBuffer();
      }
      if (store) await store.put(url, new Response(data)).catch(() => {});
      return data;
    };
    const doc = JSON.parse(new TextDecoder().decode(await get('model.int8.json', false)));
    return new StrudelLM(doc, await get('model.int8.bin', true));
  }

  linear(W, x, out, n, m) {
    if (!this.k) return linearJS(W, x, out, n, m);
    this.X.set(x);
    this.k.linear(W.qo, W.so, this.X.byteOffset, this.O.byteOffset, n, m);
    out.set(this.O.subarray(0, n));
    return out;
  }

  newCache() { return { cap: 0, layers: this.blocks.map(() => ({ k: null, v: null })) }; }

  grow(cache, t) {
    if (t < cache.cap) return;
    const D = this.cfg.dim, cap = Math.min(this.cfg.ctx, Math.max(256, cache.cap * 2));
    for (const l of cache.layers) {
      const k = new Float32Array(cap * D), v = new Float32Array(cap * D);
      if (l.k) { k.set(l.k); v.set(l.v); }
      l.k = k; l.v = v;
    }
    cache.cap = cap;
  }

  rope(x, t) {  // in place on each head of x (length dim)
    const { dim: D, heads: H } = this.cfg, hd = D / H, half = hd / 2;
    for (let h = 0; h < H; h++) {
      const o = h * hd;
      for (let j = 0; j < half; j++) {
        const ang = Math.fround(t * this.freq[j]), c = Math.cos(ang), s = Math.sin(ang);
        const a = x[o + j], b = x[o + half + j];
        x[o + j] = a * c - b * s; x[o + half + j] = a * s + b * c;
      }
    }
  }

  // Logits for the next token after feeding `id` at position `t`; keys and values are cached.
  step(id, t, cache) {
    const { dim: D, heads: H } = this.cfg, hd = D / H, L = this.blocks.length, V = this.bpe.vocab.length;
    this.grow(cache, t);
    const x0 = rmsNorm(row(this.tok, id, D, new Float32Array(D)), new Float32Array(D));
    const x = Float32Array.from(x0);
    const h = new Float32Array(D), qkv = new Float32Array(3 * D), a = new Float32Array(D), o = new Float32Array(D);
    const u = new Float32Array(4 * D), e = new Float32Array(D), att = new Float64Array(t + 1), skips = [];
    const scale = 1 / Math.sqrt(hd);
    this.blocks.forEach((b, i) => {
      if (i >= L - Math.floor(L / 2)) {
        const s = skips.pop(), wgt = this.skip[L - 1 - i];
        for (let j = 0; j < D; j++) x[j] += wgt * s[j];
      }
      for (let j = 0; j < D; j++) x[j] = b.mix[0] * x[j] + b.mix[1] * x0[j];
      rmsNorm(x, h);
      this.linear(b['qkv.weight'], h, qkv, 3 * D, D);
      const q = qkv.subarray(0, D), k = qkv.subarray(D, 2 * D), v = qkv.subarray(2 * D);
      for (let hh = 0; hh < H; hh++) { rmsNorm(q, q, hh * hd, hd); rmsNorm(k, k, hh * hd, hd); }
      this.rope(q, t); this.rope(k, t);
      if (b.ve >= 0) {
        row(this.ve[b.ve], id, D, e);
        const m = b.vmix;
        for (let j = 0; j < D; j++) v[j] = (1 - m) * v[j] + m * e[j];
      }
      const { k: K, v: Vc } = cache.layers[i];
      K.set(k, t * D); Vc.set(v, t * D);
      for (let hh = 0; hh < H; hh++) {
        const off = hh * hd;
        let max = -Infinity;
        for (let s = 0; s <= t; s++) {
          let dot = 0;
          const ko = s * D + off;
          for (let j = 0; j < hd; j++) dot += q[off + j] * K[ko + j];
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
      this.linear(b['proj.weight'], a, o, D, D);
      for (let j = 0; j < D; j++) x[j] += o[j];
      rmsNorm(x, h);
      this.linear(b['up.weight'], h, u, 4 * D, D);
      for (let j = 0; j < 4 * D; j++) u[j] = u[j] > 0 ? u[j] * u[j] : 0;
      this.linear(b['down.weight'], u, o, D, 4 * D);
      for (let j = 0; j < D; j++) x[j] += o[j];
      if (i < Math.floor(L / 2)) skips.push(Float32Array.from(x));
    });
    rmsNorm(x, h);
    const logits = this.linear(this.head, h, new Float32Array(V), V, D);
    for (let j = 0; j < V; j++) logits[j] = 15 * Math.tanh(logits[j] / 15);
    return logits;
  }

  // Continue `prompt` until `stop` appears (END for a whole program, '\n' for one line). Synchronous: run it
  // in a Web Worker. onToken(count, textSoFar) after each new token; return true from it to stop early.
  generate(prompt, { stop = END, temperature = 0.9, topK = 40, maxTokens = 1600, seed = 1, onToken = () => {} } = {}) {
    const random = mulberry32(seed), ids = this.bpe.encode(prompt), cache = this.newCache(), out = [];
    let logits, t = 0;
    for (const id of ids) logits = this.step(id, t++, cache);
    while (out.length < maxTokens && t < this.cfg.ctx) {
      const order = [...logits.keys()].sort((x, y) => logits[y] - logits[x]).slice(0, topK);
      const p = order.map((i) => Math.exp((logits[i] - logits[order[0]]) / temperature));
      let r = random() * p.reduce((s, x) => s + x, 0), pick = order[0];
      for (let j = 0; j < order.length; j++) { r -= p[j]; if (r <= 0) { pick = order[j]; break; } }
      out.push(pick);
      const text = this.bpe.decode(out), at = text.indexOf(stop);
      if (at >= 0) return { text: text.slice(0, at), tokens: out.length, complete: true };
      if (onToken(out.length, text) === true) return { text, tokens: out.length, complete: false };
      logits = this.step(pick, t++, cache);
    }
    return { text: this.bpe.decode(out), tokens: out.length, complete: false };
  }
}
