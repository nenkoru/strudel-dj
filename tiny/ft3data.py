"""Data for the third genre fine-tune (base130 -> base130ft3), from what the first two showed:

- they forgot the general data (baseB loss 0.64 -> 0.98) and three times more replayed *programs* barely
  helped: the general one-part lines (the page's format) were never replayed. replay-lines: lines from
  LAMD and Discover, as many characters as genre-lines;
- given a prompt with a section word (build, drop, break, groove) and `on` words, they mostly answered
  an empty line: the genre lines rarely carry both. genre-lines-aug: the genre lines with a section word
  put in after the level on 30% of them (where none is) and the `on` words taken out of 15%, so every
  combination the page sends is seen.

    python3 tiny/ft3data.py   (on the GPU server, in ~/strudel-lm; then ft3.sh packs and trains)
"""
import gzip
import random
from pathlib import Path

D = Path(__file__).parent / 'data'
SECTIONS = ['build', 'drop', 'break', 'groove']
STYLES = {'house', 'techno', 'prog', 'edm', 'any'}


def lines(name):
    with gzip.open(D / name, 'rt', errors='replace') as f:
        yield from (ln.rstrip('\n') for ln in f if ln.strip())


def augment(line, rng):
    head, sep, mini = line.partition('>')
    if not sep:
        return line
    words = head.split(' ')
    if rng.random() < 0.15 and 'on' in words:
        words = words[:words.index('on')]
    if rng.random() < 0.3 and not any(w in SECTIONS for w in words):
        at = next((i for i, w in enumerate(words) if w in STYLES), None)
        if at is not None and at + 1 < len(words) and words[at + 1] in ('lo', 'mid', 'hi'):
            words.insert(at + 2, rng.choice(SECTIONS))
    return ' '.join(words) + '>' + mini


def main():
    rng = random.Random(3)
    size = 0
    with gzip.open(D / 'genre-lines-aug.txt.gz', 'wt', compresslevel=6) as f:
        for ln in lines('genre-lines.txt.gz'):
            out = augment(ln, rng)
            size += len(out)
            f.write(out + '\n')
    got, kept = 0, 0
    with gzip.open(D / 'replay-lines.txt.gz', 'wt', compresslevel=6) as f:
        for src in ('lamd-train.txt.gz', 'discover1-train.txt.gz'):
            for i, ln in enumerate(lines(src)):
                if i % 9 == 4:  # spread over the file
                    f.write(ln + '\n'); got += len(ln); kept += 1
                if got > size // 2 * (1 + (src != 'lamd-train.txt.gz')):
                    break
    print(f'genre-lines-aug {size / 1e6:.0f} M chars; replay-lines {kept} lines, {got / 1e6:.0f} M chars')


if __name__ == '__main__':
    main()
