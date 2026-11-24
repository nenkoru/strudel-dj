// A batch of rating items composed ahead on the Mac, so the rating page on a phone only plays them
// (loading and running the 10M model there made iOS reload the page). Same choices as the page's
// makeItem (deckc/rate/index.html): one of the owner's tracks, a phrase of a chosen energy, a role,
// the section from rekordbox's phrase kind, what the track plays there; two parts (twins) for that
// moment, one draft each at a random temperature, and each part's next three phrases developed from
// it over what the track does in them (`dev`, for the page's 2- and 4-phrase listening). Four moments
// per track in a row, so the phone decodes a track once for four cards.
//
//   NODE_PATH=js/node_modules node deckc/batch.mjs <moments> <seed> <out.json> [model.json | http://...]
//   (an http model is the base model served on the GPU by tiny/serve.py, through an ssh tunnel)
//   (several in parallel, then merged into deckc/mine/batch.json: see README)
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { Tiny } from './src/tiny.mjs';
import { composePhrase, heardOver, pickForm, pickStyleLayer, restyle, STYLES, loopFeatures } from './src/compose.mjs';
import { tasteFeatures, tasteProb, pickTwins } from './src/taste.mjs';

const [n, seed, out, modelPath = fileURLToPath(new URL('./site/tiny.json', import.meta.url))] = process.argv.slice(2);
let s = 1 + 7919 * +seed;
const rnd = () => (s = (s * 16807) % 2147483647) / 2147483647;
const pick = (xs) => xs[Math.floor(rnd() * xs.length)];

let tasteModel = null;
try { tasteModel = JSON.parse(readFileSync(new URL('../tiny/taste.json', import.meta.url), 'utf8')); } catch {}
let reward = null;
try { reward = JSON.parse(readFileSync(new URL('../tiny/reward.json', import.meta.url), 'utf8')); } catch {}
const logit = (f) => reward ? reward.bias + Object.entries(reward.w).reduce((a, [k, w]) => a + w * (f[k] ?? 0), 0) : 0;
const BEST = Math.max(1, parseInt(process.env.BEST || '2', 10));
if (BEST > 2 && (!tasteModel || !reward)) console.error('best-of-N without', !tasteModel ? 'tiny/taste.json' : '', !reward ? 'tiny/reward.json' : '');
const KEYS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
const LEVELS = [['lo', 'тихое место', 0, 0.4], ['mid', 'середина', 0.4, 0.75], ['hi', 'пик энергии', 0.75, 1.01]];
const SECTION = { 'подъём': 'build', 'припев': 'drop', 'спад': 'break', 'бридж': 'break', 'интро': 'groove', 'куплет': 'groove', 'аутро': 'groove' };

// where each track leaves room, per bar and 16th (deckc/hear.py pockets): the phrase's average goes to
// the composer, which prefers notes in the gaps of their band
let POCKETS = {};
try { POCKETS = JSON.parse(readFileSync(new URL('./mine/pockets.json', import.meta.url), 'utf8')); } catch {}
const pocketAt = (id, bar) => {
  const bars = POCKETS[id]?.slice(bar, bar + 8);
  if (!bars?.length) return undefined;
  const avg = (k) => Array.from({ length: 16 }, (_, st) => bars.reduce((a, b) => a + +b[k][st], 0) / bars.length / 9);
  return { low: avg(0), mid: avg(1), high: avg(2) };
};
const own = JSON.parse(readFileSync(new URL('./mine/mine.json', import.meta.url), 'utf8')).tracks
  .filter((t) => t.phrases.some((p) => p.bar >= 0 && p.bar + 8 < t.energy.length));
let model, name;
let byMini;
if (modelPath.startsWith('http')) {
  const cfg = await fetch(`${modelPath}/info`).then((r) => r.json());
  model = { cfg: { ...cfg, hear: true }, generate: async (prompt, { temperature = 0.8 } = {}) => {
    const r = await fetch(`${modelPath}/generate`, { method: 'POST', body: JSON.stringify({ prompt, temperature }) }).then((x) => x.json());
    if (r.error) throw new Error(r.error);
    return r.text;
  } };
  name = `${cfg.name} ${cfg.layers}x${cfg.dim} step ${cfg.step} loss ${cfg.valid_loss}`;
} else if (modelPath.startsWith('pieces:')) {
  const pool = readFileSync(modelPath.slice(7), 'utf8').trim().split('\n').map((l) => JSON.parse(l));
  const idx = new Map();  // index key -> [parts]
  byMini = new Map();  // mini -> {id, temperature, model}
  for (const piece of pool) {
    for (const p of piece.parts) {
      if (!p.mini || p.role === 'part') continue;
      const role = p.role === 'solo' ? 'lead' : p.role;
      const key = p.role === 'drums' ? `drums|${piece.style}` : `${role}|${piece.key}|${piece.mode}|${piece.style}`;
      if (!idx.has(key)) idx.set(key, []);
      idx.get(key).push(p);
      byMini.set(p.mini, { id: piece.id, temperature: piece.temperature, model: piece.model });
    }
  }
  // the same parts under any style, for a key whose style has none
  for (const [k, v] of idx) {
    const [role, key, mode, style] = k.split('|');
    if (style !== '*' && role !== 'drums') {
      const wk = `${role}|${key}|${mode}|*`;
      if (!idx.has(wk)) idx.set(wk, []);
      idx.get(wk).push(...v);
    }
  }
  const queues = new Map();  // index key -> shuffled queue
  const nextFrom = (key) => {
    let q = queues.get(key);
    if (!q || !q.length) {
      const parts = idx.get(key);
      if (!parts?.length) throw new Error('pool: no ' + key);
      q = [...parts];
      for (let i = q.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [q[i], q[j]] = [q[j], q[i]]; }
      queues.set(key, q);
    }
    return q.shift();
  };
  model = {
    cfg: { hear: false },
    generate: (prompt) => {
      const tokens = prompt.replace(/>$/, '').split(' ');
      let key;
      if (tokens[0] === 'drums') key = `drums|${tokens[1]}`;
      else {
        const role = tokens[0] === 'solo' ? 'lead' : tokens[0];
        key = `${role}|${tokens[1]}|${tokens[2]}|${tokens[3]}`;
        if (!idx.get(key)?.length) key = `${role}|${tokens[1]}|${tokens[2]}|*`;
      }
      return nextFrom(key).mini;
    },
  };
  name = `${pool[0]?.model} pieces`;
} else {
  model = new Tiny(JSON.parse(readFileSync(modelPath, 'utf8')));
  const generate = model.generate.bind(model);  // no yielding to a UI: Node's loop would see nothing pending and exit
  model.generate = (prompt, opts) => generate(prompt, { ...opts, slice: Infinity });
  name = `tiny ${model.cfg.dim}d step ${model.cfg.step} loss ${model.cfg.valid_loss}${model.cfg.hear ? ' hear' : ''}`;
}
// Where a part may come in (the owner: parts started "neither here nor there", e.g. over a talking intro
// a bar before the music kicks in): rekordbox's phrase lines where the track keeps one state for the
// part's first 8 bars: the kick neither arrives nor leaves (deckc/hear.py's words per bar) and the
// loudness does not jump (E Ke Keq Aty: a phrase line at bar 56 sat in a talking break, the music
// slams back at 57). A phrase line whose change comes a few bars in moves there when that is on a
// 4-bar line, else it is no entry. Drums
// and bass only where the track has a kick; elsewhere other roles get soft voices (SOFT).
const SOFT = { lead: ['ep1', 'vibes', 'kalimba', 'musicbox'], solo: ['ep1', 'vibes', 'ensemble', 'warmpad', 'halo', 'oohs'],
  chords: ['ep1', 'ep2', 'strings', 'wurli'] };
function settled(track, role) {
  const kick = (b) => (track.hear?.[b] ?? '').includes('kick');
  const turn = (b) => kick(b) !== kick(b - 1) || Math.abs((track.energy[b] ?? 0) - (track.energy[b - 1] ?? 0)) > 0.35;
  const firstTurn = (bar) => [1, 2, 3, 4, 5, 6, 7].find((k) => turn(bar + k)) ?? 0;
  const out = [];
  for (const p of track.phrases) {
    let bar = p.bar;
    if (bar < 0 || bar + 8 >= track.energy.length) continue;
    const change = firstTurn(bar);
    if (change > 0) {
      if (change % 4 || bar + change + 8 >= track.energy.length) continue;  // the music turns mid-phrase: no entry here
      bar += change;
      if (firstTurn(bar)) continue;
    }
    const hasKick = kick(bar);
    if ((role === 'drums' || role === 'bass') && !hasKick) continue;
    out.push({ bar, kind: p.kind });
  }
  return out;
}

const items = [];
let track;
for (let i = 0; i < +n; i++) {
  // a new track for every moment: in batches of four per track the owner heard whole runs of good and bad
  track = pick(own);
  // swipes 2026-11-05 (48): chords 8/11 liked, solo 5/16, lead 1/4, drums 1/9, bass 1/8. The owner wants
  // variety, not everything around chords: every kind of part as often (chords twice), the styles
  // (compose.mjs STYLES) built on the roles the model writes; `role` is the kind, `base` what it writes
  const role = pick(['chords', 'chords', 'solo', 'lead', 'bass', 'drums', ...Object.keys(STYLES)]);
  const style = STYLES[role], base = style?.base ?? role;
  const starts = settled(track, base);
  if (!starts.length) { i--; continue; }
  const mean = (b) => track.energy.slice(b, b + 8).reduce((a, x) => a + x, 0) / 8;
  const [level, levelName, lo, hi] = pick(LEVELS);
  const fits = starts.filter((p) => mean(p.bar) >= lo && mean(p.bar) < hi);
  const start = pick(fits.length ? fits : starts), fromBar = start.bar, energy = mean(fromBar);
  const next = mean(fromBar + 8), prev = mean(Math.max(0, fromBar - 8));
  const section = SECTION[start.kind] ?? (next - energy > 0.25 ? 'build' : energy < 0.35 ? 'break' : energy - prev > 0.25 ? 'drop' : 'groove');
  const [tonic, mode] = track.key.split(' ');
  const hear = track.hear ? heardOver(track.hear.slice(fromBar, fromBar + 8)) : undefined;
  const ask = { role: base, family: track.family, keyPc: KEYS.indexOf(tonic), minor: mode === 'minor', energy, section, hear, pocket: pocketAt(track.id, fromBar) };
  // 0.75 lost in the swipes; how far up still pays is the open question
  // each twin gets its own phrase form (composePhrase FORMS), so a pair of swipes also compares forms
  const beatless = !(hear ?? '').includes('kick');  // over a talking intro or an ambient stretch: soft sounds only
  // where there is no kick only chords (4/18 liked over beatless stretches, most of them solos); a bass only
  // where the track has no bassline of its own
  if ((beatless && !['chords', 'pad', 'drone', 'arp', 'vox'].includes(role)) || (role === 'bass' && (hear ?? '').includes('low'))) { i--; continue; }
  const one = async () => {
    // temperature 0.9 9/16 liked, 1.1 4/14, 1.3 3/18; the shape `call` 1/10
    const temperature = pick([0.8, 0.9, 1.0]);
    let form = pickForm(base, rnd);
    while (form.startsWith('call+')) form = pickForm(base, rnd);
    const voice = style ? pick(style.voices) : beatless && SOFT[role] ? pick(SOFT[role]) : role === 'drums' ? pick(['latin', 'perc', 'wood', 'shaker']) : undefined;
    // a style is heard without ear candy on top, with a second lane that suits it (STYLES layers)
    // two drafts: more cuts to choose the one that sits in the track's gaps
    const p = await composePhrase(model, { ...ask, drafts: 2, temperature, form, ...(voice ? { voice } : {}), ...(style ? { layer: pickStyleLayer(role, rnd), candy: [] } : {}) });
    // from a pool: the program's own temperature (the taste model reads it) and which program it came from
    const src = byMini?.get(p.draft);
    return { ...p, code: style ? restyle(p.code, role, rnd, ask.pocket) : p.code, temperature: src?.temperature ?? temperature, ...(src ? { piece: src.id } : {}) };
  };
  // the track's phrases after the first: their energy, rekordbox kind and sound, for the developed phrases
  const later = [1, 2, 3].map((k) => fromBar + 8 * k).filter((b) => b + 8 <= track.energy.length).map((b) => {
    const kind = [...track.phrases].reverse().find((p) => p.bar <= b)?.kind, e = mean(b);
    return { energy: e, section: SECTION[kind] ?? (e < 0.35 ? 'break' : 'groove'), hear: track.hear ? heardOver(track.hear.slice(b, b + 8)) : undefined,
      pocket: pocketAt(track.id, b) };
  });
  const develop = async (p) => {
    const dev = [];
    for (const at of later) {
      p = { ...(await composePhrase(model, { ...ask, ...at, drafts: 2, temperature: p.temperature, prev: p, form: p.form, ...(style ? { candy: [] } : {}) })), temperature: p.temperature };
      if (style) p.code = restyle(p.code, role, rnd, at.pocket);
      dev.push({ code: p.code, mini: p.mini, fx: p.fx, overlap: p.overlap ?? 1, energy: +at.energy.toFixed(2), section: at.section });
    }
    return dev;
  };
  try {
    let a, b;
    if (BEST <= 2) {
      a = await one();
      b = await one();
      if (b.mini === a.mini && b.fx.join() === a.fx.join()) b = await one();
    } else {
      const cands = [];
      for (let k = 0; k < BEST; k++) {
        try { cands.push(await one()); } catch {}
      }
      if (cands.length < 2) throw new Error('fewer than 2 candidates');
      for (const c of cands) {
        c.critic = +(c.score + 0.5 * logit(loopFeatures(base, track.family, c.loop, energy))).toFixed(3);
        c.taste = tasteModel ? +tasteProb(tasteModel, tasteFeatures({ role: base, voice: c.voice, section, track: track.id, form: c.form, temperature: c.temperature, hear, family: track.family, code: c.code })).toFixed(3) : 0.5;
      }
      [a, b] = pickTwins(cands.map((c) => ({ c, critic: c.critic, taste: c.taste }))).map((x) => x.c);
    }
    a.dev = await develop(a); b.dev = await develop(b);
    const part = (p) => ({ code: p.code, draft: p.draft, mini: p.mini, fx: p.fx, voice: p.voice, layer: p.layer, candy: p.candy, pocket: p.pocket, form: p.form, score: +p.score.toFixed(3), temperature: p.temperature, dev: p.dev, piece: p.piece, critic: p.critic, taste: p.taste });
    items.push({ set: 'mine', family: track.family, section, track: track.id, url: 'mine/tracks/' + track.file,
      title: `${track.artist} — ${track.title}`, key: track.key, role, base, fromBar, phrase: start.kind, hear,
      energy: +energy.toFixed(2), level, levelName: fits.length ? levelName : 'середина',
      pairId: `b${seed}-${i}-${Math.floor(rnd() * 1e6).toString(36)}`, prompt: a.prompt, model: name, ...(BEST > 2 ? { bestOf: BEST } : {}), a: part(a), b: part(b) });
  } catch (e) { console.error(i, e.message); }
  if (i % 10 === 9) console.error(seed, i + 1, 'of', n);
}
writeFileSync(out, JSON.stringify(items));
console.error(seed, 'done', items.length);
