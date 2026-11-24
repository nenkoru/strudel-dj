// Taste model: logistic regression over part features, mirroring tiny/taste.py.
// taste.json: {"intercept": float, "w": {feature_name: coef}, "swipes": n, "accuracy": cv_acc}

const none = (x) => (x === undefined || x === null ? 'None' : String(x));

export function tasteFeatures(opts) {
  const { role, voice, section, track, form, temperature, hear, family, code } = opts;
  const d = {};
  d[`role=${none(role)}`] = 1;
  d[`voice=${none(voice)}`] = 1;
  d[`section=${none(section)}`] = 1;
  d[`track=${none(track)}`] = 1;
  d[`family=${none(family)}`] = 1;
  d[`shape=${String(form ?? '').split('+')[0]}`] = 1;
  d.T = temperature === undefined || temperature === null || temperature === 0 ? 1 : Number(temperature);
  const hearStr = hear === undefined || hear === null ? '' : JSON.stringify(hear);
  d.beat = hearStr.includes('kick') ? 1 : 0;
  d.layer = ((code ?? '').match(/note\(/g) || []).length > 1 ? 1 : 0;
  d.len = Number(((code ?? '').length / 1000).toFixed(6));
  for (const m of String(form ?? '').split('+').slice(1)) {
    if (m !== 'none') d[`move=${m}`] = 1;
  }
  return d;
}

export function tasteProb(model, f) {
  const z = model.intercept + Object.entries(f).reduce((s, [k, v]) => s + (model.w[k] ?? 0) * v, 0);
  return 1 / (1 + Math.exp(-z));
}

export function pickTwins(cands) {
  // cands: [{ c: {mini, fx, ...}, critic, taste, ... }]
  const byCritic = [...cands].sort((a, b) => b.critic - a.critic);
  const byTaste = [...cands].sort((a, b) => b.taste - a.taste);
  const rankC = new Map(byCritic.map((x, i) => [x, i]));
  const rankT = new Map(byTaste.map((x, i) => [x, i]));
  const ranked = [...cands].sort((a, b) => {
    const ta = rankC.get(a) + rankT.get(a), tb = rankC.get(b) + rankT.get(b);
    if (ta !== tb) return ta - tb;
    return b.critic - a.critic;
  });
  const a = ranked[0];
  const rest = ranked.slice(1);
  const b = rest.find((x) => x.c.mini !== a.c.mini || x.c.fx?.join() !== a.c.fx?.join()) ?? rest[0];
  return [a, b];
}
