"""Fine-tune lines from two more CC-BY datasets, in the pretraining corpus's format (tiny/prep_big.py):

- Strudel-Synth (Decomposer paper; 21k multi-voice Strudel programs written by a language model, with
  their MIDI): the MIDI goes through the same windows, roles and `on` words as Lakh; the key is
  estimated from the notes (Krumhansl profiles); programs whose comments say house / techno / trance /
  acid / edm / minimal / progressive / garage / disco are `edm`, the rest (mostly pop, rock) `any`.
- NeuralAcid basslines (10k four-bar chord-conditioned basslines, house / techno vamps and acid
  templates in all keys): tokens -> bass lanes, key from the first chord, style `edm`.

Writes tiny/data/extra-train.txt (with 2 random transpositions of Strudel-Synth's pitched lanes).

    uv run python tiny/prep_extra.py data/raw/dl/strudel-synth/x data/raw/dl/neuralacid/train.jsonl
"""
import glob
import json
import random
import re
import sys
from collections import Counter
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from prep_big import windows, read_notes  # noqa: E402  (puts the repo root on the path for convert)
from convert import BARS, STEPS, lane_code  # noqa: E402
from prep import key_name, transpose  # noqa: E402

NAMES = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
MAJOR = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
MINOR = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
EDM = re.compile(r'\b(house|techno|trance|acid|edm|minimal|progressive|garage|disco)\b', re.I)
LEVELS = {'bass': (3, 7)}


def key_of(notes):
    """'X major' / 'X minor' by correlating the pitch-class durations with the Krumhansl profiles."""
    hist = [0.0] * 12
    for s, e, p, ch, prog in notes:
        if ch != 9:
            hist[p % 12] += max(1, e - s)
    if not sum(hist):
        return None
    def corr(profile, k):
        x = [hist[(i + k) % 12] for i in range(12)]
        mx, my = sum(x) / 12, sum(profile) / 12
        num = sum((a - mx) * (b - my) for a, b in zip(x, profile))
        den = (sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in profile)) ** 0.5
        return num / den if den else -1
    best = max(((corr(MAJOR, k), k, 'major') for k in range(12)), key=lambda t: t[0])
    best = max([best] + [(corr(MINOR, k), k, 'minor') for k in range(12)], key=lambda t: t[0])
    return f'{NAMES[best[1]]} {best[2]}'


def synth_job(path):
    name = Path(path).stem
    try:
        data = Path(path).read_bytes()
        key = key_of(read_notes(data)[1])
        lanes = windows(data, name)
    except Exception:
        return []
    js = Path(path).parent.parent / 'answers' / f'{name}.js'
    style = 'edm' if js.exists() and EDM.search(js.read_text(errors='ignore')) else 'any'
    rng, lines = random.Random(name), []
    for role, lv, mini, on in lanes:
        tags = f' {lv}' + (' on ' + on if on and rng.random() < 0.85 else '')
        if role == 'drums':
            lines.append(f'drums {style}{tags}>{mini}')
            continue
        if not key:
            continue
        for k in [0] + rng.sample([-5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6], 2):
            try:
                lines.append(f'{role} {key_name(key, k)} {style}{tags}>{transpose(mini, k)}')
            except ValueError:
                pass
    return lines


def acid_lines(path):
    """NeuralAcid tokens (<BAR>, CHORD_x, NOTE_n, DUR_n, VEL_v, <REST>) -> `bass <key> edm <level>>` lines."""
    out = []
    for line in open(path):
        r = json.loads(line)
        notes, bar, pos, pitch = [], -1, 0, None
        for t in r['tokens']:
            if t == '<BAR>':
                bar += 1; pos = bar * STEPS
            elif t.startswith('NOTE_'):
                pitch = int(t[5:])
            elif t == '<REST>':
                pitch = 'rest'
            elif t.startswith('DUR_'):
                d = int(t[4:])
                if isinstance(pitch, int) and 0 <= pos < BARS * STEPS:  # notes running past bar 4 are dropped
                    notes.append({'step': pos, 'len': d, 'pitch': pitch, 'ch': 0, 'prog': 38})
                pos += d; pitch = None
        if not notes:
            continue
        code = lane_code('bass', notes, 0)
        m = code and re.match(r'note\("([^"]*)"\)', code)
        if not m:
            continue
        first = r['chords'][0]
        root = first['root'].replace('♯', '#').lower()  # in the model's spelling, as prep.key_name writes it
        root = {'db': 'c#', 'd#': 'eb', 'gb': 'f#', 'g#': 'ab', 'a#': 'bb'}.get(root, root)
        mode = 'minor' if first['type'].startswith(('min', 'm7', 'dim')) or first['type'] == 'm' else 'major'
        per_bar = len({n['step'] for n in notes}) / BARS
        lv = 'lo' if per_bar < 3 else 'mid' if per_bar < 7 else 'hi'
        out.append(f'bass {root} {mode} edm {lv}>{m[1]}')
    return out


def main(synth_dir, acid_path):
    paths = sorted(glob.glob(f'{synth_dir}/midi/*.mid'))
    with Pool(10) as pool:
        synth = [ln for lines in pool.imap_unordered(synth_job, paths, chunksize=64) for ln in lines]
    acid = acid_lines(acid_path)
    lines = list(dict.fromkeys(synth + acid))
    random.Random(0).shuffle(lines)
    (HERE / 'data' / 'extra-train.txt').write_text('\n'.join(lines) + '\n')
    print(len(paths), 'Strudel-Synth files ->', len(synth), 'lines;', len(acid), 'NeuralAcid lines;', len(lines), 'unique')
    print(Counter(ln.split()[0] for ln in lines).most_common(), Counter(' edm ' in ln for ln in lines))
    for ln in lines[:8]:
        print('  ', ln[:140])


if __name__ == '__main__':
    main(*sys.argv[1:3])
