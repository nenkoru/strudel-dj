"""A logistic model of the owner's ratings (good vs meh) on a loop's features (tiny/critic.mjs
features), strongly regularised: 100-odd ratings can say which way a feature should go, not much
more. Writes tiny/reward.json for the critic.

    python tiny/reward.py features.jsonl
"""
import json
import sys
from pathlib import Path

import numpy as np

rows = [json.loads(line) for line in open(sys.argv[1])]
names = [k for k in rows[0] if k != 'y']
X = np.array([[r[k] for k in names] for r in rows], float)
y = np.array([r['y'] for r in rows], float)
w, bias, lam = np.zeros(len(names)), 0.0, 1.0
for _ in range(5000):  # gradient descent on the L2-penalised log loss
    p = 1 / (1 + np.exp(-(X @ w + bias)))
    w -= 0.1 * (X.T @ (p - y) / len(y) + lam * w / len(y))
    bias -= 0.1 * float(np.mean(p - y))
p = 1 / (1 + np.exp(-(X @ w + bias)))
acc = float(np.mean((p > 0.5) == y))
print(f'{len(rows)} ratings, {int(y.sum())} good; train accuracy {acc:.2f} (always-meh {1 - y.mean():.2f})')
print({k: round(float(v), 2) for k, v in zip(names, w)})
Path(__file__).with_name('reward.json').write_text(json.dumps({'bias': bias, 'w': dict(zip(names, w.tolist()))}))
