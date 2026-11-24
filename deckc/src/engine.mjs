// Third Deck browser engine. Two track decks and the Strudel guest decks (3, 4, ...) share superdough's
// AudioContext and one global clock: the master tempo and a bar grid starting at `origin`.
// Each track deck starts on a global bar line, its playbackRate set so its bars match the
// clock (0.8% for 123 vs 124 BPM, a 14-cent pitch shift); the third deck is queried 0.25 s
// ahead on the same clock, so it keeps playing in time through a transition.
// Bundled to site/deckc.js (see README).
import { initAudio, getAudioContext, superdough, samples, registerSynthSounds, registerSound } from 'superdough';
import { noteToMidi } from '@strudel/core';
import { compile } from '../../js/dialect.mjs';

export { compile };
export { Tiny } from "./tiny.mjs";
export { composePart, composePhrase, promptFor, drumLevel, heardOver, pickVoice, pickForm } from "./compose.mjs";
const LOOKAHEAD = 0.25;
const KILL_DB = -40;

let ready;
export function init(kitUrl, base) {
  return (ready ??= (async () => {
    await initAudio();
    registerSynthSounds();
    const kit = await fetch(kitUrl).then((r) => r.json());
    await samples(kit, new URL(base, location.href).href);
    // Warm the one-shot samples: superdough fetches and decodes on first use, so the first hits of a
    // newly ordered layer came late or not at all, right when guests listen for it. In the background:
    // waiting for all 36 held the rating page's start on a phone, and a part's own sounds are warmed by
    // prepare() before it plays. Pitched instruments (5 MB of notes) only by prepare().
    const at = getAudioContext().currentTime + 0.05;
    Promise.all(Object.entries(kit).filter(([, files]) => Array.isArray(files))
      .map(([s]) => superdough({ s, gain: 0 }, at, 0.05, 1).catch(() => {})));
  })());
}

export const audioContext = () => getAudioContext();

export async function loadBuffer(source) {
  const data = source instanceof ArrayBuffer ? source : await fetch(source).then((r) => r.arrayBuffer());
  return getAudioContext().decodeAudioData(data);
}

// Sounds cut from the track that is playing, so a guest part has the track's own timbre instead of a
// bare oscillator next to a finished mix (the owner: "the sounds stand out from the track's").
// `chop`: an 8th note of the track starting on the offbeat of its loudest bar with chords or leads in
// it (between kicks), played at the part's pitches against the track's key; `trackhat`: a 16th from
// the offbeat of its loudest bar with tops, which the part high-passes into a hat. Cut once per track
// (deckc/hear.py's `hear` and the energy curve choose the bars) and registered as Strudel sounds.
const NOTE_PC = { C: 0, 'C#': 1, D: 2, 'D#': 3, E: 4, F: 5, 'F#': 6, G: 7, 'G#': 8, A: 9, 'A#': 10, B: 11 };
export function useTrackSounds(track) {
  if (!track?.buffer || !track.bpm) return false;
  track.cuts ??= (() => {
    const ctx = getAudioContext(), buf = track.buffer, bar = 240 / track.bpm;
    const loudest = (word) => {
      const bars = (track.energy ?? []).map((e, i) => [e, i]).filter(([, i]) => !track.hear || (track.hear[i] ?? '').includes(word));
      return (bars.sort((x, y) => y[0] - x[0])[0] ?? [0, 16])[1];
    };
    const cut = (barIndex, seconds) => {
      const from = Math.max(0, Math.floor(((track.bar0 ?? 0) + barIndex * bar + bar / 8) * buf.sampleRate));  // the offbeat 8th
      const n = Math.min(Math.floor(seconds * buf.sampleRate), buf.length - from);
      const out = ctx.createBuffer(buf.numberOfChannels, Math.max(1, n), buf.sampleRate);
      const fadeIn = Math.floor(0.004 * buf.sampleRate), fadeOut = Math.floor(0.02 * buf.sampleRate);
      for (let c = 0; c < buf.numberOfChannels; c++) {
        const src = buf.getChannelData(c), dst = out.getChannelData(c);
        for (let i = 0; i < n; i++) dst[i] = src[from + i] * Math.min(1, i / fadeIn, (n - i) / fadeOut);
      }
      return out;
    };
    const root = NOTE_PC[(track.key ?? 'C').split(' ')[0]] ?? 0;
    return { chop: cut(loudest('mid'), bar / 8), hat: cut(loudest('top'), bar / 16), base: 72 + root - (root > 5 ? 12 : 0) };
  })();
  const { chop, hat, base } = track.cuts;
  const player = (buffer, pitched) => (t, value, onended) => {
    const ctx = getAudioContext(), src = ctx.createBufferSource(), g = ctx.createGain();
    src.buffer = buffer;
    const midi = value.note == null ? base : typeof value.note === 'number' ? value.note : noteToMidi(value.note);
    const rate = (pitched ? 2 ** ((midi - base) / 12) : 1) * (value.speed ?? 1);
    src.playbackRate.value = rate;
    const end = t + Math.min(buffer.duration / rate, Math.max(0.03, value.duration ?? 0.2) + (value.release ?? 0.03));
    g.gain.setValueAtTime(1, t); g.gain.setValueAtTime(1, Math.max(t, end - 0.015)); g.gain.linearRampToValueAtTime(0, end);
    src.connect(g); src.start(t); src.stop(end + 0.01);
    src.onended = () => { src.disconnect(); g.disconnect(); onended(); };
    return { node: g, stop: (when) => src.stop(when) };
  };
  registerSound('chop', player(chop, true), { type: 'synth' });
  registerSound('trackhat', player(hat, false), { type: 'synth' });
  return true;
}

// Fetch and decode the sample notes a layer will play (silently), so its first bars are not late.
const warmed = new Set();
export async function prepare(code) {
  let pattern;
  try { ({ pattern } = compile(code)); } catch { return; }
  const at = getAudioContext().currentTime + 0.05, jobs = [];
  for (const h of pattern.queryArc(0, 8)) {
    const { s, note } = h.value, key = `${s}:${note}`;
    if (!s || warmed.has(key)) continue;
    warmed.add(key);
    jobs.push(superdough({ s, note, gain: 0 }, at, 0.05, 1).catch(() => {}));
  }
  await Promise.all(jobs);
}

export function validate(code) {
  compile(code);
  return true;
}

// Plays the first `bars` bars of a layer on its own, from `at` (an AudioContext time) or now.
export function audition(code, { bpm, at, bars = 2, gain = 0.9 }) {
  const { pattern } = compile(code);
  const ctx = getAudioContext();
  const barSec = 240 / bpm, cps = bpm / 240;
  const t0 = at ?? ctx.currentTime + 0.05;
  for (const h of pattern.queryArc(0, bars)) {
    if (!h.hasOnset()) continue;
    const value = { ...h.value, gain: (h.value.gain ?? 1) * gain };
    superdough(value, t0 + h.whole.begin.valueOf() * barSec, h.duration.valueOf() * barSec, cps).catch(() => {});
  }
  return t0 + bars * barSec;
}

// One turntable: source → isolator (low / mid / high) → fader → the tracks bus.
export class Deck {
  constructor(bus) {
    const ctx = getAudioContext();
    this.low = new BiquadFilterNode(ctx, { type: 'lowshelf', frequency: 220 });
    this.mid = new BiquadFilterNode(ctx, { type: 'peaking', frequency: 1000, Q: 0.7 });
    this.high = new BiquadFilterNode(ctx, { type: 'highshelf', frequency: 3500 });
    this.fader = new GainNode(ctx, { gain: 1 });
    this.low.connect(this.mid).connect(this.high).connect(this.fader).connect(bus);
    this.kills = { low: false, mid: false, high: false };
    this.track = null; this.src = null;
  }

  get playing() { return !!this.src; }

  // Start `track` ({buffer, bpm, bar0}) so that its bar `fromBar` lands on global bar `atBar`.
  start(track, clock, atBar, fromBar) {
    this.stop();
    const ctx = getAudioContext();
    this.track = track;
    this.rate = clock.bpm / track.bpm;
    let at = clock.timeOf(atBar);
    let offset = track.bar0 + fromBar * 240 / track.bpm;
    if (offset < 0) { at -= offset / this.rate; offset = 0; }  // the grid may start a few ms before the file
    this.src = new AudioBufferSourceNode(ctx, { buffer: track.buffer, playbackRate: this.rate });
    this.src.connect(this.low);
    this.src.start(Math.max(at, ctx.currentTime), offset + Math.max(0, ctx.currentTime - at) * this.rate);
    this.startBar = atBar; this.fromBar = fromBar;
    const src = this.src;
    src.onended = () => { if (this.src === src) this.src = null; };
  }

  // Track bar playing at global bar `bar` (for labels).
  trackBar(bar) { return this.fromBar + bar - this.startBar; }

  stop(at) {
    if (!this.src) return;
    try { this.src.stop(at); } catch {}
    if (!at) { this.src.disconnect(); this.src = null; }
    else { const src = this.src; setTimeout(() => { if (this.src === src) this.src = null; src.disconnect(); }, (at - getAudioContext().currentTime) * 1000 + 50); }
  }

  kill(band, on, at) {
    this.kills[band] = on;
    const g = this[band].gain, t = at ?? getAudioContext().currentTime;
    g.cancelScheduledValues(t);
    g.setTargetAtTime(on ? KILL_DB : 0, t, 0.03);
  }

  // `from` matters when an earlier move is still scheduled: gain.value is the level now, not at `at`.
  fade(to, at, seconds, from = this.fader.gain.value) {
    const g = this.fader.gain, ctx = getAudioContext();
    const t = Math.max(at ?? ctx.currentTime, ctx.currentTime);
    g.cancelScheduledValues(ctx.currentTime);
    g.setValueAtTime(from, t);
    g.linearRampToValueAtTime(to, t + (seconds || 0.01));
  }
}

// A guest deck: one Strudel layer at a time, for a set number of bars (Infinity = until replaced).
class Slot {
  constructor() { this.layer = null; this.pending = null; this.pendingAt = 0; this.until = Infinity; this.mute = false; }
}

// The global clock, the two track decks and the guest decks (slots) that play on top.
export class Mixer {
  constructor(guestDecks = 2) {
    const ctx = getAudioContext();
    this.bus = new GainNode(ctx, { gain: 0.9 });
    this.bus.connect(ctx.destination);
    this.decks = [new Deck(this.bus), new Deck(this.bus)];
    this.slots = Array.from({ length: guestDecks }, () => new Slot());
    this.bpm = 124; this.origin = 0; this.nudge = 0; this.phraseBars = 8;
    this.gainC = 0.9; this.muteC = false;
    this.running = false;
    this.onSwitch = null; this.onExpire = null; this.onBar = null;
    this.level = null;  // (layer, bar) -> gain factor: the page rides a layer with the track's energy
  }

  get barSec() { return 240 / this.bpm; }
  timeOf(bar) { return this.origin + this.nudge + bar * this.barSec; }
  barAt(t) { return (t - this.origin - this.nudge) / this.barSec; }
  bar() { return Math.floor(this.barAt(getAudioContext().currentTime)); }
  nextPhrase() {
    const c = this.barAt(getAudioContext().currentTime + LOOKAHEAD);
    return Math.max(0, Math.ceil(c / this.phraseBars) * this.phraseBars);
  }

  // Start the clock at `bpm`; global bar 0 begins shortly after now.
  start(bpm) {
    this.stop();
    this.bpm = bpm;
    this.origin = getAudioContext().currentTime + 0.15;
    this.cursor = null; this.lastBar = null;
    for (const s of this.slots) { s.layer = null; s.pending = null; s.until = Infinity; }
    this.running = true;
    this.timer = setInterval(() => this.tick(), 40);
  }

  stop() {
    for (const d of this.decks) { d.stop(); d.fade(1); for (const b of ['low', 'mid', 'high']) d.kill(b, false); }
    clearInterval(this.timer);
    this.running = false;
  }

  setTracksGain(v) { this.bus.gain.setTargetAtTime(v, getAudioContext().currentTime, 0.05); }

  // External clock (Mixxx): the tempo and the time of global bar 0. Small corrections are eased in;
  // a jump (cue, loop, beatjump, tempo move) snaps, and the cursor skips to the lookahead edge so the
  // bars in between are neither replayed nor piled up at once.
  follow(bpm, origin) {
    const now = getAudioContext().currentTime;
    const err = Math.abs(this.timeOf(this.barAt(now + LOOKAHEAD)) - (origin + this.nudge + this.barAt(now + LOOKAHEAD) * 240 / bpm));
    if (err > 0.03 || Math.abs(bpm - this.bpm) / this.bpm > 0.005) {
      this.bpm = bpm; this.origin = origin;
      if (this.cursor != null) this.cursor = this.barAt(now + LOOKAHEAD);
      return true;
    }
    this.bpm = bpm; this.origin += (origin - this.origin) * 0.2;
    return false;
  }

  // Put a layer {id, label, code} on guest deck `i` for `bars` bars, starting on the next phrase
  // line ("phrase") or the next bar ("bar"). Returns the bar it starts on.
  queue(i, layer, { at = 'phrase', bars = Infinity } = {}) {
    const s = this.slots[i];
    const pattern = layer.code ? compile(layer.code).pattern : null;
    s.pending = { ...layer, pattern, bars };
    s.pendingAt = at === 'bar' ? Math.ceil(this.barAt(getAudioContext().currentTime + LOOKAHEAD)) : this.nextPhrase();
    if (!this.running) { s.layer = s.pending; s.pending = null; s.until = Infinity; this.onSwitch?.(i, s.layer); }
    return s.pendingAt;
  }

  // Add or remove guest decks (the last ones go first; notes already scheduled still sound).
  setGuestDecks(n) {
    while (this.slots.length < n) this.slots.push(new Slot());
    this.slots.length = Math.max(0, n);
  }

  // Change how long the layer already on deck `i` keeps playing, counted from its start.
  setLength(i, bars) {
    const s = this.slots[i];
    if (s.layer) { s.layer.bars = bars; s.until = s.layer.startBar + bars; }
    if (s.pending) s.pending.bars = bars;
  }

  tick() {
    const now = getAudioContext().currentTime;
    const from = this.cursor ?? this.barAt(now);
    const to = this.barAt(now + LOOKAHEAD);
    if (!(to > from)) return;
    // Bar callbacks fire a lookahead early, so automation can be scheduled on the exact line.
    for (let b = Math.ceil(from); b < to; b++) if (b !== this.lastBar) { this.lastBar = b; this.onBar?.(b); }
    this.slots.forEach((s, i) => {
      // events in time order: a pending layer starting, or the current one running out of bars
      let a = from;
      for (;;) {
        const sw = s.pending ? s.pendingAt : Infinity, ex = s.layer ? s.until : Infinity;
        const ev = Math.min(sw, ex);
        if (ev >= to) break;
        this.schedule(s, a, ev);
        a = Math.max(a, ev);
        if (sw <= ex) {
          s.layer = { ...s.pending, startBar: sw }; s.pending = null;
          s.until = sw + (s.layer.bars ?? Infinity);
          this.onSwitch?.(i, s.layer);
        } else {
          const done = s.layer; s.layer = null; s.until = Infinity;
          this.onExpire?.(i, done);
        }
      }
      this.schedule(s, a, to);
    });
    this.cursor = to;
  }

  schedule(s, a, b) {
    if (!s.layer?.pattern || s.mute || this.muteC || b <= 0) return;
    a = Math.max(0, a);
    if (b <= a) return;
    const cps = this.bpm / 240;
    for (const h of s.layer.pattern.queryArc(a, b)) {
      if (!h.hasOnset() || h.whole.begin < a) continue;
      const at = h.whole.begin.valueOf(), level = this.level?.(s.layer, at) ?? 1;
      const value = { ...h.value, gain: (h.value.gain ?? 1) * this.gainC * level };
      superdough(value, this.timeOf(at), h.duration.valueOf() * this.barSec, cps).catch(() => {});
    }
  }
}
