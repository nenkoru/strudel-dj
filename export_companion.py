"""Companion task: given what deck A plays (some lanes of a loop), write the missing lanes.

This is the live-set format: deck A is transcribed into the dialect (transcribe/), the model
answers with a layer that fits. Pairs are cut from data/strudel.jsonl, so no new data is needed:

    given drums+bass        → write chords+lead   ("add harmony")
    given drums+chords+lead → write bass          ("add a bassline")
    given bass+chords+lead  → write drums         ("add drums")

    uv run python export_companion.py   # → data/mlx-companion/{train,valid,test}.jsonl
"""
import json
import random
from pathlib import Path

from evalkit import prompt

SYSTEM = 'You are a live companion deck. Write the requested Strudel lanes in the loop dialect so they fit the playing loop. Code only.'
TASKS = [({'drums', 'bass'}, {'chords', 'lead'}, 'Add harmony and a lead'),
         ({'drums', 'chords', 'lead'}, {'bass'}, 'Add a bassline'),
         ({'bass', 'chords', 'lead'}, {'drums'}, 'Add drums')]


def lanes(row):
    """The stack's lane lines, paired with their roles (convert.py writes one lane per line)."""
    lines = [l.strip().rstrip(',') for l in row['code'].split('\n')[1:-1]]
    assert len(lines) == len(row['roles']), row['id']
    return dict(zip(row['roles'], lines))


def stack(parts):
    return 'stack(\n' + ',\n'.join(f'  {p}' for p in parts) + '\n)' if len(parts) > 1 else parts[0]


def examples(row):
    have = lanes(row)
    for given, want, ask in TASKS:
        if not given <= have.keys() or not want & have.keys():
            continue
        order = [r for r in ('drums', 'bass', 'chords', 'lead')]
        deck_a = stack([have[r] for r in order if r in given])
        answer = stack([have[r] for r in order if r in want and r in have])
        user = f"{prompt(row).rsplit(chr(10), 1)[0]}\nDeck A is playing:\n{deck_a}\n{ask}."
        yield {'messages': [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': user},
                            {'role': 'assistant', 'content': answer}]}


rows = [json.loads(l) for l in open('data/strudel.jsonl')]
train = [r for r in rows if not r['test']]
random.Random(0).shuffle(train)
splits = {'train': train[150:], 'valid': train[:150], 'test': [r for r in rows if r['test']]}
out = Path('data/mlx-companion'); out.mkdir(parents=True, exist_ok=True)
counts = {}
for name, part in splits.items():
    exs = [e for r in part for e in examples(r)]
    with open(out / f'{name}.jsonl', 'w') as f:
        f.writelines(json.dumps(e, ensure_ascii=False) + '\n' for e in exs)
    counts[name] = len(exs)
print(counts)
