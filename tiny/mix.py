"""Fine-tune corpora for the bigger model: style lines with effect words, the rated "good" lines, the
critic's picks (if any) and a slice of the pretraining corpus so the model keeps its general music.

    python tiny/mix.py <name> [--picks picks.txt] [--big 200000] [--hear]   -> tiny/data/<name>-{train,valid}.txt

--hear: the pretraining slice comes from big-hear-train.txt (lanes with `on` words from the other
parts), and style and rated lines get `on` words a track would plausibly have in their section.
"""
import argparse
import random
from pathlib import Path

D = Path(__file__).parent / 'data'
ap = argparse.ArgumentParser()
ap.add_argument('name')
ap.add_argument('--picks')
ap.add_argument('--big', type=int, default=200000)
ap.add_argument('--hear', action='store_true')
ap.add_argument('--extra', help='more lines taken whole (tiny/data/extra-train.txt from prep_extra.py)')
ap.add_argument('--human', help="lines people liked on the rating page (tiny/data/swiped-good.txt), x20")
ap.add_argument('--style', help="keep only pretraining-slice and extra lines of this style tag (e.g. edm), plus --general of the rest")
ap.add_argument('--general', type=int, default=0, help='with --style: this many lines of other styles, so it keeps its general music')
args = ap.parse_args()
rng = random.Random(args.name)
style = (D / 'style-fx.txt').read_text().splitlines()
rated = (D / 'rated-good.txt').read_text().splitlines()
picks = Path(args.picks).read_text().splitlines() if args.picks else []
# what a DJ track plays in each section (deckc/hear.py words), for lines that come without it
ON = {'break': (['mid', 'mid top', 'low mid', ''], [5, 3, 1, 1]), 'build': (['kick mid top', 'mid top', 'kick low mid top', 'kick top'], [4, 3, 2, 1]),
      'drop': (['kick low mid top', 'kick low top'], [7, 3]), 'groove': (['kick low mid top', 'kick low top', 'kick top'], [5, 4, 1]),
      None: (['kick low mid top', 'kick low top', 'mid top', 'mid', 'kick mid top'], [4, 2, 1, 1, 1])}


def with_on(line):
    prompt, part = line.split('>', 1)
    words = prompt.split()
    section = next((w for w in words if w in ON), None)
    on = rng.choices(*ON[section])[0]
    return f'{prompt} on {on}>{part}' if on and rng.random() < 0.85 else line


if args.hear:
    style = [with_on(l) for l in style]
    rated = [with_on(l) for l in rated]
    picks = [with_on(l) if ' on ' not in l.split('>')[0] else l for l in picks]
big = []
other = []
with open(D / ('big-hear-train.txt' if args.hear else 'big-train.txt')) as f:  # a random slice, without reading 1.2 GB into a list
    for i, line in enumerate(f):
        if args.style:
            tagged = f' {args.style} ' in line.split('>', 1)[0] + ' '
            if tagged and rng.random() < args.big / 4_000_000:
                big.append(line.rstrip('\n'))
            elif not tagged and rng.random() < args.general / 3_000_000:
                other.append(line.rstrip('\n'))
        elif rng.random() < args.big / 6_900_000:
            big.append(line.rstrip('\n'))
big += other
extra = Path(args.extra).read_text().splitlines() if args.extra else []
if args.style:
    extra = [ln for ln in extra if f' {args.style} ' in ln.split('>', 1)[0] + ' ']
human = Path(args.human).read_text().splitlines() if args.human else []
train = style[1000:] * 2 + rated * 20 + picks * 10 + big + extra + human * 20
rng.shuffle(train)
(D / f'{args.name}-train.txt').write_text('\n'.join(train) + '\n')
(D / f'{args.name}-valid.txt').write_text('\n'.join(style[:1000]) + '\n')
print(args.name, len(train), 'lines:', len(style) - 1000, 'style x2,', len(rated), 'rated x20,', len(picks), 'picks x10,', len(big), 'big,',
      len(extra), 'extra,', len(human), 'liked x20')
