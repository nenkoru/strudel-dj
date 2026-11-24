"""The base model's tokenizer: byte-level BPE (GPT-2's byte alphabet, so any text encodes) whose words
are whole lines, so merges may cross spaces and learn the notation's chunks (` ~@3`, `[bd ~`,
`).s("gm_`). Trained on an even mix of the three kinds of text the base sees: narrow lines (a part
under a track), pieces (tiny/piece.py) and whole Strudel programs. The page needs the same encoder,
so it is kept simple: tiny/<name>.tokenizer.json holds the byte map's inverse, the vocabulary and the
merges in rank order.

    uv run --with tokenizers python tiny/tokenizer.py train tok4k 4096 <files...>
    uv run --with tokenizers python tiny/tokenizer.py measure tok4k <files...>
"""
import gzip
import random
import sys
from pathlib import Path

from tokenizers import Tokenizer, models, pre_tokenizers, decoders, trainers, Regex

HERE = Path(__file__).parent
SAMPLE = 60_000_000  # characters per file in training


def read(path, limit):
    opener = gzip.open if path.endswith('.gz') else open
    with opener(path, 'rt', errors='replace') as f:
        return f.read(limit)


def build():
    tok = Tokenizer(models.BPE())
    tok.pre_tokenizer = pre_tokenizers.Sequence([
        pre_tokenizers.Split(Regex('\n'), 'isolated'),        # a line is a word; the newline its own
        pre_tokenizers.ByteLevel(add_prefix_space=False, use_regex=False),
    ])
    tok.decoder = decoders.ByteLevel()
    return tok


def train(name, size, files):
    tok = build()
    texts = []
    for f in files:
        t = read(f, SAMPLE)
        lines = t.split('\n')
        random.Random(0).shuffle(lines)  # pieces span lines: shuffling only mixes which lines are seen together
        texts.append('\n'.join(lines))
        print(f, len(t) // 1000000, 'M chars', flush=True)
    trainer = trainers.BpeTrainer(vocab_size=int(size), min_frequency=50, show_progress=False,
                                  initial_alphabet=pre_tokenizers.ByteLevel.alphabet())
    tok.train_from_iterator((ln for t in texts for ln in t.split('\n')), trainer=trainer)
    tok.save(str(HERE / f'{name}.tokenizer.json'))
    print('vocab', tok.get_vocab_size())


def measure(name, files):
    tok = Tokenizer.from_file(str(HERE / f'{name}.tokenizer.json'))
    for f in files:
        t = read(f, 3_000_000)
        n = len(tok.encode(t).ids)
        print(f'{f}: {len(t) / n:.2f} chars per token')


if __name__ == '__main__':
    cmd, name, *rest = sys.argv[1:]
    train(name, rest[0], rest[1:]) if cmd == 'train' else measure(name, rest)
