"""data/strudel.jsonl → chat-format SFT files, split as in MidiCaps.

    data/sft/{train,test}.jsonl   full dialect description as system prompt (same as the baseline)
    data/mlx/{train,valid,test}.jsonl   one-line system prompt, for mlx_lm.lora
"""
import json
import random
from pathlib import Path

from evalkit import SYSTEM, SYSTEM_SHORT, prompt


def chat(row, system):
    return {'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': prompt(row)},
                         {'role': 'assistant', 'content': row['code']}]}


rows = [json.loads(l) for l in open('data/strudel.jsonl')]
train = [r for r in rows if not r['test']]
test = [r for r in rows if r['test']]
random.Random(0).shuffle(train)
splits = {'train': train[150:], 'valid': train[:150], 'test': test}

for d in ('sft', 'mlx'):
    Path(f'data/{d}').mkdir(parents=True, exist_ok=True)
with open('data/sft/train.jsonl', 'w') as f:
    f.writelines(json.dumps({'id': r['id'], **chat(r, SYSTEM)}, ensure_ascii=False) + '\n' for r in train)
with open('data/sft/test.jsonl', 'w') as f:
    f.writelines(json.dumps({'id': r['id'], **chat(r, SYSTEM)}, ensure_ascii=False) + '\n' for r in test)
for name, part in splits.items():
    with open(f'data/mlx/{name}.jsonl', 'w') as f:
        f.writelines(json.dumps(chat(r, SYSTEM_SHORT), ensure_ascii=False) + '\n' for r in part)
print({k: len(v) for k, v in splits.items()})
