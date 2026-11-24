"""The owner's taste from the rating page's swipes, and a batch ordered to learn it fastest.

A logistic regression on what a part is made of (kind, voice, section, track, phrase form and its moves,
temperature, whether the track has a kick there, a second timbre, length) predicts good/bad; 5-fold
cross-validated it is right on 74% of 369 swipes (2026-11-06; always "bad" would be 53%, and the owner
repeats his own verdict on 86% of repeats, the ceiling). It orders deckc/mine/batch.json: the moments the
model is least sure about first (a swipe there teaches it the most), every fourth one at random so the
estimate stays honest.

    uv run --with scikit-learn python tiny/taste.py <ratings dir (ArtifactData out_dir)> [batch.json]
"""
import glob
import json
import random
import sys
from pathlib import Path

import numpy as np
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score


def features(role, voice, section, track, form, temperature, hear, family, code):
    d = {f'role={role}': 1, f'voice={voice}': 1, f'section={section}': 1, f'track={track}': 1, f'family={family}': 1,
         f'shape={str(form).split("+")[0]}': 1, 'T': float(temperature or 1), 'beat': float('kick' in json.dumps(hear or '')),
         'layer': float(code.count('note(') > 1), 'len': len(code) / 1000}
    for m in str(form).split('+')[1:]:
        if m != 'none':
            d[f'move={m}'] = 1
    return d


def of_rating(r):
    return features(r.get('role'), r.get('voice'), r.get('section'), r.get('track'), r.get('form', ''), r.get('temperature'),
                    r.get('hear'), r.get('family'), r.get('code', ''))


def of_part(item, p):
    return features(item['role'], p.get('voice'), item.get('section'), item.get('track'), p.get('form', ''), p.get('temperature'),
                    item.get('hear'), item.get('family'), p.get('code', ''))


def main(ratings_dir, batch_path='deckc/mine/batch.json'):
    rows, seen = [], set()
    for d in ratings_dir.split(','):
        for f in glob.glob(f'{d.strip()}/*.json'):
            b = Path(f).name
            if b in seen:
                continue
            seen.add(b)
            rows.append(json.load(open(f)))
    rows = [r.get('data', r) for r in rows]
    rows = [r for r in rows if r.get('verdict') in ('good', 'bad')]
    vec = DictVectorizer()
    X = vec.fit_transform([of_rating(r) for r in rows])
    y = np.array([r['verdict'] == 'good' for r in rows])
    clf = LogisticRegression(C=0.3, max_iter=2000)
    acc = cross_val_score(clf, X, y, cv=5).mean()
    clf.fit(X, y)
    export = Path(__file__).parent / 'taste.json'
    export.write_text(json.dumps({'intercept': float(clf.intercept_[0]), 'w': dict(zip(vec.get_feature_names_out(), clf.coef_[0])),
                                  'swipes': len(rows), 'accuracy': round(float(acc), 3)}))
    print(f'{len(rows)} swipes, cross-validated accuracy {acc:.2f}')
    print('exported', export)
    if batch_path == '-' or not Path(batch_path).exists():
        return
    doc = json.load(open(batch_path))
    items = doc['items']
    for it in items:
        ps = clf.predict_proba(vec.transform([of_part(it, it['a']), of_part(it, it['b'])]))[:, 1]
        it['taste'] = round(float(ps.mean()), 3)
    rng = random.Random(0)
    unsure = sorted(items, key=lambda it: abs(it['taste'] - 0.5))
    rest = unsure[:]
    rng.shuffle(rest)
    order, used = [], set()
    while len(order) < len(items):  # three least sure, then one at random
        for src, k in ((unsure, 3), (rest, 1)):
            for it in src:
                if k == 0:
                    break
                if it['pairId'] not in used:
                    used.add(it['pairId']); order.append(it); k -= 1
    doc['items'] = order
    doc['taste'] = {'swipes': len(rows), 'accuracy': round(float(acc), 3)}
    json.dump(doc, open(batch_path, 'w'))
    print('ordered', len(order), 'items; first ten taste:', [it['taste'] for it in order[:10]])


if __name__ == '__main__':
    main(*sys.argv[1:3])
