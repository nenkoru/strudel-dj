"""Training text for the tiny in-page model: one lane's mini-notation per line, after a prompt.

    drums edm>  <bd*4>, <[~ hh]*4>, ...
    bass e minor edm>  <[e2 ~ e2 ~] ...>

The model writes only the mini-notation (what notes or hits, when); the page wraps it in the
style's sound and effects. Pitched lanes are transposed into all 12 keys. Lanes longer than
MAXLEN characters are dropped (mostly dense chord lanes). Writes tiny/data/{train,valid}.txt.

    uv run python tiny/prep.py
"""
import json
import random
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
OUT = Path(__file__).parent / 'data'
MAXLEN = 400
NAMES = ['c', 'c#', 'd', 'eb', 'e', 'f', 'f#', 'g', 'ab', 'a', 'bb', 'b']
PC = {n: i for i, n in enumerate(NAMES)} | {'db': 1, 'd#': 3, 'gb': 6, 'g#': 8, 'a#': 10, 'cb': 11, 'fb': 4, 'e#': 5, 'b#': 0}
NOTE = re.compile(r'(?<![a-z_])([a-g])(#|b)?(\d)')


def transpose(mini, k):
    def sub(m):
        p = PC[m[1] + (m[2] or '')] + 12 * int(m[3]) + k
        if not 12 <= p < 96:
            raise ValueError
        return NAMES[p % 12] + str(p // 12)
    return NOTE.sub(sub, mini)


def key_name(key, k):
    tonic, mode = key.split()
    return f'{NAMES[(PC[tonic.lower()] + k) % 12]} {mode}'


def main():
    random.seed(0)
    rows = {'train': [], 'valid': []}
    for line in open(ROOT / 'data' / 'strudel.jsonl'):
        r = json.loads(line)
        lanes = re.findall(r'^\s*(note|s)\("([^"]*)"\)', r['code'], re.M)
        style = 'edm' if 'electronic' in r['genre'] else 'any'
        split = 'valid' if r['test'] else 'train'
        mode = r['key'].split()[-1]
        if mode not in ('major', 'minor'):
            continue
        for (_, mini), role in zip(lanes, r['roles']):
            if len(mini) > MAXLEN:
                continue
            if role == 'drums':
                rows[split].append(f'drums {style}>{mini}')
                continue
            for k in range(-6, 6) if split == 'train' else [0]:
                try:
                    rows[split].append(f'{role} {key_name(r["key"], k)} {style}>{transpose(mini, k)}')
                except ValueError:
                    pass
    OUT.mkdir(exist_ok=True)
    for split, xs in rows.items():
        random.shuffle(xs)
        (OUT / f'{split}.txt').write_text('\n'.join(xs) + '\n')
        print(split, len(xs), 'lines', sum(map(len, xs)) // 1000, 'k chars')
    chars = sorted(set(''.join(rows['train'])))
    print('vocab', len(chars), ''.join(chars))


if __name__ == '__main__':
    main()
