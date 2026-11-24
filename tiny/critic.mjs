// The critic of the self-improvement loop (tiny/rest.sh): the page's own rules (scoreDraft: on the
// 16th grid, density for the style and energy, no one-cell loops, pitch variety) plus a small
// logistic model of the owner's ratings (tiny/reward.py), so drafts are judged without a listener.
//
//   node tiny/critic.mjs prompts <n> <out.jsonl> [seed] [plain|hear]   prompts like the page's (plain: no section tag,
//                                                                 for models trained before sections; hear: with `on` words)
//   node tiny/critic.mjs features <ratings dir> <out.jsonl>       rated loops -> features
//   node tiny/critic.mjs score <samples.jsonl> <reward.json> <out.jsonl> [keep]
//   node tiny/critic.mjs pairs <samples.jsonl> <reward.json> <out.jsonl> [gap]  best vs worst draft, for tiny/dpo.py
import { readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { scoreDraft, loopFeatures, promptFor, drive, inKey, fitNotes, MODEL_NOTES } from '../deckc/src/compose.mjs';

const [mode, a, b, c, keepArg] = process.argv.slice(2);
const rng = (() => { let s = mode === 'prompts' ? 7 + 1000 * +(c ?? 0) : 7; return () => (s = (s * 16807) % 2147483647) / 2147483647; })();
const pick = (xs) => xs[Math.floor(rng() * xs.length)];
const KIT = { tight_hat: 'hh', open_hat: 'oh', clap: 'cp', tom: 'lt', ride: 'rd' };

if (mode === 'prompts') {
  const rows = [];
  for (let i = 0; i < +a; i++) {
    const role = pick(['bass', 'bass', 'bass', 'lead', 'lead', 'solo', 'solo', 'drums', 'drums']);
    const family = pick(['house', 'progressive', 'progressive', 'techno']), energy = +rng().toFixed(2);
    const keyPc = Math.floor(rng() * 12), minor = rng() < 0.75, d = drive(energy);
    // sections as the pages pick them: from the track's energy and where it is heading
    const section = keepArg === 'plain' ? undefined : d < 0.45 ? pick(['break', 'break', 'build']) : d < 0.75 ? pick(['build', 'groove', 'groove']) : pick(['drop', 'groove']);
    // what the track plays, as deckc/hear.py would hear it in that section (tiny/mix.py --hear uses the same odds)
    const ON = { break: ['mid', 'mid', 'mid top', 'low mid'], build: ['kick mid top', 'mid top', 'kick low mid top'],
      drop: ['kick low mid top', 'kick low mid top', 'kick low top'], groove: ['kick low mid top', 'kick low top'] };
    const hear = keepArg === 'hear' ? pick(ON[section]) : undefined;
    rows.push({ role, family, energy, keyPc, minor, section, hear, prompt: promptFor({ role, family, keyPc, minor, energy: d, section, hear }) });
  }
  writeFileSync(b, rows.map((r) => JSON.stringify(r)).join('\n') + '\n');
} else if (mode === 'features') {
  const out = [];
  for (const f of readdirSync(a)) {
    let r = JSON.parse(readFileSync(`${a}/${f}`, 'utf8')); r = r.data ?? r;
    if (r.verdict === 'skip') continue;
    let mini = r.mini;
    if (r.role === 'drums') for (const [k, v] of Object.entries(KIT)) mini = mini.replaceAll(k, v);
    const cut = scoreDraft(mini, r);
    if (cut) out.push({ y: +(r.verdict === 'good'), ...loopFeatures(r.role, r.family, cut.loop, r.energy) });
  }
  writeFileSync(b, out.map((r) => JSON.stringify(r)).join('\n') + '\n');
  console.log(out.length, 'rated loops,', out.filter((r) => r.y).length, 'good');
} else if (mode === 'score') {
  const rm = JSON.parse(readFileSync(b, 'utf8')), keep = +(keepArg ?? 0.25);
  const logit = (f) => rm.bias + Object.entries(rm.w).reduce((s, [k, w]) => s + w * (f[k] ?? 0), 0);
  const scored = [], first = [];
  for (const line of readFileSync(a, 'utf8').trim().split('\n')) {
    const r = JSON.parse(line);
    const cuts = r.drafts.map((d) => scoreDraft(d, r)).map((cut) => cut && {
      ...cut, total: cut.score + 0.5 * logit(loopFeatures(r.role, r.family, cut.loop, r.energy))
        - (r.role === 'drums' ? 0 : 0.8 * (1 - inKey(cut.mini, r.keyPc, r.minor))) });
    first.push(cuts[0]?.total ?? -2);
    const best = cuts.filter(Boolean).sort((x, y) => y.total - x.total)[0];
    if (!best) continue;
    // training lines in the model's spelling: kit names back to drum names, notes in key and register
    let mini = best.mini;
    if (r.role === 'drums') for (const [k, v] of Object.entries(KIT)) mini = mini.replaceAll(k, v);
    else mini = fitNotes(r.role, mini, r.keyPc, r.minor, MODEL_NOTES);
    scored.push({ role: r.role, total: best.total, line: r.prompt + mini + (best.fx.length ? '|' + best.fx.join(' ') : '') });
  }
  // the best draft of each prompt, and of those the top share within each role (roles score on
  // different scales: a pooled cut kept only solos): the next fine-tune's lines
  const kept = [];
  for (const role of ['bass', 'lead', 'solo', 'drums']) {
    const mine = [...new Map(scored.filter((s) => s.role === role).map((s) => [s.line, s])).values()].sort((x, y) => y.total - x.total);
    kept.push(...mine.slice(0, Math.ceil(mine.length * keep)));
  }
  writeFileSync(c, kept.map((s) => s.line).join('\n') + '\n');
  const mean = (xs) => xs.reduce((s, x) => s + x, 0) / xs.length;
  console.log(JSON.stringify({ prompts: first.length, firstDraft: +mean(first).toFixed(3),
    bestOfN: +mean(scored.map((s) => s.total)).toFixed(3), kept: kept.length, keptMean: +mean(kept.map((s) => s.total)).toFixed(3) }));
} else if (mode === 'pairs') {
  // preference pairs for tiny/dpo.py without a listener: per prompt the best draft against the worst,
  // as the model wrote them, when the critic separates them clearly. Both must parse: with unparsable
  // drafts as the losers, DPO pulled the model off the notation (parse rate 1.0 -> 0.56)
  const rm = JSON.parse(readFileSync(b, 'utf8')), gap = +(keepArg ?? 0.3);
  const logit = (f) => rm.bias + Object.entries(rm.w).reduce((s, [k, w]) => s + w * (f[k] ?? 0), 0);
  const out = [];
  for (const line of readFileSync(a, 'utf8').trim().split('\n')) {
    const r = JSON.parse(line);
    const totals = r.drafts.map((d) => {
      const cut = scoreDraft(d, r);
      if (!cut) return null;
      return cut.score + 0.5 * logit(loopFeatures(r.role, r.family, cut.loop, r.energy))
        - (r.role === 'drums' ? 0 : 0.8 * (1 - inKey(cut.mini, r.keyPc, r.minor)));
    });
    const order = totals.map((t, i) => i).filter((i) => totals[i] !== null).sort((x, y) => totals[y] - totals[x]);
    if (order.length < 2) continue;
    const hi = order[0], lo = order[order.length - 1];
    if (totals[hi] - totals[lo] >= gap && r.drafts[hi] !== r.drafts[lo])
      out.push({ prompt: r.prompt, chosen: r.drafts[hi], rejected: r.drafts[lo], source: 'critic' });
  }
  writeFileSync(c, out.map((r) => JSON.stringify(r)).join('\n') + '\n');
  console.log(out.length, 'pairs');
}
