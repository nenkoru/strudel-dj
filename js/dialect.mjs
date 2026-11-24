// Strict parser for the loop dialect (see ../DIALECT.md). Model output is never evaluated as
// JavaScript: only whitelisted calls are recognised and rebuilt through the Strudel API.
import * as core from '@strudel/core';
import { mini } from '@strudel/mini';

const SOURCES = new Set(['note', 's', 'n', 'sound']);
const METHODS = new Set(['s', 'bank', 'gain', 'velocity', 'lpf', 'hpf', 'lpq', 'room', 'size', 'delay',
  'delaytime', 'delayfeedback', 'attack', 'decay', 'sustain', 'release', 'pan', 'legato', 'speed',
  'crush', 'shape', 'transpose', 'n', 'octave', 'clip',
  'arp', 'struct', 'mask', 'segment',  // guest-part styles (deckc/src/compose.mjs STYLES): arpeggios, stabs, gates, fills
  // synth voices (compose.mjs SYNTHS): native-node shaping only, see research_notes/sounds_synthesis.md
  'lpenv', 'lpattack', 'lpdecay', 'lpsustain', 'lprelease', 'fanchor', 'hpq', 'bpf', 'bpq',
  'fm', 'fmh', 'fmattack', 'fmdecay', 'fmsustain', 'fmwave', 'vib', 'vibmod', 'penv', 'pattack', 'pdecay', 'panchor',
  'vowel', 'orbit', 'postgain',
  // a silent lane on the track's kicks ducks the guest orbit (deckc/src/compose.mjs PUMP): superdough's
  // orbit ducking is plain gain automation, no worklet
  'duckorbit', 'duckdepth', 'duckattack', 'duckonset']);
// numeric arguments kept where they cannot blow up the mix: biquad Q is in dB, FM index and pitch
// envelopes past these are noise, orbits beyond 8 multiply reverbs
const CLAMP = { lpq: [0, 15], hpq: [0, 15], bpq: [0, 15], fm: [0, 12], penv: [-24, 24], orbit: [1, 8], postgain: [0, 1.5],
  delayfeedback: [0, 0.8], gain: [0, 1.5], room: [0, 1], size: [0, 8], duckorbit: [1, 8], duckdepth: [0, 1],
  duckattack: [0.002, 1], duckonset: [0, 0.5], transpose: [-36, 36], octave: [-3, 3] };
const LIMITS = { code: 4000, string: 2000, lanes: 8, methods: 18, eventsPerCycle: 256, cycles: 4 };

function tokenize(src) {
  const toks = [];
  const re = /\s+|\/\/[^\n]*|([A-Za-z_]\w*)|(-?\d+(?:\.\d+)?)|"([^"\\\n]*)"|([(),.])|(.)/gy;
  for (let m; (m = re.exec(src)) && m[0];) {
    if (m[5] !== undefined) throw Error(`Unexpected character ${JSON.stringify(m[5])} at ${m.index}`);
    if (m[1]) toks.push({ t: 'id', v: m[1] });
    else if (m[2]) toks.push({ t: 'num', v: +m[2] });
    else if (m[3] !== undefined) toks.push({ t: 'str', v: m[3] });
    else if (m[4]) toks.push({ t: m[4] });
  }
  return toks;
}

export function parse(src) {
  if (typeof src !== 'string' || src.length > LIMITS.code) throw Error('Code missing or too long');
  const toks = tokenize(src);
  let i = 0;
  const peek = () => toks[i] || { t: 'eof' };
  const take = (t) => { if (peek().t !== t) throw Error(`Expected ${t}, got ${peek().t}`); return toks[i++]; };
  const lane = () => {
    const name = take('id').v;
    if (!SOURCES.has(name)) throw Error(`Unknown function ${name}`);
    take('('); const arg = take('str').v; take(')');
    const methods = [];
    while (peek().t === '.') {
      i++;
      const m = take('id').v;
      if (!METHODS.has(m)) throw Error(`Method not allowed: ${m}`);
      take('(');
      let a = peek().t === 'num' ? take('num').v : take('str').v;
      if (typeof a === 'number' && CLAMP[m]) a = Math.min(CLAMP[m][1], Math.max(CLAMP[m][0], a));
      take(')');
      methods.push([m, a]);
      if (methods.length > LIMITS.methods) throw Error('Too many methods');
    }
    return { source: name, mini: arg, methods };
  };
  let lanes;
  if (peek().t === 'id' && peek().v === 'stack') {
    i++; take('(');
    lanes = [lane()];
    while (peek().t === ',') { i++; if (peek().t === ')') break; lanes.push(lane()); }
    take(')');
  } else lanes = [lane()];
  if (peek().t !== 'eof') throw Error(`Trailing input: ${peek().t}`);
  if (lanes.length > LIMITS.lanes) throw Error('Too many lanes');
  return lanes;
}

// transpose and octave by a number of semitones or octaves: Strudel's own transpose comes with
// @strudel/tonal (not installed: it threw "pat[m] is not a function"), and superdough ignores octave
// on synths. Note names become MIDI numbers.
const shiftBy = (pat, semis) => pat.withValue((v) => {
  const m = typeof v.note === 'string' ? core.noteToMidi(v.note) : v.note;
  return typeof m === 'number' ? { ...v, note: m + semis } : v;
});

// struct as sample-and-hold: each hit of the rhythm plays the notes that last began at or before it
// (looking back up to a bar). Strudel's own struct keeps only notes that begin exactly on a hit, and
// the guest styles (stabs, gates, vocal chops: deckc/src/compose.mjs STYLES) put their hits over melodies
// that rest or sustain there: 0 of 4 hits sounded in a test, whole parts came out silent.
const hold = (src, rhythm) => new core.Pattern((state) => {
  const out = [];
  for (const x of rhythm.query(state)) {
    if (!x.whole || !x.value || x.value === '~') continue;
    const at = x.whole.begin;
    const back = src.query(state.setSpan(new core.TimeSpan(at.sub(1), at.add(core.Fraction(1, 1024)))))
      .filter((h) => h.whole && h.whole.begin.lte(at) && h.hasOnset());
    if (!back.length) continue;
    const last = back.reduce((m, h) => (h.whole.begin.gt(m) ? h.whole.begin : m), back[0].whole.begin);
    for (const h of back) if (h.whole.begin.eq(last)) out.push(new core.Hap(x.whole, x.part, h.value, h.combineContext(x)));
  }
  return out;
});

function buildLane({ source, mini: text, methods }) {
  if (text.length > LIMITS.string) throw Error('Pattern string too long');
  let pat = core[source](mini(text));
  for (const [m, a] of methods) {
    if (m === 'transpose' || m === 'octave') {
      if (typeof a !== 'number') throw Error(`${m} takes a number`);
      pat = shiftBy(pat, m === 'octave' ? 12 * a : a);
    } else if (m === 'struct') pat = hold(pat, typeof a === 'string' ? mini(a) : core.pure(a));
    else pat = pat[m](typeof a === 'string' ? mini(a) : a);
  }
  return pat;
}

// Returns { lanes, pattern } or throws with a reason a reward function can count.
export function compile(src) {
  const lanes = parse(src).map(buildLane);
  const pattern = lanes.length === 1 ? lanes[0] : core.stack(...lanes);
  for (let c = 0; c < LIMITS.cycles; c++) {
    if (pattern.queryArc(c, c + 1).length > LIMITS.eventsPerCycle) throw Error('Too many events per cycle');
  }
  return { lanes, pattern };
}

export function midiOf(v) {
  if (typeof v.note === 'number') return v.note;
  if (typeof v.note === 'string') return core.noteToMidi(v.note);
  if (typeof v.n === 'number') return v.n + 48;
  return null;
}

// Onset events of each lane over `cycles` bars: {lane, begin (in bars), dur, midi, s}.
export function events(src, cycles = LIMITS.cycles) {
  const { lanes } = compile(src);
  return lanes.flatMap((p, lane) => p.queryArc(0, cycles).filter((h) => h.hasOnset()).map((h) => ({
    lane, begin: h.whole.begin.valueOf(), dur: h.duration.valueOf(), midi: midiOf(h.value), s: h.value.s ?? null,
  })));
}
