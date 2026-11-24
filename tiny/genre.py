"""The genre fine-tune's corpus for the base model (base130 -> base130ft): house, techno and progressive
in both formats the base knows, plus a replay of its general data so it keeps what it learned.

- genre-pieces: whole programs (tiny/piece.py) from MTG-Jamendo dance tracks transcribed to MIDI (styles
  house/techno/prog/edm, no drums, cleaned to the loops they play: prep_midi.py clean_transcribed), a third of the Lakh programs MidiCaps calls electronic (style edm; 167k
  in all, mostly synth-pop, they would drown the rest), WaivOps NRG-CP dance
  chords, Groove drums and the Strudel-Synth programs; shuffled, so the valid split pack takes from the
  file's start is a sample of all of them
- genre-lines: the page's one-part lines (role key style level>mini) of the same sources (a quarter of
  Lakh's: all of them were 500 M of the 614 M characters), the style-fx lines and the parts the owner
  swiped right
- replay-pieces: general programs (LAMD, Discover) as many characters as genre-pieces

    python3 tiny/genre.py   (on the GPU server, in ~/strudel-lm; then train_torch.py pack, see ft.sh)
"""
import gzip
import random
from pathlib import Path

D = Path(__file__).parent / 'data'
SEP = '\n\x1e\n'


def docs(name):
    with gzip.open(D / name, 'rt', errors='replace') as f:
        buf = ''
        while chunk := f.read(1 << 24):
            buf += chunk
            *done, buf = buf.split(SEP)
            yield from (d for d in done if d.strip())


def lines(name):
    with (gzip.open(D / name, 'rt', errors='replace') if name.endswith('.gz') else open(D / name)) as f:
        yield from (ln.rstrip('\n') for ln in f if ln.strip())


def main():
    rng = random.Random(0)
    genre = list(docs('jamendo-clean-pieces.txt.gz')) + list(docs('nrgcp-pieces.txt.gz')) + list(docs('groove-pieces.txt.gz')) \
        + list(docs('strudel-pieces.txt.gz')) + [d for i, d in enumerate(docs('lakhmac-pieces.txt.gz')) if 'style: edm' in d.split('\n', 1)[0] and i % 3 == 0]
    rng.shuffle(genre)
    size = sum(map(len, genre))
    with gzip.open(D / 'genre-pieces.txt.gz', 'wt', compresslevel=6) as f:
        f.writelines(d + SEP for d in genre)
    tagged = list(lines('jamendo-clean-train.txt.gz')) + list(lines('nrgcp-train.txt.gz')) + list(lines('groove-train.txt.gz')) \
        + list(lines('style-fx.txt')) + list(lines('swiped-good.txt')) * 5 \
        + [ln for i, ln in enumerate(lines('lakhmac-train.txt.gz')) if ' edm ' in ln.split('>', 1)[0] and i % 4 == 0]
    rng.shuffle(tagged)
    with gzip.open(D / 'genre-lines.txt.gz', 'wt', compresslevel=6) as f:
        f.writelines(ln + '\n' for ln in tagged)
    replay, got = [], 0
    for src in ('lamd-pieces.txt.gz', 'discover1-pieces.txt.gz'):
        for i, d in enumerate(docs(src)):
            if i % 7 == 3:  # spread over the file, not its start
                replay.append(d); got += len(d)
            if got > size // 2 * (1 + (src != 'lamd-pieces.txt.gz')):
                break
    rng.shuffle(replay)
    with gzip.open(D / 'replay-pieces.txt.gz', 'wt', compresslevel=6) as f:
        f.writelines(d + SEP for d in replay)
    print(f'genre-pieces: {len(genre)} programs, {size / 1e6:.0f} M chars; genre-lines: {len(tagged)} lines, '
          f'{sum(map(len, tagged)) / 1e6:.0f} M chars; replay: {len(replay)} programs, {got / 1e6:.0f} M chars')


if __name__ == '__main__':
    main()
