import assert from 'node:assert/strict';
import { tasteFeatures, tasteProb, pickTwins } from './src/taste.mjs';
const f = tasteFeatures({ role: 'bass', voice: 'acid', section: 'drop', track: 't1', form: 'answer4+lift+none+build+fill', temperature: 0.9, hear: 'kick low', family: 'techno', code: 'note("a").s("x") note("b")' });
assert.deepEqual(f, { 'role=bass': 1, 'voice=acid': 1, 'section=drop': 1, 'track=t1': 1, 'family=techno': 1, 'shape=answer4': 1, T: 0.9, beat: 1, layer: 1, len: 0.026, 'move=lift': 1, 'move=build': 1, 'move=fill': 1 });
const g = tasteFeatures({ role: 'chords', voice: undefined, section: undefined, track: 't2', form: '', temperature: 0, hear: undefined, family: 'house', code: '' });
assert.deepEqual(g, { 'role=chords': 1, 'voice=None': 1, 'section=None': 1, 'track=t2': 1, 'family=house': 1, 'shape=': 1, T: 1, beat: 0, layer: 0, len: 0 });
assert.equal(tasteProb({ intercept: 0, w: {} }, f), 0.5);
assert.ok(Math.abs(tasteProb({ intercept: 1, w: { 'role=bass': 1, T: 2 } }, f) - 1 / (1 + Math.exp(-(1 + 1 + 1.8)))) < 1e-12);
const C = (mini, critic, taste, fx = []) => ({ c: { mini, fx }, critic, taste });
// ranks: critic order x(3) y(2) z(1) w(0); taste order w(.9) z(.8) y(.7) x(.1) -> totals x 0+3, y 1+2, z 2+1, w 3+0 = all 3 -> ties by critic: x, y
let [a, b] = pickTwins([C('x', 3, 0.1), C('y', 2, 0.7), C('z', 1, 0.8), C('w', 0, 0.9)]);
assert.equal(a.c.mini, 'x'); assert.equal(b.c.mini, 'y');
[a, b] = pickTwins([C('x', 3, 0.9), C('x', 2, 0.8), C('z', 1, 0.1)]);
assert.equal(a.c.mini, 'x'); assert.equal(b.c.mini, 'z');
[a, b] = pickTwins([C('x', 3, 0.9), C('x', 2, 0.8)]);
assert.equal(a.critic, 3); assert.equal(b.critic, 2);
[a, b] = pickTwins([C('x', 3, 0.9), C('x', 2, 0.8, ['lpf'])]);
assert.equal(b.c.fx[0], 'lpf');
console.log('bestof ok');
