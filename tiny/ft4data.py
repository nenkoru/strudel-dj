"""Lines for the fourth genre fine-tune (base130 -> base130ft4), from what FT3's page-prompt check showed
(reports/ft/README.md): basses were mostly one note on every 16th (`f1*16`) and drum lines hardly came
out.

- genre-lines-v4: genre-lines-aug (tiny/ft3data.py) without 80% of the one-pitch bass lines; the Freesound
  loop lines (tiny/loops2midi.py) five times, with the same tag variety; drum lines from GigaMIDI's
  drums-only files (general drums in the page's format), 20 M characters.

    python3 tiny/ft4data.py   (on the GPU server, in ~/strudel-lm; then ft4.sh)
"""
import gzip
import random
import re
from pathlib import Path

from ft3data import augment, lines

D = Path(__file__).parent / 'data'
NOTE = re.compile(r'(?<![a-z_])([a-g])(#|b)?(\d)')


def one_pitch_bass(line):
    head, _, mini = line.partition('>')
    return head.startswith('bass ') and len({m.group(0) for m in NOTE.finditer(mini)}) <= 1


def main():
    rng = random.Random(4)
    dropped = kept = loops = drums = 0
    with gzip.open(D / 'genre-lines-v4.txt.gz', 'wt', compresslevel=6) as f:
        for ln in lines('genre-lines-aug.txt.gz'):
            if one_pitch_bass(ln) and rng.random() < 0.8:
                dropped += 1
                continue
            f.write(ln + '\n'); kept += 1
        loop_lines = list(lines('loops-train.txt.gz'))
        for _ in range(5):
            for ln in loop_lines:
                f.write(augment(ln, rng) + '\n'); loops += 1
        size = 0
        for i, ln in enumerate(lines('giga-drums-only-train.txt.gz')):
            if i % 3 == 0 and ln.startswith('drums'):
                f.write(augment(ln, rng) + '\n'); drums += 1; size += len(ln)
            if size > 20e6:
                break
    print(f'genre-lines-v4: kept {kept}, dropped {dropped} one-pitch basses, {loops} loop lines, {drums} drum lines')


if __name__ == '__main__':
    main()
