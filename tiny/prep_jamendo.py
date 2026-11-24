"""Training lines from the dance tracks transcribed by tiny/audio2midi.py: the same windows, roles and
`on` words as the Lakh corpus (tiny/prep_big.py), the key estimated from the notes (prep_extra.key_of),
the style from the track's Jamendo tags (house, techno, prog, edm), and two random transpositions.
Drum lanes are left out: the band-onset drum transcription mixes claps with hats and drops kicks.
Writes tiny/data/jamendo-train.txt.

    uv run python tiny/prep_jamendo.py data/raw/dl/jamendo/midi
"""
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from prep_big import windows, read_notes  # noqa: E402
from prep_extra import key_of  # noqa: E402
from prep import key_name, transpose  # noqa: E402


def main(folder):
    folder = Path(folder)
    lines, tracks = [], 0
    for row in (json.loads(l) for l in open(folder / 'meta.jsonl')):
        path = folder / row['midi']
        if not path.exists():
            continue
        data = path.read_bytes()
        key = key_of(read_notes(data)[1])
        if not key:
            continue
        tracks += 1
        rng = random.Random(row['midi'])
        for role, lv, mini, on in windows(data, row['midi']):
            if role == 'drums':
                continue
            tags = f" {row['style']} {lv}" + (' on ' + on if on and rng.random() < 0.85 else '')
            for k in [0] + rng.sample([-5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6], 2):
                try:
                    lines.append(f'{role} {key_name(key, k)}{tags}>{transpose(mini, k)}')
                except ValueError:
                    pass
    lines = list(dict.fromkeys(lines))
    random.Random(0).shuffle(lines)
    (HERE / 'data' / 'jamendo-train.txt').write_text('\n'.join(lines) + '\n')
    print(tracks, 'tracks ->', len(lines), 'lines')


if __name__ == '__main__':
    main(sys.argv[1])
