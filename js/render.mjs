// Offline renderer: JSONL {id, code, tempo} → <outdir>/<id>.wav through superdough, no browser.
//   node render.mjs <in.jsonl> <outdir> [--limit N] [--bars 4] [--samples <dir with bd/sd/hh.wav>]
// --samples registers those one-shots as bank "trk" (trk_bd, trk_sd, trk_hh) for .bank("trk"), or
// the dir's strudel.json when present (kit.py adds a pitched trk_lead).
// superdough keeps one output controller and one worklet load per process, so the whole batch is
// laid out end to end in a single OfflineAudioContext and sliced afterwards. Network responses
// (soundfonts, TR-909 samples) are cached under ../data/cache: after a first run it works offline.
import './quiet.mjs';
import * as WA from 'node-web-audio-api';
import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';

for (const [k, v] of Object.entries(WA)) globalThis[k] ??= v;
globalThis.window = globalThis;
window.addEventListener = window.removeEventListener = () => {};
window.postMessage = () => {};
globalThis.document = { createElement: () => ({ getContext: () => null }), addEventListener() {}, removeEventListener() {}, dispatchEvent: () => true };

const CACHE = new URL('../data/cache/', import.meta.url);
mkdirSync(CACHE, { recursive: true });
const netFetch = globalThis.fetch;
globalThis.fetch = async (url, opts) => {
  if (String(url).startsWith('file://')) return new Response(readFileSync(new URL(url))); // --samples
  const file = new URL(createHash('sha1').update(String(url)).digest('hex'), CACHE);
  if (!existsSync(file)) {
    const res = await netFetch(url, opts);
    if (!res.ok) throw Error(`${res.status} ${url}`);
    writeFileSync(file, Buffer.from(await res.arrayBuffer()));
  }
  return new Response(readFileSync(file));
};

const { setDefaultAudioContext, initAudio, registerSynthSounds, superdough, samples } = await import('superdough');
// superdough adds room/delay/vowel helpers to AudioContext.prototype only; without these every
// .room() / .delay() / .vowel() event failed ("createReverb is not a function") offline.
for (const k of ['adjustLength', 'createReverb', 'createVowelFilter', 'createFeedbackDelay']) {
  if (AudioContext.prototype[k] && !OfflineAudioContext.prototype[k]) OfflineAudioContext.prototype[k] = AudioContext.prototype[k];
}
// fontloader directly: the package index pulls in sfumato, whose deps are not Node-loadable.
const { registerSoundfonts } = await import('@strudel/soundfonts/fontloader.mjs');
const { compile } = await import('./dialect.mjs');

const args = process.argv.slice(2);
const opt = (name, d) => { const i = args.indexOf(name); return i < 0 ? d : +args[i + 1]; };
const [input, outdir] = args;
const LIMIT = opt('--limit', Infinity), BARS = opt('--bars', 4), SR = 44100, TAIL = 1.5, GAP = 1;
const SAMPLES = args.includes('--samples') ? args[args.indexOf('--samples') + 1] : null;
const KEEP = args.includes('--keep-level');
mkdirSync(outdir, { recursive: true });

function wav(chans) {
  const n = chans[0].length, out = Buffer.alloc(44 + n * 4);
  out.write('RIFF', 0); out.writeUInt32LE(36 + n * 4, 4); out.write('WAVEfmt ', 8); out.writeUInt32LE(16, 16);
  out.writeUInt16LE(1, 20); out.writeUInt16LE(2, 22); out.writeUInt32LE(SR, 24); out.writeUInt32LE(SR * 4, 28);
  out.writeUInt16LE(4, 32); out.writeUInt16LE(16, 34); out.write('data', 36); out.writeUInt32LE(n * 4, 40);
  for (let i = 0; i < n; i++) for (let c = 0; c < 2; c++) {
    out.writeInt16LE(Math.round(Math.max(-1, Math.min(1, chans[c][i])) * 32767), 44 + i * 4 + c * 2);
  }
  return out;
}

const rows = readFileSync(input, 'utf8').split('\n').filter(Boolean).map(JSON.parse).slice(0, LIMIT);
const t0 = performance.now();

// Cost grows with (voices × context length), so large inputs are split into small chunks,
// each rendered by a child process; chunks run in parallel.
const CHUNK = opt('--chunk', 6);
if (!args.includes('--child') && rows.length > CHUNK) {
  const { spawn } = await import('node:child_process');
  const { availableParallelism, tmpdir } = await import('node:os');
  const { mkdtempSync } = await import('node:fs');
  const { fileURLToPath } = await import('node:url');
  const tmp = mkdtempSync(join(tmpdir(), 'strudel-render-'));
  const chunks = [];
  for (let i = 0; i < rows.length; i += CHUNK) chunks.push(rows.slice(i, i + CHUNK));
  const lines = [];
  let next = 0;
  const worker = async () => {
    while (next < chunks.length) {
      const k = next++, file = join(tmp, `${k}.jsonl`);
      writeFileSync(file, chunks[k].map((r) => JSON.stringify(r)).join('\n'));
      const out = await new Promise((resolve) => {
        const p = spawn(process.execPath, [fileURLToPath(import.meta.url), file, outdir, '--child', '--bars', String(BARS),
          ...(SAMPLES ? ['--samples', SAMPLES] : []), ...(KEEP ? ['--keep-level'] : [])],
          { stdio: ['ignore', 'pipe', 'ignore'] });
        let text = '';
        p.stdout.on('data', (d) => { text += d; });
        p.on('close', (code) => resolve({ text, code }));
      });
      const got = out.text.split('\n').filter(Boolean).map(JSON.parse);
      const seen = new Set(got.map((r) => r.id));
      for (const r of chunks[k]) if (!seen.has(r.id)) got.push({ id: r.id, ok: false, error: `renderer exited ${out.code}` });
      lines.push(...got);
    }
  };
  await Promise.all(Array.from({ length: Math.min(opt('--jobs', availableParallelism()), chunks.length) }, worker));
  for (const r of lines) process.stdout.write(JSON.stringify(r) + '\n');
  const audio = lines.reduce((s, r) => s + (r.seconds || 0), 0);
  console.error(JSON.stringify({ rows: rows.length, rendered: lines.filter((r) => r.ok).length, chunks: chunks.length,
    audioSeconds: +audio.toFixed(1), totalMs: Math.round(performance.now() - t0) }));
  process.exit(0);
}
const jobs = [], results = [];
let offset = 0.01;
for (const row of rows) {
  try {
    const { pattern } = compile(row.code);
    const cps = (row.tempo || 120) / 240; // one cycle = one 4/4 bar
    const seconds = BARS / cps + TAIL;
    jobs.push({ row, pattern, cps, offset, seconds });
    offset += seconds + GAP;
  } catch (e) {
    results.push({ id: row.id, ok: false, error: String(e.message).slice(0, 200) });
  }
}

const ctx = new OfflineAudioContext(2, Math.ceil(SR * (offset + 0.1)), SR);
const RealAudioContext = globalThis.AudioContext;
globalThis.AudioContext = function () { return ctx; }; // superdough 1.2 has no setter for its context
setDefaultAudioContext();
globalThis.AudioContext = RealAudioContext;
ctx.resume = async () => {}; // initAudio awaits resume(), which never settles on an unstarted offline context
// A few soundfont zones are MP3s with an ID3 header the decoder rejects; strip it, else use silence.
let decodeFailures = 0;
const decode = ctx.decodeAudioData.bind(ctx);
ctx.decodeAudioData = async (data, ok, err) => {
  let buf;
  try { buf = await decode(data.slice(0)); } catch {
    const b = new Uint8Array(data);
    const id3 = b[0] === 0x49 && b[1] === 0x44 && b[2] === 0x33 ? 10 + ((b[6] << 21) | (b[7] << 14) | (b[8] << 7) | b[9]) : 0;
    try { buf = await decode(b.slice(id3).buffer); } catch { decodeFailures++; buf = ctx.createBuffer(1, 1, SR); }
  }
  ok?.(buf);
  return buf;
};
await initAudio();
registerSynthSounds();
registerSoundfonts();
await samples('https://raw.githubusercontent.com/felixroos/dough-samples/main/tidal-drum-machines.json');
// VCSL (CC0, multi-sampled acoustic instruments: sax_vib, recorder_*, ocarina, harmonica...), as strudel.cc loads it.
await samples('https://strudel.b-cdn.net/vcsl.json', 'https://strudel.b-cdn.net/VCSL/');
if (SAMPLES) {
  const { pathToFileURL } = await import('node:url');
  const { resolve } = await import('node:path');
  const base = pathToFileURL(resolve(SAMPLES)).href + '/';
  const kit = join(SAMPLES, 'strudel.json'); // written by transcribe/kit.py, may hold pitched sounds
  if (existsSync(kit)) await samples(JSON.parse(readFileSync(kit, 'utf8')), base);
  else {
    const have = ['bd', 'sd', 'hh'].filter((n) => existsSync(join(SAMPLES, `${n}.wav`)));
    await samples(Object.fromEntries(have.map((n) => [`trk_${n}`, [`${n}.wav`]])), base);
  }
}

for (const job of jobs) {
  const haps = job.pattern.queryArc(0, BARS).filter((h) => h.hasOnset());
  job.haps = haps.length; job.failed = 0; job.errors = new Set();
  for (const h of haps) {
    // the hap's cycle position as the 5th argument, as @strudel/webaudio passes it: without it every LFO and
    // tremolo restarts its phase on each note (short tremolo notes came out ~10x too quiet)
    try { await superdough(h.value, job.offset + h.whole.begin.valueOf() / job.cps, h.duration.valueOf() / job.cps, job.cps, h.whole.begin.valueOf()); }
    catch (e) { job.failed++; job.errors.add(String(e.message).slice(0, 80)); }
  }
}
const scheduledMs = performance.now() - t0;
const buf = await ctx.startRendering();
const L = buf.getChannelData(0), R = buf.getChannelData(1);
for (const job of jobs) {
  const a = Math.floor(job.offset * SR), b = a + Math.ceil(job.seconds * SR);
  const chans = [L.slice(a, b), R.slice(a, b)];
  let sq = 0, peak = 0;
  for (const c of chans) for (const x of c) { sq += x * x; peak = Math.max(peak, Math.abs(x)); }
  // no clipping in files; --keep-level leaves the level alone (deckc/prerender.py levels the parts itself)
  if (peak > 0.99 && !KEEP) for (const c of chans) for (let i = 0; i < c.length; i++) c[i] *= 0.99 / peak;
  writeFileSync(join(outdir, `${job.row.id}.wav`), wav(chans));
  results.push({ id: job.row.id, ok: true, haps: job.haps, failed: job.failed, errors: [...job.errors].slice(0, 3),
    rms: +Math.sqrt(sq / (2 * chans[0].length)).toFixed(4), peak: +peak.toFixed(3), seconds: +job.seconds.toFixed(2) });
}
for (const r of results) process.stdout.write(JSON.stringify(r) + '\n');
const audio = jobs.reduce((s, j) => s + j.seconds, 0);
console.error(JSON.stringify({ rows: rows.length, rendered: jobs.length, audioSeconds: +audio.toFixed(1), decodeFailures,
  scheduleMs: Math.round(scheduledMs), totalMs: Math.round(performance.now() - t0) }));
process.exit(0);
