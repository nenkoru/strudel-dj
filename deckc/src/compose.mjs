// A guest-deck part from the tiny model (tiny/): prompt, drafts, snap to the 16th grid, cut into
// dance loops, keep the loop that fits the style and the track's energy, add the page's sound.
// Shared by the demo page and the rating page.
//
// Raw drafts sounded off-beat: the model's bar groups often add up to 15 or 20 steps instead of 16,
// so notes fell between 16ths. A draft is read back as events, snapped to 16ths and re-encoded.
import { compile } from '../../js/dialect.mjs';

const NOTE_NAMES = ['c', 'db', 'd', 'eb', 'e', 'f', 'gb', 'g', 'ab', 'a', 'bb', 'b'];
export const MODEL_NOTES = ['c', 'c#', 'd', 'eb', 'e', 'f', 'f#', 'g', 'ab', 'a', 'bb', 'b'];
const PCS = { c: 0, 'c#': 1, db: 1, d: 2, 'd#': 3, eb: 3, e: 4, f: 5, 'f#': 6, gb: 6, g: 7, 'g#': 8, ab: 8, a: 9, 'a#': 10, bb: 10, b: 11 };
const STYLE_TAG = { house: 'house', progressive: 'prog', techno: 'techno' };
// no kick (the track has one) and no crash (a loop repeats it every bar)
const DRUM_KIT = { sd: 'clap', cp: 'clap', hh: 'tight_hat', oh: 'open_hat', rim: 'rim', lt: 'tom', mt: 'tom', ht: 'tom', rd: 'ride' };
// Guest percussion sits on top of a full track: one voice when it is quiet, two at most, each as loud
// as the page's ready-made layer of that sound. Five voices at 0.45 burst into the phrase.
const VOICE_GAIN = { clap: 0.5, tight_hat: 0.3, open_hat: 0.42, rim: 0.45, tom: 0.42, ride: 0.35, shaker: 0.4, house_hat: 0.32, trackhat: 0.9,
  bongo_hi: 0.5, bongo_lo: 0.5, conga: 0.55, quinto: 0.5, claves: 0.4, cowbell: 0.35, agogo: 0.35, shaker2: 0.4, tamb: 0.35, tambshake: 0.35,
  woodblock: 0.4, clap2: 0.45, triangle: 0.3, cabasa: 0.35, darbuka: 0.5 };
const maxVoices = () => 2;  // one voice alone read as too sparse in the ratings, even where the track is quiet

// Timbres per role, one picked per part: one sound per style got tiresome over a rating session, and
// bare oscillators stood out from the finished track, so the synths are filtered and given some room
// to sit behind it, and drums sometimes use the track's own hat (OWN: `trackhat`, cut from the playing
// track by engine.useTrackSounds); then the style's sound (HOME), then the rest.
// The name goes into rating rows so the ratings say which sounds fit. Drum kits swap sample names in
// the finished code. (supersaw was dropped: its worklet loads from a data: URL a page may refuse.)
export const VOICES = {
  bass: {
    saw: '.s("sawtooth").lpf(450).decay(0.12).sustain(0.1).gain(0.5)',
    square: '.s("square").lpf(600).decay(0.2).sustain(0.2).gain(0.5)',
    acid: '.s("sawtooth").lpf("<500 900 1400 900>").lpq(12).decay(0.12).sustain(0.1).gain(0.42)',
    pluck: '.s("triangle").decay(0.15).sustain(0).shape(0.3).gain(0.55)',
    sub: '.s("sine").decay(0.3).sustain(0.5).shape(0.25).gain(0.6)',
    lately: '.s("lately").clip(1).lpf(2000).gain(0.6)',  // the TX81Z house bass (deckc/instruments.py)
    synbass1: '.s("synbass1").clip(1).lpf(1800).gain(0.6)', synbass2: '.s("synbass2").clip(1).lpf(2200).gain(0.6)',
    fretless: '.s("fretless").clip(1).gain(0.6)',
    // played basses (FluidR3): finger, pick, slap, upright
    fingerbass: '.s("fingerbass").clip(1).gain(0.6)', pickbass: '.s("pickbass").clip(1).gain(0.6)',
    slapbass: '.s("slapbass").clip(1).gain(0.55)', upright: '.s("upright").clip(1).room(0.15).gain(0.65)',
  },
  lead: {
    triangle: '.s("triangle").decay(0.3).sustain(0.2).delay(0.3).room(0.3).gain(0.4)',
    saw: '.s("sawtooth").lpf(1800).decay(0.15).sustain(0).delay(0.3).room(0.35).gain(0.28)',
    square: '.s("square").lpf(1200).decay(0.1).sustain(0).delay(0.4).room(0.4).gain(0.26)',
    bell: '.s("sine").decay(0.5).sustain(0).delay(0.3).room(0.5).gain(0.5)',
    // sampled instruments (deckc/instruments.py, all at one loudness): electric pianos, a fifths stab, synth brass
    wurli: '.s("wurli").clip(1).room(0.3).gain(0.6)',
    dxpiano: '.s("dxpiano").clip(1).room(0.3).delay(0.2).gain(0.6)',
    fmpiano: '.s("fmpiano").clip(1).room(0.35).gain(0.6)',
        brass: '.s("brass").clip(1).room(0.3).gain(0.6)',
    // General MIDI (FluidR3): keys, organs, mallets, plucks, hits
    ep1: '.s("ep1").clip(1).room(0.3).gain(0.6)', ep2: '.s("ep2").clip(1).room(0.3).delay(0.2).gain(0.6)',
    organ: '.s("organ").clip(1).room(0.25).gain(0.6)', porgan: '.s("porgan").clip(1).room(0.25).gain(0.6)',
    clav: '.s("clav").clip(1).room(0.2).gain(0.6)', vibes: '.s("vibes").room(0.4).delay(0.25).gain(0.6)',
    marimba: '.s("marimba").room(0.3).gain(0.6)', kalimba: '.s("kalimba").room(0.4).delay(0.25).gain(0.6)',
    musicbox: '.s("musicbox").room(0.5).delay(0.3).gain(0.6)',
    pizz: '.s("pizz").room(0.3).gain(0.6)', brasssec: '.s("brasssec").clip(1).room(0.3).gain(0.6)',
  },
  solo: {
    sax: '.s("sax").clip(1).room(0.5).delay(0.25).gain(0.7)',
    square: '.s("square").lpf(1500).decay(0.25).sustain(0.3).delay(0.4).room(0.5).gain(0.28)',
    flute: '.s("sine").attack(0.06).sustain(0.7).release(0.3).room(0.6).delay(0.3).gain(0.5)',
    soft: '.s("triangle").attack(0.01).sustain(0.5).release(0.2).room(0.5).gain(0.45)',
    // sampled instruments: keys, a calliope lead, pads and a choir for long notes
    wurli: '.s("wurli").clip(1).room(0.4).delay(0.25).gain(0.6)',
    fmpiano: '.s("fmpiano").clip(1).room(0.4).delay(0.25).gain(0.6)',
            strings: '.s("strings").clip(1).room(0.5).gain(0.5)',
            // General MIDI (FluidR3): keys, mallets, pads, voices, strings, flute
    ep1: '.s("ep1").clip(1).room(0.4).delay(0.25).gain(0.6)', organ: '.s("organ").clip(1).room(0.4).gain(0.6)',
    vibes: '.s("vibes").room(0.5).delay(0.3).gain(0.6)', kalimba: '.s("kalimba").room(0.5).delay(0.3).gain(0.6)',
    marimba: '.s("marimba").room(0.4).delay(0.2).gain(0.6)', musicbox: '.s("musicbox").room(0.6).delay(0.3).gain(0.6)',
    ensemble: '.s("ensemble").clip(1).room(0.5).gain(0.5)', warmpad: '.s("warmpad").clip(1).room(0.5).gain(0.5)',
    polysynth: '.s("polysynth").clip(1).room(0.4).gain(0.5)', halo: '.s("halo").clip(1).room(0.6).gain(0.5)',
    aahs: '.s("aahs").clip(1).room(0.6).gain(0.5)', oohs: '.s("oohs").clip(1).room(0.6).gain(0.5)',
    brasssec: '.s("brasssec").clip(1).room(0.4).gain(0.6)',
  },
  // stabs and chords: house organ and piano stabs, dub chords, strings, brass, hits
  chords: {
    organ: '.s("organ").clip(1).room(0.25).gain(0.5)', porgan: '.s("porgan").clip(1).room(0.25).gain(0.55)',
    ep1: '.s("ep1").clip(1).room(0.3).gain(0.6)', ep2: '.s("ep2").clip(1).room(0.3).gain(0.6)', wurli: '.s("wurli").clip(1).room(0.3).gain(0.6)',
    dxpiano: '.s("dxpiano").clip(1).room(0.3).delay(0.25).gain(0.55)', polysynth: '.s("polysynth").clip(1).room(0.3).gain(0.5)',
    dub: '.s("polysynth").clip(1).lpf(1200).delay(0.5).delayfeedback(0.6).room(0.5).gain(0.5)',
    strings: '.s("ensemble").clip(1).room(0.4).gain(0.5)', brass: '.s("brasssec").clip(1).room(0.3).gain(0.5)',
    stab: '.s("sawtooth").lpf(1600).decay(0.15).sustain(0).room(0.3).gain(0.2)',
  },
  drums: {
    track: { tight_hat: 'trackhat', open_hat: 'trackhat', shaker: 'trackhat' },
    // hand percussion (deckc/perc.py, VCSL): the model's drum voices played on other instruments
    latin: { tom: 'conga', rim: 'claves', clap: 'bongo_hi', tight_hat: 'shaker2', ride: 'agogo', open_hat: 'tambshake' },
    perc: { tight_hat: 'cabasa', open_hat: 'tamb', rim: 'cowbell', clap: 'clap2', tom: 'darbuka', ride: 'triangle' },
    wood: { tight_hat: 'shaker2', rim: 'woodblock', clap: 'clap2', tom: 'bongo_lo', ride: 'cowbell', open_hat: 'tamb' },
    kit: {},
    shaker: { tight_hat: 'shaker' },
    house: { tight_hat: 'house_hat', clap: 'rim' },
  },
};
// `chop` (lead and solo cut from the track) went 0 for 15 in the owner's swipes, often skipped within
// seconds, and was taken out; the track's hat stays for drums while it has no verdict yet.
const OWN = { drums: 'track' };
const HOME = { bass: { house: 'fingerbass', progressive: 'lately', techno: 'acid' }, lead: { house: 'ep1', progressive: 'polysynth', techno: 'porgan' },
  solo: { house: 'sax', progressive: 'ep1', techno: 'vibes' }, chords: { house: 'organ', progressive: 'polysynth', techno: 'dub' },
  drums: { house: 'kit', progressive: 'kit', techno: 'kit' } };
// bare oscillators: "the AI bass sounds very synthy" (the owner); they stay, at a third of a sample's odds
// Synth voices from verified recipes (research_notes/sounds_synthesis.md, rendered through superdough
// 1.2.6): the owner found the sounds "too simple". Only native Web Audio nodes (filter and pitch
// envelopes, FM, additive partials, vibrato, vowel filters, delay, room): supersaw, pulse, the ladder
// filter, distortion and tremolo run as AudioWorklets loaded from data: URLs the artifact may refuse.
// They are complete sounds: the role's FX and the model's effect words are not added on top (SYNTHS).
const SYNTHS = {
  bass: {
    acid303: '.s("sawtooth").lpf(320).lpq(13).lpenv("<3 5 4 6>").lpdecay(0.14).lpsustain(0).decay(0.18).sustain(0.5).release(0.03).gain(0.55)',
    clicksub: '.s("sine").penv(-12).pdecay(0.02).panchor(0).decay(0.3).sustain(0.7).release(0.06).lpf(220).gain(0.8)',
    talkbass: '.s("sawtooth").vowel("<a o e i>").lpf(1500).lpq(2).decay(0.15).sustain(0.4).release(0.03).gain(1.0)',
    envbass: '.s("sawtooth").lpf(380).lpq(5).lpenv(3).lpdecay(0.12).lpsustain(0.2).decay(0.2).sustain(0.4).release(0.04).gain(0.8)',
  },
  chords: {
    dhstab: '.s("sawtooth").lpf(500).lpq(4).lpenv(4).lpdecay(0.15).lpsustain(0).decay(0.25).sustain(0).release(0.05).delay(0.3).room(0.3).size(3).gain(0.6)',
    organ7: '.s("square").n(7).lpf(3000).lpq(1).decay(0.2).sustain(0.15).release(0.05).room(0.25).gain(0.35)',
    dubchord: '.s("sawtooth").hpf(180).lpf(700).lpq(3).lpenv(2.5).lpdecay(0.2).lpsustain(0).decay(0.3).sustain(0).delay("0.55:0.375:0.65").room(0.6).size(6).orbit(3).gain(0.38)',
    warmsaw: '.s("sawtooth").n(6).lpf(1400).lpq(1).attack(0.3).sustain(1).release(1.2).hpf(150).room(0.5).size(5).gain(0.18)',
  },
  lead: {
    sawpluck: '.s("sawtooth").lpf(350).lpq(6).lpenv(5).lpdecay(0.12).lpsustain(0).decay(0.14).sustain(0).release(0.04).delay(0.4).room(0.3).size(3).gain(0.8)',
    fmpluck: '.s("triangle").fm(3).fmh(2).fmdecay(0.08).fmsustain(0).decay(0.18).sustain(0).release(0.05).delay(0.25).room(0.2).gain(0.8)',
    fmbell: '.s("sine").fm(6).fmh(3.5).fmdecay(0.5).fmsustain(0).decay(1).sustain(0).release(0.6).delay(0.35).room(0.5).size(5).gain(0.5)',
    proglead: '.s("sawtooth").vib("5:0.12").penv(-2).pattack(0.06).panchor(1).attack(0.02).sustain(0.8).release(0.4).lpf(3000).delay(0.35).room(0.5).size(5).gain(0.35)',
  },
  solo: {
    fmbell: '.s("sine").fm(6).fmh(3.5).fmdecay(0.5).fmsustain(0).decay(1).sustain(0).release(0.6).delay(0.35).room(0.5).size(5).gain(0.5)',
    proglead: '.s("sawtooth").vib("5:0.12").penv(-2).pattack(0.06).panchor(1).attack(0.02).sustain(0.8).release(0.4).lpf(3000).delay(0.35).room(0.5).size(5).gain(0.35)',
    vowelpad: '.s("sawtooth").vowel("<a e o>").lpf(1800).attack(0.2).sustain(0.8).release(0.6).room(0.5).size(5).gain(0.2)',
  },
};
for (const [role, vs] of Object.entries(SYNTHS)) Object.assign(VOICES[role], vs);
// Analog synth samples (deckc/modular.py: Modular Samples, CC0): Juno, JX-3P/8P, SH-2, Jupiter-4, Xpander,
// Minitaur single notes, levelled like the other instruments.
const ANALOG = {
  bass: { junobass: '.s("junobass").clip(1).lpf(2000).gain(0.6)', sh2bass: '.s("sh2bass").clip(1).lpf(1800).gain(0.6)',
    snapbass: '.s("snapbass").clip(1).gain(0.6)', moogbass: '.s("moogbass").clip(1).lpf(1600).gain(0.6)' },
  chords: { ravestab: '.s("ravestab").clip(1).room(0.3).gain(0.5)', bigstack: '.s("bigstack").clip(1).room(0.3).gain(0.45)',
    junopad: '.s("junopad").clip(1).release(0.6).room(0.5).size(4).gain(0.45)', darkpad: '.s("darkpad").clip(1).release(0.6).room(0.5).size(4).gain(0.45)',
    unipad: '.s("unipad").clip(1).release(0.6).room(0.5).size(4).gain(0.45)', brassy: '.s("brassy").clip(1).room(0.3).gain(0.45)',
    junopluck: '.s("junopluck").room(0.3).delay(0.3).gain(0.5)' },
  lead: { junopluck: '.s("junopluck").room(0.3).delay(0.3).gain(0.55)', buzzlead: '.s("buzzlead").clip(1).delay(0.3).room(0.3).gain(0.5)',
    brassy: '.s("brassy").clip(1).room(0.3).gain(0.5)' },
  solo: { junopad: '.s("junopad").clip(1).release(0.6).room(0.5).size(4).gain(0.45)', junopluck: '.s("junopluck").room(0.4).delay(0.3).gain(0.55)',
    buzzlead: '.s("buzzlead").clip(1).delay(0.3).room(0.4).gain(0.5)', unipad: '.s("unipad").clip(1).release(0.6).room(0.5).gain(0.45)' },
};
for (const [role, vs] of Object.entries(ANALOG)) Object.assign(VOICES[role], vs);

const SYNTH_NAMES = new Set(Object.values(SYNTHS).flatMap((vs) => Object.keys(vs)));

const OSC = new Set(['saw', 'square', 'acid', 'pluck', 'sub', 'triangle', 'bell', 'flute', 'soft', 'stab']);
export function pickVoice(role, family, rnd = Math.random) {
  const own = OWN[role], home = HOME[role][family] ?? Object.keys(VOICES[role])[0];
  const rest = Object.keys(VOICES[role]).filter((v) => v !== home && v !== own), r = rnd();
  if (own && r < 0.2) return own;
  if (r < (own ? 0.4 : 0.2)) return home;
  const w = rest.map((v) => (OSC.has(v) ? 1 / 3 : 1)), total = w.reduce((a, b) => a + b, 0);
  let x = rnd() * total;
  for (let i = 0; i < rest.length; i++) if ((x -= w[i]) < 0) return rest[i];
  return rest.at(-1);
}
// A second lane on the same notes, as producers stack a part from layers that each own a band (reports/
// Продюсерские приёмы для гостевых партий.md): a sine sub under the bass, which is then high-passed so the
// two do not fight, and which leaves the beat's first 16th to the kick when the track has one; air on
// chords and stabs (a thin bright saw an octave up, panned); a twin 12 cents off for pads; a triangle an
// octave over a lead. The older second timbres (a pad, bell or strings an octave up) stay in the pool.
// `shift` in semitones (a fraction detunes), `main` is added to the part's own lane.
const LAYERS = { bass: ['sub', 'sub', 'sub'], lead: ['octup', 'octup', 'warmpad', 'vibes', 'halo', 'strings'],
  solo: ['octup', 'warmpad', 'strings', 'oohs', 'vibes'], chords: ['air', 'air', 'twin', 'warmpad', 'ensemble', 'aahs'] };
const NO_SUB = new Set(['sub', 'clicksub', 'acid303']);  // already a sine at the bottom, or a line an octave up
export function pickLayer(role, voice, rnd = Math.random) {
  if (!LAYERS[role] || rnd() > (role === 'bass' ? 0.6 : 0.55) || (role === 'bass' && NO_SUB.has(voice))) return null;
  const pool = LAYERS[role].filter((v) => v !== voice);
  return pool[Math.floor(rnd() * pool.length)] ?? null;
}
const LAYER_SOUND = {
  sub: { shift: 0, sound: '.s("sine").lpf(160).decay(0.3).sustain(0.6).release(0.05).gain(0.45)', main: '.hpf(110)', kick: '.mask("[0 1 1 1]*4")' },
  air: { shift: 12, sound: '.s("sawtooth").hpf(2800).decay(0.12).sustain(0.1).release(0.1).pan(0.65).gain(0.07)' },
  twin: { shift: 0.12, sound: '.s("sawtooth").hpf(250).lpf(1800).attack(0.2).sustain(0.8).release(0.8).pan(0.3).room(0.5).size(4).gain(0.1)' },
  octup: { shift: 12, sound: '.s("triangle").decay(0.15).sustain(0).delay(0.3).room(0.3).pan(0.6).gain(0.15)' },
  warmpad: { shift: 12, sound: '.s("warmpad").clip(1).room(0.5).gain(0.25)' }, vibes: { shift: 12, sound: '.s("vibes").room(0.5).gain(0.3)' },
  halo: { shift: 12, sound: '.s("halo").clip(1).room(0.6).gain(0.25)' }, strings: { shift: 12, sound: '.s("ensemble").clip(1).room(0.4).gain(0.25)' },
  oohs: { shift: 12, sound: '.s("oohs").clip(1).room(0.6).gain(0.25)' }, ensemble: { shift: 12, sound: '.s("ensemble").clip(1).room(0.4).gain(0.25)' },
  aahs: { shift: 12, sound: '.s("aahs").clip(1).room(0.6).gain(0.25)' },
};
// The guest orbit ducked on the track's kicks, the sidechain pump of house and techno: a silent lane
// on every beat (postgain 0) that ducks orbit 1, as deep as the role sits under the kick. Only where the
// track has a kick (deckc/hear.py); superdough's ducking is gain automation in the browser (offline
// renders do not hear it).
const PUMP = { bass: 0.6, chords: 0.4, lead: 0.25, solo: 0.2 };
const pumpLane = (role) => `s("house_kick*4").orbit(8).duckorbit(1).duckdepth(${PUMP[role]}).duckattack(0.16).postgain(0)`;

// Ear candy over a part's phrase (deckc/perc.py one-shots), the "dope" moments the owner asked for: each
// a one-shot on a fixed spot of the 8 bars. Half the parts get one or two.
const CANDY = {
  riser: '<~ ~ ~ ~ ~ ~ riser ~>',            // swells over bar 7 into bar 8
  revcym: '<~ ~ ~ ~ ~ ~ ~ revcym>',          // a reversed cymbal sucking into the next phrase line
  impact: '<impact ~ ~ ~ ~ ~ ~ ~>',          // a sub hit on the phrase line
  downlifter: '<downlifter ~ ~ ~ ~ ~ ~ ~>',
  zap: '<~ ~ ~ [~ ~ ~ zap] ~ ~ ~ [~ zap ~ zap]>',
  sleigh: '<~ ~ ~ [~ ~ ~ sleigh] ~ ~ ~ [~ ~ ~ sleigh]>',
  fingercym: '<~ ~ ~ ~ ~ ~ ~ [~ ~ fingercym ~]>',
  flexatone: '<~ ~ ~ [~ ~ ~ flexatone] ~ ~ ~ ~>',
  slapstick: '<~ ~ ~ ~ ~ ~ ~ [~ ~ ~ slapstick]>',
  guiro: '<~ [~ ~ ~ guiro] ~ ~ ~ [~ ~ ~ guiro] ~ ~>',
  cymswell: '<~ ~ ~ ~ ~ ~ ~ cymswell>',
};
export function pickCandy(rnd = Math.random) {
  if (rnd() < 0.5) return [];
  const names = Object.keys(CANDY), first = names[Math.floor(rnd() * names.length)];
  if (rnd() < 0.6) return [first];
  const others = names.filter((n) => n !== first);
  return [first, others[Math.floor(rnd() * others.length)]];
}
// the sound each style had before VOICES, for a part that names none
export const SOUND = {
  bass: { house: '.s("square").lpf(600).decay(0.2).sustain(0.2).gain(0.5)', progressive: '.s("sawtooth").lpf(450).decay(0.12).sustain(0.1).gain(0.5)',
    techno: '.s("sawtooth").lpf("<500 900 1400 900>").lpq(12).decay(0.12).sustain(0.1).gain(0.42)' },
  lead: { house: '.s("triangle").decay(0.3).sustain(0.2).delay(0.3).room(0.3).gain(0.4)', progressive: '.s("sawtooth").lpf(2200).decay(0.15).sustain(0).delay(0.3).room(0.3).gain(0.3)',
    techno: '.s("square").lpf(1400).decay(0.1).sustain(0).delay(0.4).room(0.4).gain(0.28)' },
  solo: { house: '.s("sax").clip(1).room(0.4).gain(0.75)', progressive: '.s("sax").clip(1).room(0.5).delay(0.25).gain(0.7)',
    techno: '.s("square").lpf(1800).decay(0.25).sustain(0.3).delay(0.4).room(0.5).gain(0.3)' },
};
// The quiet ends were raised after the first ratings: 34 of 51 parts were "meh", mostly "too sparse"
// and "boring", 18 of 21 at the track's quiet phrases.
// Guest decks are there to pump the track up (the owner's brief): effects that build over the 8-bar
// phrase. Patterns run on the global bar grid and parts start on phrase lines, so "<8 steps>" are
// the bars of a phrase: a kick-ducked level (a sidechain feel), a filter that opens towards the next
// phrase where the track is below its peak, an echo thrown on the phrase's last bar.
const FX = {
  bass: (e) => '.velocity("[0.5 0.85 1 0.9]*4")' + (e < 0.75 ? '.lpf("<300 380 460 560 680 820 1000 1250>")' : ''),
  lead: (e) => '.velocity("[0.55 0.85 1 0.9]*4")' + (e < 0.75 ? '.lpf("<500 700 950 1300 1800 2500 3400 4500>")' : '')
    + '.delay("<0.25 0.25 0.25 0.25 0.25 0.25 0.25 0.6>").delayfeedback(0.5)',
  solo: () => '.delay("<0.2 0.2 0.2 0.2 0.2 0.2 0.2 0.55>").delayfeedback(0.45)',
  chords: (e) => (e < 0.75 ? '.lpf("<600 800 1000 1300 1700 2200 2800 3600>")' : '') + '.delay("<0 0 0 0.3 0 0 0 0.5>").delayfeedback(0.4)',
};
// Effect words a model trained with them writes after "|" (tiny/style_corpus.py effects); a draft
// without them gets FX above. Each word is one or two calls, added while the chain stays within the
// dialect's 12 methods.
const FX_WORDS = {
  pump: () => '.velocity("[0.5 0.85 1 0.9]*4")',
  build: (role) => (role === 'drums' ? '.hpf("<1600 1200 900 650 450 300 180 100>")'
    : role === 'bass' ? '.lpf("<300 380 460 560 680 820 1000 1250>")' : '.lpf("<500 700 950 1300 1800 2500 3400 4500>")'),
  throw: () => '.delay("<0.2 0.2 0.2 0.2 0.2 0.2 0.2 0.6>").delayfeedback(0.5)',
  wide: () => '.pan("[0.35 0.65]*4")',
  wash: () => '.room(0.7).size(0.8)',
  acid: () => '.lpf("<400 900 1800 900>").lpq(14)',
  swell: () => '.velocity("<0.45 0.55 0.65 0.75 0.85 0.95 1 1>")',
  // from hybrid DJ/live sets: silence on the last beat before the drop, answer the track (rest in
  // bars 3-4 and 7), thin the layer towards the drop, leave, echo throws on bars 4 and 8, trance gate
  cut: () => '.velocity("<1 1 1 1 1 1 1 [1 1 1 0]>")',
  call: () => '.velocity("<1 1 0 0 1 1 0 1>")',
  rise: () => '.hpf("<150 250 400 650 1000 1600 2500 4000>")',
  fade: () => '.velocity("<1 0.9 0.8 0.65 0.5 0.4 0.3 0.2>")',
  dub: () => '.delay("<0 0 0 0.6 0 0 0 0.6>").delayfeedback(0.65)',
  gate: () => '.velocity("[1 0.3 0.8 0.3]*4")',
};
const methods = (code) => (code.match(/\.\w+\(/g) || []).length;
function withFx(chain, role, words) {
  for (const w of words) {
    const next = chain + (FX_WORDS[w]?.(role) ?? '');
    if (methods(next) <= 11) chain = next;
  }
  return chain;
}

// A part is written a notch above the track's energy (it should lift, not just follow): the
// quietest phrase still gets a "mid"-ish part, the peak the densest one.
export const drive = (energy) => 0.3 + 0.7 * energy;

const DENSITY = {  // onsets per bar at the track's quietest and loudest
  bass: { house: [4, 8], progressive: [6, 12], techno: [6, 14] },
  lead: { house: [4, 7], progressive: [5, 10], techno: [4, 8] },
  solo: { house: [4, 7], progressive: [4, 7], techno: [4, 6] },
  drums: { house: [6, 12], progressive: [7, 14], techno: [7, 16] },
  chords: { house: [2, 6], progressive: [2, 5], techno: [1, 4] },  // stabs: a few hits a bar
};
const ODD16 = { bass: { house: 0.8, progressive: 0.4, techno: 0.2 }, lead: { house: 0.5, progressive: 0.3, techno: 0.3 },
  solo: { house: 0.2, progressive: 0.2, techno: 0.2 }, drums: { house: 0.4, progressive: 0.2, techno: 0.2 },
  chords: { house: 0.6, progressive: 0.3, techno: 0.4 } };

// `section` (build / drop / break / groove: where in the track the part plays) is understood by
// models fine-tuned on tiny/style_corpus.py --fx; older ones never saw it and get none. `hear` (what
// the track plays: kick low mid top, from deckc/hear.py) only by models trained with it (cfg.hear).
export function promptFor({ role, family, keyPc, minor, energy, section, hear }) {
  const style = STYLE_TAG[family] || 'house', level = energy < 0.4 ? 'lo' : energy < 0.75 ? 'mid' : 'hi';
  const tags = `${style} ${level}${section ? ' ' + section : ''}${hear ? ' on ' + hear : ''}`;
  return role === 'drums' ? `drums ${tags}>` : `${role} ${MODEL_NOTES[keyPc]} ${minor ? 'minor' : 'major'} ${tags}>`;
}

function draftBars(role, mini) {
  const { pattern } = compile(role === 'drums' ? `s("${mini}")` : `note("${mini}")`);
  const bars = [[], [], [], []];
  for (const h of pattern.queryArc(0, 4)) {
    if (!h.hasOnset()) continue;
    const b = h.whole.begin.valueOf(), step = Math.round(b * 16);
    if (step >= 64) continue;
    const v = role === 'drums' ? DRUM_KIT[h.value.s] : String(h.value.note);
    if (!v || (role !== 'drums' && !/^[a-g](#|b)?\d$/.test(v))) continue;  // the kick, misspelled sounds, drum names in a melody
    bars[Math.floor(step / 16)].push({ step: step % 16, len: Math.max(1, Math.round((h.whole.end.valueOf() - b) * 16)), v });
  }
  if (role !== 'bass' && role !== 'solo') return bars;
  // one voice: the model writes chords into bass lines (MidiCaps basses double octaves); a bass keeps
  // the lowest note of each step, a solo the highest
  const midi = (v) => { const m = v.match(/^([a-g])(#|b)?(-?\d)/); return m ? PCS[m[1] + (m[2] || '')] + 12 * +m[3] : 0; };
  return bars.map((evs) => {
    const at = new Map();
    for (const e of evs) {
      const x = at.get(e.step);
      if (!x || (role === 'bass' ? midi(e.v) < midi(x.v) : midi(e.v) > midi(x.v))) at.set(e.step, e);
    }
    return [...at.values()];
  });
}

// One bar of events as 16 steps of mini-notation: "[c2 ~ c2@2 ~@3 ...]" (tiny/style_corpus.py too).
function encodeBar(evs, hits = false) {
  const at = new Map();
  for (const e of evs) {
    const x = at.get(e.step) || { v: new Set(), len: 16 };
    x.v.add(e.v); x.len = Math.min(x.len, hits ? 1 : e.len); at.set(e.step, x);
  }
  const steps = [...at.keys()].sort((a, b) => a - b), out = [];
  let s = 0;
  const rest = (n) => { if (n > 0) out.push(n > 1 ? `~@${n}` : '~'); };
  steps.forEach((st, i) => {
    rest(st - s);
    const x = at.get(st), len = Math.max(1, Math.min(x.len, (steps[i + 1] ?? 16) - st)), v = [...x.v];
    out.push((v.length > 1 ? `[${v.join(',')}]` : v[0]) + (len > 1 ? `@${len}` : ''));
    s = st + len;
  });
  rest(16 - s);
  return `[${out.join(' ')}]`;
}

function encodeLoop(role, bars) {
  const seq = (bs) => (bs.length === 1 ? bs[0] : `<${bs.join(' ')}>`);
  if (role !== 'drums') return seq(bars.map((b) => encodeBar(b)));
  const sounds = [...new Set(bars.flat().map((e) => e.v))];
  return sounds.map((snd) => seq(bars.map((b) => encodeBar(b.filter((e) => e.v === snd), true)))).join(', ');
}

function scoreLoop(role, family, bars, energy) {
  const fam = family in DENSITY[role] ? family : 'house';
  const [lo, hi] = DENSITY[role][fam], target = lo + (hi - lo) * energy;
  const onsets = bars.map((b) => (role === 'drums' ? b.length : new Set(b.map((e) => e.step)).size));
  // a solo phrase may rest for a bar, but not open with one; other parts play every bar
  if (role === 'solo' ? onsets[0] === 0 : onsets.some((n) => n === 0)) return -Infinity;
  const d = onsets.reduce((a, b) => a + b, 0) / bars.length;
  const all = bars.flat(), odd = all.filter((e) => e.step % 2).length / all.length;
  // a melody needs a few pitches (density alone picked eight repeats of one note); a one-note bass
  // was rated boring, so a bass wants a second note too
  const pitches = new Set(all.map((e) => e.v)).size;
  const tune = role === 'lead' || role === 'solo' ? (pitches < 3 ? -0.6 : Math.min(0.2, 0.05 * (pitches - 3))) : role === 'bass' ? (pitches < 2 ? -0.3 : pitches < 3 ? -0.1 : 0) : 0;
  // half a fill bar: a steady voice that stops for the bar's last beat (its fill sound was dropped),
  // or the fill alone, which a 1-bar loop would repeat every bar
  // one 4-step cell over and over (a rolling one-note bass, an 8th arp) was rated boring
  const cells = new Set(bars.flatMap((b) => [0, 1, 2, 3].map((q) => b.filter((e) => e.step >> 2 === q).map((e) => `${e.step & 3}${e.v}`).join())));
  const same = role === 'bass' || role === 'lead' ? (cells.size === 1 ? 0.25 : cells.size === 2 ? 0.08 : 0) : 0;
  // (a steady voice may stop where another one rolls into the next phrase: a build's snare roll)
  const cut = role !== 'drums' ? 0 : bars.some((b) => [...new Set(b.map((e) => e.v))].some((v) => {
    const st = b.filter((e) => e.v === v).map((e) => e.step), late = st.filter((s) => s >= 12).length;
    return (st.length - late >= 3 && !late && !b.some((e) => e.step >= 12)) || (late >= 3 && late === st.length && bars.length === 1);
  })) ? 0.4 : 0;
  return -Math.abs(d - target) / target - ODD16[role][fam] * odd + tune - cut - same + (bars.length === 1 ? 0.05 : 0);
}

// Pitched notes into the key's scale (the model mixes up major and minor: a note outside moves a
// semitone down) and into a register a phone speaker plays: bass around octave 2-3, melodies 4-5.
// How well a loop sits in the track's pockets (deckc/hear.py pockets): `pocket` is, for the phrase's 8
// bars, how full each band is on each 16th (0..1). A part's onsets should land where its band (the bass
// in the lows, drums in the highs, the rest in the mids) is emptier than that band's average in the bar;
// the result is that difference, negated (positive when the part fills gaps), weighted like the
// critic's other terms.
const POCKET_BAND = { bass: 'low', drums: 'high' };
export function pocketFit(role, bars, pocket) {
  const band = pocket?.[POCKET_BAND[role] ?? 'mid'];
  if (!band) return 0;
  const steps = bars.flatMap((b) => [...new Set(b.map((e) => e.step))]);
  if (!steps.length) return 0;
  const mean = band.reduce((a, x) => a + x, 0) / 16;
  return -1.2 * (steps.reduce((a, st) => a + band[st], 0) / steps.length - mean);
}
// A melody an octave up where the track's mids are full and its highs open (a vocal or chords there).
export const liftOf = (role, pocket) => {
  if (!pocket || !['lead', 'solo'].includes(role)) return 0;
  const m = (k) => pocket[k].reduce((a, x) => a + x, 0) / 16;
  return m('mid') > 0.65 && m('high') < 0.4 ? 1 : 0;
};

const NOTE_RE = /(?<![a-z_])([a-g])(#|b)?(\d)/g;
const scaleOf = (minor) => (minor ? [0, 2, 3, 5, 7, 8, 10] : [0, 2, 4, 5, 7, 9, 11]);

// Share of a loop's notes that are in the key's scale (the critic marks the rest down).
export function inKey(mini, keyPc, minor) {
  const pcs = [...mini.matchAll(NOTE_RE)].map((m) => PCS[m[1] + (m[2] || '')]);
  return pcs.length ? pcs.filter((p) => scaleOf(minor).includes(((p - keyPc) % 12 + 12) % 12)).length / pcs.length : 1;
}

// Notes into the key's scale and a register a phone speaker plays (see sound), spelled with `names`
// (the page's for Strudel, MODEL_NOTES for training lines).
export function fitNotes(role, mini, keyPc, minor, names = NOTE_NAMES, lift = 0) {
  const scale = scaleOf(minor);
  const octs = [...mini.matchAll(NOTE_RE)].map((m) => +m[3]).sort((a, b) => a - b);
  const median = octs[octs.length >> 1] ?? 3, want = (role === 'bass' ? 2 : 4) + lift;
  const shift = median < want ? want - median : median > want + 1 ? want + 1 - median : 0;
  return mini.replace(NOTE_RE, (m, l, acc, o) => {
    let p = PCS[l + (acc || '')] + 12 * (+o + shift);
    if (!scale.includes(((p - keyPc) % 12 + 12) % 12)) p -= 1;
    return names[p % 12] + Math.floor(p / 12);
  });
}

function sound(role, family, mini, keyPc, minor, energy, fx = [], voice, layer = null, candy = [], kick = false, lift = 0) {
  const sweets = candy.filter((c) => CANDY[c]).map((c) => `s("${CANDY[c]}").gain(0.45)`);
  const pump = kick && PUMP[role] ? [pumpLane(role)] : [];
  const chains = [...partSound(role, family, mini, keyPc, minor, energy, fx, voice, layer, kick, lift), ...sweets, ...pump];  // one flat stack: the dialect allows no nesting
  return chains.length === 1 ? chains[0] : `stack(${chains.join(', ')})`;
}

function partSound(role, family, mini, keyPc, minor, energy, fx, voice, layer, kick = false, lift = 0) {
  if (role === 'drums') {
    const swap = VOICES.drums[voice] ?? {};
    const voices = mini.split(', ').map((seq) => {
      seq = seq.replace(/[a-z][a-z_]+/g, (name) => swap[name] ?? name);
      const hat = seq.includes('trackhat') ? '.hpf(6500)' : '';  // the cut carries the track's bass and mids: keep the hiss
      return withFx(`s("${seq}").gain(${VOICE_GAIN[seq.match(/[a-z][a-z_]+/)[0]] ?? 0.4})${hat}`, role, fx);
    });
    return voices;
  }
  mini = fitNotes(role, mini, keyPc, minor, NOTE_NAMES, lift);
  const own = SYNTH_NAMES.has(voice);  // a synth voice is a finished sound: no role FX on top
  const chain = (snd) => { const base = `note("${mini}")${snd}`; return own ? base : fx.length ? withFx(base, role, fx) : base + FX[role](energy); };
  const main = chain(VOICES[role][voice] ?? SOUND[role]?.[family] ?? SOUND[role]?.house ?? Object.values(VOICES[role])[0]);
  const lay = layer && LAYER_SOUND[layer];
  if (!lay) return [main];
  // the layer's notes: whole octaves stay names, a detune becomes MIDI numbers ("57.12")
  const shifted = mini.replace(NOTE_RE, (m, l, acc, o) => (Number.isInteger(lay.shift)
    ? `${l}${acc || ''}${+o + lay.shift / 12}` : String(PCS[l + (acc || '')] + 12 * (+o + 1) + lay.shift)));
  return [main + (lay.main ?? ''), `note("${shifted}")${lay.sound}${kick ? lay.kick ?? '' : ''}`];
}

// Drum loops with some of their voices: every subset of up to `max` sounds.
function voiceSubsets(loop, max) {
  const sounds = [...new Set(loop.flat().map((e) => e.v))], out = [];
  for (let mask = 1; mask < 1 << sounds.length; mask++) {
    const keep = sounds.filter((_, i) => mask & (1 << i));
    if (keep.length <= max) out.push(loop.map((b) => b.filter((e) => keep.includes(e.v))));
  }
  return out;
}

// Gain factor for AI percussion `since` bars after it came in, over a track at `energy` (0..1) that
// bar: it eases in over two bars and drops to about a third in a breakdown.
export const drumLevel = (since, energy) => Math.min(1, 0.35 + 0.325 * Math.max(0, since)) * (0.35 + 0.65 * energy);

// What a loop is like, for the learned half of the critic (tiny/reward.py fits it to the ratings).
export function loopFeatures(role, family, loop, energy) {
  const fam = family in DENSITY[role] ? family : 'house', [lo, hi] = DENSITY[role][fam], target = lo + (hi - lo) * drive(energy);
  const all = loop.flat(), onsets = loop.map((b) => new Set(b.map((e) => e.step)).size);
  const cells = new Set(loop.flatMap((b) => [0, 1, 2, 3].map((q) => b.filter((e) => e.step >> 2 === q).map((e) => `${e.step & 3}${e.v}`).join())));
  return {
    density: onsets.reduce((a, b) => a + b, 0) / loop.length / target,
    odd: all.length ? all.filter((e) => e.step % 2).length / all.length : 0,
    pitches: Math.min(8, new Set(all.map((e) => e.v)).size) / 8,
    cells: Math.min(8, cells.size) / 8,
    bars: loop.length / 4,
    energy,
    ...Object.fromEntries(['bass', 'lead', 'solo', 'drums'].map((r) => [r, +(role === r)])),
  };
}

// The best loop cut from one draft: {score, loop, mini, fx}, or null if nothing in it parses.
// Also the critic of the self-improvement loop (tiny/critic.mjs).
export function scoreDraft(draft, opts) {
  const cuts = cutsOf(draft, opts);
  if (!cuts.length) return null;
  const best = cuts.reduce((a, b) => (b.score > a.score ? b : a));
  return { ...best, mini: encodeLoop(opts.role, best.loop), fx: fxOf(draft) };
}

const fxOf = (draft) => (draft.split('|')[1] || '').trim().split(/\s+/).filter((w) => w in FX_WORDS);

// Every loop a draft can be cut into, with its score: runs of its bars and, for drums, sets of its voices.
function cutsOf(draft, { role, family, energy, pocket }) {
  const segments = role === 'solo' ? [[0, 1], [2, 3], [0, 1, 2, 3]] : [[0], [1], [2], [3], [0, 1], [2, 3]];
  let bars;
  try { bars = draftBars(role, draft.split('|')[0]); } catch { return []; }  // unbalanced brackets and the like
  const out = [];
  for (const seg of segments) {
    const loop = seg.map((j) => bars[j]);
    for (const cand of role === 'drums' ? voiceSubsets(loop, maxVoices(energy)) : [loop]) {
      const score = scoreLoop(role, family, cand, drive(energy));
      if (score > -Infinity) out.push({ score: score + pocketFit(role, cand, pocket), loop: cand });
    }
  }
  return out;
}

// The `on` words for a stretch of a track: those heard in at least half of its bars (deckc/hear.py
// gives one string per bar).
export function heardOver(bars) {
  const count = {};
  for (const b of bars) for (const w of (b || '').split(' ')) if (w) count[w] = (count[w] || 0) + 1;
  return ['kick', 'low', 'mid', 'top'].filter((w) => count[w] >= bars.length / 2).join(' ');
}

// How much two loops share, ignoring which bar: the share of (step, note) events either has that both
// have (0 nothing, 1 the same).
export function overlap(a, b) {
  const set = (loop) => new Set(loop.flat().map((e) => `${e.step}:${e.v}`));
  const x = set(a), y = set(b), both = [...x].filter((k) => y.has(k)).length;
  return both / Math.max(1, x.size + y.size - both);
}
const KEEP = 0.55;  // the next phrase of a part keeps about half of what the last one played

// Fresh drafts rarely share half a loop with the last phrase (5-47% in a test), so the next phrase is
// also tried as a cross of the two: each bar's first half from one loop, its second half from the other.
function crossover(a, b) {
  return a.map((bar, j) => [...bar.filter((e) => e.step < 8), ...b[j % b.length].filter((e) => e.step >= 8)]);
}

// A few drafts, each cut into loops; the best-scoring loop wins. With `prev` (the part's last phrase)
// it is that part's next phrase instead: same timbre, the track's energy, section and sound for the
// new phrase, and drafts that keep about half of the last loop win, so it develops rather than jumps.
// Sampling is bolder than it was (0.8): in the owner's swipes, parts sampled at 1.1 fitted 64% of the
// time, at 0.95 54%, at 0.75 38%.
export async function composePart(model, { role, family, keyPc, minor, energy = 0.7, section, hear, drafts = 3, temperature = 1.0, voice = pickVoice(role, family), prev }) {
  section = model.vocab?.includes('|') ? section : undefined;  // effect-trained models know sections
  hear = model.cfg?.hear ? hear : undefined;
  if (prev) voice = prev.voice;
  const prompt = promptFor({ role, family, keyPc, minor, energy: drive(energy), section, hear }), t0 = performance.now();
  const rank = (cut) => cut.score - (prev?.loop ? 1.5 * Math.abs(overlap(prev.loop, cut.loop) - KEEP) : 0);
  let best = null;
  const consider = (cut, draft) => { if (cut && rank(cut) > (best?.rank ?? -Infinity)) best = { ...cut, draft, rank: rank(cut) }; };
  for (let i = 0; i < drafts + 3 && !(best && i >= drafts); i++) {
    let draft, cut;
    try { draft = await model.generate(prompt, { temperature }); cut = scoreDraft(draft, { role, family, energy }); } catch { continue; }
    consider(cut, draft);
    if (cut && prev?.loop) for (const loop of [crossover(prev.loop, cut.loop), crossover(cut.loop, prev.loop)]) {
      if (role === 'drums' && new Set(loop.flat().map((e) => e.v)).size > maxVoices(energy)) continue;
      const score = scoreLoop(role, family, loop, drive(energy));
      if (score > -Infinity) consider({ score, loop, mini: encodeLoop(role, loop), fx: cut.fx }, draft);
    }
  }
  if (!best) {
    if (prev) return { ...prev, seconds: (performance.now() - t0) / 1000 };  // the last phrase again
    throw Error('модель не смогла написать разбираемый паттерн');
  }
  const { fx, mini, loop } = best, code = sound(role, family, mini, keyPc, minor, energy, fx, voice);
  compile(code);
  return { code, mini, fx, voice, loop, draft: best.draft, prompt, score: best.score, energy, seconds: (performance.now() - t0) / 1000,
    ...(prev?.loop ? { overlap: +overlap(prev.loop, loop).toFixed(2) } : {}) };
}

// Bar transforms for phrase forms. Bars are [{step, len, v}], v a note name (or a kit sound for drums).
const toMidi = (v) => { const m = /^([a-g](?:#|b)?)(-?\d)$/.exec(v); return m ? PCS[m[1]] + 12 * (+m[2] + 1) : null; };
const fromMidi = (n) => MODEL_NOTES[((n % 12) + 12) % 12] + (Math.floor(n / 12) - 1);
const up = (bar, semis) => bar.map((e) => { const n = toMidi(e.v); return n == null ? e : { ...e, v: fromMidi(n + semis) }; });
const thin = (bar) => bar.filter((e, i) => e.step % 4 === 0 || i === 0);  // the downbeats (and the first note)
const shift = (bar) => bar.map((e) => ({ ...e, step: (e.step + 2) % 16 })).sort((x, y) => x.step - y.step);  // an 8th later
const fill = (bar) => {  // the last beat as 16ths of the bar's last sound
  const keep = bar.filter((e) => e.step < 12), last = (keep.length ? keep : bar).at(-1);
  return last ? [...keep.map((e) => ({ ...e, len: Math.min(e.len, 12 - e.step) })), ...[12, 13, 14, 15].map((step) => ({ ...last, step, len: 1 }))] : bar;
};
const gap = (bar) => bar.filter((e) => e.step < 12).map((e) => ({ ...e, len: Math.min(e.len, 12 - e.step) }));  // the last beat silent
const stutter = (bar) => { const b1 = bar.filter((e) => e.step < 4); return [0, 4, 8, 12].flatMap((o) => b1.map((e) => ({ ...e, step: e.step + o, len: Math.min(e.len, 4 - e.step) }))); };  // beat one four times
const halve = (bar) => { const h = bar.filter((e) => e.step < 8).map((e) => ({ ...e, len: Math.min(e.len, 8 - e.step) })); return [...h, ...h.map((e) => ({ ...e, step: e.step + 8 }))]; };  // a loop roll: the first half twice
const double = (bar) => { const d = bar.map((e) => ({ ...e, step: e.step >> 1, len: Math.max(1, e.len >> 1) })); return [...d, ...d.map((e) => ({ ...e, step: e.step + 8 }))]; };  // double time
const half = (bar) => bar.filter((e) => e.step < 8).map((e) => ({ ...e, step: e.step * 2, len: e.len * 2 }));  // half time
const push = (bar) => bar.map((e) => ({ ...e, step: (e.step + 1) % 16 })).sort((x, y) => x.step - y.step);  // a 16th later
const pitches = (bar) => bar.map((e) => toMidi(e.v));
const retro = (bar) => { const p = pitches(bar).reverse(); return bar.map((e, i) => (p[i] == null ? e : { ...e, v: fromMidi(p[i]) })); };  // the notes backwards
const invert = (bar) => { const p = pitches(bar), o = p.find((x) => x != null); return bar.map((e, i) => (p[i] == null ? e : { ...e, v: fromMidi(2 * o - p[i]) })); };  // upside down around the first note
const pedal = (bar) => (bar.length ? [{ ...bar[0], step: 0, len: 16 }] : bar);  // the first note held

// How an 8-bar phrase uses its loop A and two answers B and C (variations of A; see composePhrase).
// A form is five independent choices, so a set played twice over the same tracks never comes out the
// same (the owner's wish): 5 x 8 x 6 x 6 x 5 = 7200 combinations per part for pitched roles, on top of
// the model's notes, timbres and effect words. Rows save the form as "shape+pitch+twist+density+ending"
// so the ratings can say which choices work. (k: the bar 0..7)
const SHAPES = {
  plain: () => 'A',                                                // the loop throughout
  answer4: (k) => (k % 4 === 3 ? 'B' : 'A'),                       // A A A A'
  answer2: (k) => (k % 2 === 1 ? 'B' : 'A'),                       // A A' A A'
  abac: (k) => (k % 4 === 1 ? 'B' : k % 4 === 3 ? 'C' : 'A'),      // two different answers
  call: (k) => (k % 4 === 2 ? null : k % 4 === 3 ? (k === 7 ? 'B' : null) : 'A'),  // two bars on, two off
};
const PITCH = {  // semitones per bar; fitNotes snaps the result to the key
  none: [0, 0, 0, 0, 0, 0, 0, 0],
  lift: [0, 0, 0, 0, 12, 12, 12, 12], drop: [0, 0, 0, 0, -12, -12, -12, -12],
  fourth: [0, 0, 0, 0, 5, 5, 5, 5], fifth: [0, 0, 0, 0, 7, 7, 7, 7],
  minorwalk: [0, 0, -4, -4, -2, -2, 0, 0], climb: [0, 0, 3, 3, 5, 5, 7, 7], octaves: [0, 12, 0, 12, 0, 12, 0, 12],
};
const TWIST = { none: (b) => b, mirror: invert, retro, pedal, shift, push };  // on bars 4 and 8
const THICK = {  // how full the bars are over the phrase
  none: (k, b) => b,
  build: (k, b) => (k < 4 ? thin(b) : b), breakdown: (k, b) => (k >= 4 && k < 7 ? thin(b) : b),
  pulse: (k, b) => (k % 2 ? thin(b) : b), halftime: (k, b) => (k < 4 ? half(b) : b), double: (k, b) => (k >= 6 ? double(b) : b),
};
const ENDING = {
  none: (k, b) => b, fill: (k, b) => (k === 7 ? fill(b) : b), stutter: (k, b) => (k === 7 ? stutter(b) : b),
  roll: (k, b) => (k === 6 ? halve(b) : k === 7 ? fill(stutter(b)) : b), gap: (k, b) => (k === 7 ? gap(b) : b),
};
const pickOf = (xs, rnd) => xs[Math.floor(rnd() * xs.length)];
const maybe = (p, xs, rnd) => (rnd() < p ? 'none' : pickOf(xs.filter((x) => x !== 'none'), rnd));
// One or two moves on top of the shape, never more: recipes stacking four or five (call + retro +
// halftime + roll + fourth) went 3 for 13 in the owner's swipes; variety comes from parts differing,
// each one stays simple. The shape is mostly an answer form (`call` and `plain` rarer).
export function pickForm(role, rnd = Math.random) {
  const pitched = role !== 'drums';
  const shape = rnd() < 0.7 ? pickOf(['answer4', 'answer2', 'abac'], rnd) : pickOf(['plain', 'call'], rnd);
  const moves = {
    pitch: pitched ? Object.keys(PITCH).filter((p) => p !== 'none' && !(role === 'bass' && p === 'drop')) : [],
    twist: Object.keys(TWIST).filter((t) => t !== 'none' && (pitched || t === 'shift' || t === 'push')),
    density: Object.keys(THICK).filter((d) => d !== 'none' && !(role === 'solo' && (d === 'double' || d === 'pulse'))),
    ending: Object.keys(ENDING).filter((e) => e !== 'none'),
  };
  const form = { pitch: 'none', twist: 'none', density: 'none', ending: 'none' };
  const n = rnd() < 0.25 ? 0 : rnd() < 0.65 ? 1 : 2;  // how many moves: none, one or two
  const kinds = Object.keys(moves).filter((k) => moves[k].length);
  for (let i = 0; i < n && kinds.length; i++) {
    const k = kinds.splice(Math.floor(rnd() * kinds.length), 1)[0];
    form[k] = pickOf(moves[k], rnd);
  }
  return [shape, form.pitch, form.twist, form.density, form.ending].join('+');
}
function formBars(form, A, B, C) {
  const [shape, pitch, twist, density, ending] = form.split('+');
  return Array.from({ length: 8 }, (_, k) => {
    const which = SHAPES[shape](k);
    let bar = which === null ? [] : { A, B, C }[which][k % { A, B, C }[which].length];
    bar = THICK[density](k, bar);
    if (k % 4 === 3) bar = TWIST[twist](bar);
    bar = up(bar, PITCH[pitch][k]);
    return ENDING[ending](k, bar);
  });
}

// One phrase (8 bars) of a part: a loop that keeps playing, answered every `every` bars (2 or 4) by
// a variation of itself, A A A A' (the owner asked for movement every second or fourth bar). A first
// version built the phrase from different pieces each time and the owner threw nearly all of it out
// (4 of 19: the bass jumped to other notes, solos lost the thread), so the loop is now the part and
// the variation only changes the second half of its bars: a cross of the loop with another cut from
// the drafts that keeps about 60% of it. `prev`: the part's previous phrase, whose loop this one
// develops (as composePart does). As many model calls as composePart, so the phone keeps up.
// Styles: more kinds of guest part made from the roles the model writes (the owner: chords are liked,
// "but I don't want everything to circle around chords"). The model writes the base role's notes; a style
// picks the voice and adds one or two Strudel calls on the part's main lane: arpeggios, stabs, pads and
// trance gates from chords, vocal chops from a solo line, a 16th sequence from a lead, an acid line an
// octave up from a bass, fills (the 4th bar only) from percussion.
const pickOf2 = (xs, rnd) => xs[Math.floor(rnd() * xs.length)];
// `layers`: the second lanes that suit the style (null: none); restyle gives them the style's calls too.
export const STYLES = {
  arp: { base: 'chords', layers: ['air', null], voices: ['junopluck', 'ravestab', 'polysynth', 'dxpiano', 'organ7', 'dhstab'],
    // the chord held on every 16th first (dialect struct: sample-and-hold), so each arp step has one to pick from
    add: (r) => '.struct("x*16")' + pickOf2(['.arp("[0 1 2 1 0 1 2 3]*2")', '.arp("[0 2 1 2]*4")', '.arp("[0 1 2 3]*4")', '.arp("[0 1 2 1]*2")'], r) + '.clip(0.8)' },
  stab: { base: 'chords', layers: ['air', 'air', null], voices: ['ravestab', 'ravestab', 'bigstack', 'dhstab', 'organ7', 'dubchord', 'organ', 'brassy'],
    add: (r, p) => `.struct("${pocketStruct(['[~ x ~ x]', '[x ~ ~ x ~ ~ x ~]', '[~ ~ x ~ ~ x ~ ~]', '<[~ x ~ x] [~ x ~ x ~ x ~ ~]>'], r, p)}")` + '.clip(0.35)' },
  pad: { base: 'chords', layers: ['twin', 'twin', null], voices: ['junopad', 'darkpad', 'unipad', 'warmsaw'], add: () => '.attack(0.4).release(1.5)' },
  gate: { base: 'chords', layers: ['air', null], voices: ['junopad', 'darkpad', 'warmsaw', 'dhstab'],
    add: (r, p) => `.struct("${pocketStruct(['[x ~ x x ~ x ~ x x ~ x x ~ x x ~]', '[x x ~ x x ~ x ~]*2'], r, p)}")` + '.clip(0.6)' },
  // the bar's chord held for the whole bar (arp("0") kept only notes starting on the bar line: 0 of 10 sounded)
  drone: { base: 'chords', layers: ['twin', null], voices: ['darkpad', 'unipad', 'warmsaw'], add: () => '.struct("x").attack(0.8).release(2)' },
  vox: { base: 'solo', voices: ['vowelpad', 'vowelpad', 'oohs', 'aahs'],
    add: (r, p) => `.struct("${pocketStruct(['[~ x ~ ~ x ~ x ~]', '[x ~ ~ x ~ ~ x ~]*2', '[~ ~ x ~]*2'], r, p)}")` + '.clip(0.4)' },
  seq: { base: 'lead', layers: ['octup', null], voices: ['junopluck', 'sawpluck', 'fmpluck', 'fmbell', 'buzzlead', 'dxpiano'], add: () => '.segment(16).clip(0.5)' },
  acid: { base: 'bass', voices: ['acid303'], add: () => '.segment(16)', up: 1 },
  fill: { base: 'drums', voices: ['latin', 'perc', 'wood'], add: () => '.mask("<0 0 0 1>")', lanes: 'all' },
};

// The code with a style applied (the first note(...) lane, or every s(...) lane for fills); the code as it
// was when the result would not compile in the strict dialect.
// A style's rhythm that sits in the track's pockets: of two rhythms drawn at random, the one whose hits
// fall where the mids are emptier (the whole list is not ranked, so a track does not always get one).
function pocketStruct(structs, rnd, pocket) {
  const a = pickOf2(structs, rnd), b = pickOf2(structs, rnd);
  if (!pocket?.mid || a === b) return a;
  const full = (st) => {
    const steps = compile(`note("c4").struct("${st}")`).pattern.queryArc(0, 1).filter((h) => h.hasOnset())
      .map((h) => Math.round(h.whole.begin.valueOf() * 16) % 16);
    return steps.reduce((x, k) => x + pocket.mid[k], 0) / Math.max(1, steps.length);
  };
  return full(a) <= full(b) ? a : b;
}

export function pickStyleLayer(style, rnd = Math.random) {
  const ls = STYLES[style]?.layers ?? [null];
  return ls[Math.floor(rnd() * ls.length)];
}

export function restyle(code, style, rnd = Math.random, pocket) {
  const st = STYLES[style];
  if (!st) return code;
  const add = st.add(rnd, pocket);
  // the end of the lane starting at i: the comma or closing bracket of the enclosing stack, or the end
  const laneEnd = (i) => {
    let depth = 0, q = false;
    for (let j = i; j < code.length; j++) {
      const ch = code[j];
      if (ch === '"') q = !q;
      else if (!q && ch === '(') depth++;
      else if (!q && ch === ')') { if (depth === 0) return j; depth--; }
      else if (!q && ch === ',' && depth === 0) return j;
    }
    return code.length;
  };
  // added at the lane's end, after the voice's own calls (its .clip(1) would undo a stab's short notes)
  // every note lane (a layer follows the style's rhythm), the first only for a line moved up an octave
  const starts = st.lanes === 'all' ? [...code.matchAll(/s\("/g)].map((m) => m.index)
    : st.up ? [code.indexOf('note("')].filter((i) => i >= 0) : [...code.matchAll(/note\("/g)].map((m) => m.index);
  let out = code;
  for (const i of starts.reverse()) {
    const end = laneEnd(i);
    let lane = code.slice(i, end).trimEnd();
    if (st.up) lane = lane.replace(/note\("([^"]*)"\)/, (m, mini) => `note("${mini.replace(NOTE_RE, (_, l, acc, o) => `${l}${acc || ''}${+o + st.up}`)}")`);
    out = out.slice(0, i) + lane + add + out.slice(i + code.slice(i, end).trimEnd().length);
  }
  try { compile(out); return out; } catch { return code; }
}

export async function composePhrase(model, { role, family, keyPc, minor, energy = 0.7, section, hear, drafts = 3, temperature = 1.0, voice = pickVoice(role, family), every = 4, form, prev, layer, candy = pickCandy(), pocket }) {
  form ??= `${every === 2 ? 'answer2' : 'answer4'}+none+none+none+none`;
  const kick = /\bkick\b/.test(hear ?? '');  // what the track plays, whether or not the model reads it
  section = model.vocab?.includes('|') ? section : undefined;
  hear = model.cfg?.hear ? hear : undefined;
  if (prev) voice = prev.voice;
  layer = layer !== undefined ? layer : prev ? prev.layer ?? null : pickLayer(role, voice);  // a part keeps its layer
  const prompt = promptFor({ role, family, keyPc, minor, energy: drive(energy), section, hear }), t0 = performance.now();
  const pool = [];
  let first = null;
  for (let i = 0; i < drafts + 3 && !(pool.length && i >= drafts); i++) {
    let draft;
    try { draft = await model.generate(prompt, { temperature }); } catch { continue; }
    const cuts = cutsOf(draft, { role, family, energy, pocket });
    if (!cuts.length) continue;
    first ??= draft;
    pool.push(...cuts.map((c) => ({ ...c, draft })));
  }
  if (!pool.length) {
    if (prev) return { ...prev, seconds: (performance.now() - t0) / 1000 };
    throw Error('модель не смогла написать разбираемый паттерн');
  }
  // the loop: the best cut, or with `prev` the best that keeps about half of the last phrase's loop
  const cands = [...pool];
  if (prev?.loop) for (const c of pool) for (const loop of [crossover(prev.loop, c.loop), crossover(c.loop, prev.loop)]) {
    if (role === 'drums' && new Set(loop.flat().map((e) => e.v)).size > maxVoices(energy)) continue;
    const score = scoreLoop(role, family, loop, drive(energy));
    if (score > -Infinity) cands.push({ score: score + pocketFit(role, loop, pocket), loop, draft: c.draft });
  }
  const rank = (c) => c.score - (prev?.loop ? 1.5 * Math.abs(overlap(prev.loop, c.loop) - KEEP) : 0);
  const base = cands.reduce((a, b) => (rank(b) > rank(a) ? b : a));
  // its answer: the loop with the second half of its bars from another cut
  const answers = [];  // the two best distinct variations: B, then C
  for (const c of pool) {
    const loop = crossover(base.loop, c.loop), code = encodeLoop(role, loop);
    if (code === encodeLoop(role, base.loop) || answers.some((x) => x.code === code)) continue;
    if (role === 'drums' && new Set(loop.flat().map((e) => e.v)).size > maxVoices(energy)) continue;
    const score = scoreLoop(role, family, loop, drive(energy));
    if (score === -Infinity) continue;
    answers.push({ loop, code, r: score + pocketFit(role, loop, pocket) - 1.5 * Math.abs(overlap(base.loop, loop) - 0.6) });
  }
  answers.sort((x, y) => y.r - x.r);
  const A = base.loop, B = answers[0]?.loop ?? A, C = answers[1]?.loop ?? B;
  const bars = formBars(form, A, B, C);
  const fx = fxOf(base.draft ?? first), mini = encodeLoop(role, bars), code = sound(role, family, mini, keyPc, minor, energy, fx, voice, layer, candy, kick, liftOf(role, pocket));
  compile(code);
  return { code, mini, fx, voice, layer, candy, form, loop: base.loop, every, pocket: +pocketFit(role, base.loop, pocket).toFixed(3), draft: base.draft ?? first, prompt, score: base.score, energy, seconds: (performance.now() - t0) / 1000,
    ...(prev?.loop ? { overlap: +overlap(prev.loop, base.loop).toFixed(2) } : {}) };
}
