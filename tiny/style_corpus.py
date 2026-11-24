"""Dance-style training lines for the tiny model: house / prog / techno parts written by rules,
with random variation, at three energies.

    bass g minor house hi>[g2 ~ g2@2 ~ g3 ~ f2 ...]
    drums techno lo>[~@2 hh ~@3 hh ...], [~@4 cp ~@7 cp ~@3]

The MidiCaps loops taught the model notation and pop grooves; these teach it what the page wants
from a guest deck: 16-step bars, loops of 1-2 bars (solo phrases 2-4), the track's kick left alone,
density following the energy tag. Encoding matches the page's (deckc/site/index.html encodeBar).

    uv run python tiny/style_corpus.py [--n 40000]
"""
import argparse
import random
from pathlib import Path

HERE = Path(__file__).parent
NAMES = ['c', 'c#', 'd', 'eb', 'e', 'f', 'f#', 'g', 'ab', 'a', 'bb', 'b']
MINOR, MAJOR = [0, 2, 3, 5, 7, 8, 10], [0, 2, 4, 5, 7, 9, 11]
STYLES, ENERGIES = ['house', 'prog', 'techno'], ['lo', 'mid', 'hi']


class Key:
    def __init__(self, pc, minor):
        self.pc, self.minor = pc, minor
        self.scale = MINOR if minor else MAJOR

    def name(self):
        return f"{NAMES[self.pc]} {'minor' if self.minor else 'major'}"

    def note(self, degree, octave):
        """Scale degree (0 = tonic, may be negative or > 6) in the octave of the tonic."""
        semis = self.scale[degree % 7] + 12 * (degree // 7)
        p = self.pc + semis + 12 * octave
        return NAMES[p % 12] + str(p // 12)


def encode_bar(events, hits=False):
    """events: [(step, length, value)] -> "[a ~ b@2 ~@3 ...]" over 16 steps (as the page encodes)."""
    at = {}
    for step, length, v in events:
        x = at.setdefault(step, [[], 16])
        if v not in x[0]:
            x[0].append(v)
        x[1] = min(x[1], 1 if hits else length)
    steps, out, s = sorted(at), [], 0

    def rest(n):
        if n > 0:
            out.append('~@%d' % n if n > 1 else '~')
    for i, st in enumerate(steps):
        rest(st - s)
        vals, length = at[st]
        length = max(1, min(length, (steps[i + 1] if i + 1 < len(steps) else 16) - st))
        tok = f"[{','.join(vals)}]" if len(vals) > 1 else vals[0]
        out.append(tok + ('@%d' % length if length > 1 else ''))
        s = st + length
    rest(16 - s)
    return '[' + ' '.join(out) + ']'


def seq(bars):
    return bars[0] if len(bars) == 1 else '<' + ' '.join(bars) + '>'


def loop_pitched(bars):
    return seq([encode_bar(b) for b in bars])


def loop_drums(bars):
    sounds = []
    for b in bars:
        for _, _, v in b:
            if v not in sounds:
                sounds.append(v)
    return ', '.join(seq([encode_bar([e for e in b if e[2] == snd], hits=True) for b in bars]) for snd in sounds)


R = random.Random(0)


def pick(*opts):
    return R.choice(opts)


# ---------- bass ----------
BASS_RHYTHMS = {
    'house': {'lo': [[2, 6, 10, 14], [0, 6, 10], [2, 10, 14]],
              'mid': [[2, 6, 10, 14, 15], [0, 3, 6, 10, 14], [2, 5, 6, 10, 13, 14], [0, 2, 6, 8, 10, 14]],
              'hi': [[0, 2, 3, 6, 8, 10, 11, 14], [2, 3, 6, 7, 10, 11, 14, 15], [0, 3, 6, 8, 10, 12, 14, 15]]},
    'prog': {'lo': [[2, 6, 10, 14], [2, 3, 10, 11]],
             'mid': [[1, 2, 3, 5, 6, 7, 9, 10, 11, 13, 14, 15], [2, 3, 6, 7, 10, 11, 14, 15]],
             'hi': [[1, 2, 3, 5, 6, 7, 9, 10, 11, 13, 14, 15], [1, 2, 3, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15]]},
    'techno': {'lo': [[0, 3, 6, 10], [2, 7, 10], [0, 6, 12]],
               'mid': [[0, 2, 3, 6, 8, 10, 11, 14], [1, 2, 5, 6, 9, 10, 13, 14], [0, 3, 6, 9, 12, 14]],
               'hi': [[0, 1, 2, 3, 5, 6, 8, 9, 10, 11, 13, 14], list(range(16)), [0, 2, 3, 4, 6, 7, 8, 10, 11, 12, 14, 15]]},
}


def bass(key, style, energy, section=None):
    if section == 'break' and R.random() < 0.6:  # the track drops its kick: a held root, or root and fifth
        bars = [[(0, 16, key.note(0, 2))]] if R.random() < 0.5 else [[(0, 8, key.note(0, 2)), (8, 8, key.note(4, 2))]]
        return loop_pitched(bars)
    rhythm = pick(*BASS_RHYTHMS[style][energy])
    octave = 2
    cells = ([None, 0, 7, 0], [None, 0, 4, 7], [None, 7, 0, 4], [None, 0, 0, 7], [None, 2, 4, 0], [None, 7, 4, 2])
    halves = (pick(*cells), pick(*cells))  # a prog bass figure per half bar
    roots = pick([0, 0], [0, 5], [0, 6], [0, 3], [0, 0]) if style != 'techno' else [0, 0]
    bars = []
    for root in roots[:pick(1, 2)]:
        ev = []
        for i, st in enumerate(rhythm):
            nxt = rhythm[i + 1] if i + 1 < len(rhythm) else 16
            if style == 'prog':  # the track already rolls a one-note bass: the guest one moves (ratings)
                step = halves[st >= 8][st % 4]
                deg = root + (step or 0)
            elif style == 'techno':
                deg = root + R.choices([0, 7, -1, 4, 2], [8, 3, 1, 1, 1])[0]
            else:
                deg = root + R.choices([0, 7, 4, 6, -3], [8, 3, 2, 1, 1])[0]
            length = 1 if style in ('prog', 'techno') else min(nxt - st, pick(1, 2, 2, 3))
            ev.append((st, length, key.note(deg, octave)))
        bars.append(ev)
    return loop_pitched(bars)


# ---------- synth lead ----------
def lead(key, style, energy):
    chord = lambda d: [d, d + 2, d + 4, d + 7]  # scale degrees of a triad plus octave
    prog = pick([0, 5], [0, 6], [0, 3], [5, 6], [0, 0])
    bars = []
    for root in prog[:pick(1, 2)]:
        tones = chord(root)
        ev = []
        if style == 'prog':      # arpeggio: 16ths (hi), 8ths (mid), quarter offbeats (lo)
            step = {'hi': 1, 'mid': 1, 'lo': 2}[energy]
            shape = pick([0, 1, 2, 3], [0, 2, 1, 3], [0, 1, 2, 1], [3, 2, 1, 0], [0, 2, 3, 2])
            for i, st in enumerate(range(0, 16, step)):
                if energy == 'mid' and st % 4 == 3:
                    continue  # a broken 16th arp: a gap before each beat
                ev.append((st, 1, key.note(tones[shape[i % 4]] + (7 if energy == 'hi' and i % 8 >= 4 else 0), 4)))
        elif style == 'techno':  # hypnotic: a 3-step (dotted 8th) figure over the 4/4
            hits = {'lo': [0, 6, 12], 'mid': [0, 3, 6, 9, 12], 'hi': [0, 3, 6, 9, 12, 14]}[energy]
            notes = [key.note(tones[j], 4) for j in pick([0, 0, 1], [0, 2, 0], [0, 1, 2], [3, 0, 1])]
            for i, st in enumerate(hits):
                ev.append((st, 1, notes[i % len(notes)]))
        else:                    # house: offbeat stabs and short answers
            hits = {'lo': [2, 10], 'mid': [2, 6, 10, 13], 'hi': [2, 3, 6, 10, 11, 14]}[energy]
            for st in hits:
                ev.append((st, 1, key.note(tones[pick(0, 1, 2, 3)], 4)))
        bars.append(ev)
    return loop_pitched(bars)


# ---------- solo phrases (2 or 4 bars, call and answer, pentatonic leaning; the page picks the instrument) ----------
def solo(key, style, energy):
    penta = [0, 2, 3, 4, 6] if key.minor else [0, 1, 2, 4, 5]  # scale degrees: minor/major pentatonic
    n_notes = {'lo': (2, 4), 'mid': (3, 6), 'hi': (5, 8)}[energy]

    def motif():
        n = R.randint(*n_notes)
        start = pick(0, 0, 2, 3, 4)
        steps = sorted(R.sample(range(start, 14), min(n, 14 - start)))
        deg = pick(0, 2, 4)
        ev = []
        for i, st in enumerate(steps):
            deg = max(-2, min(9, deg + R.choices([-1, 1, 0, -2, 2], [4, 4, 1, 1, 1])[0]))
            nxt = steps[i + 1] if i + 1 < len(steps) else 16
            d = penta[deg % 5] + 7 * (deg // 5)
            ev.append((st, min(nxt - st, pick(1, 2, 2, 3)), key.note(d, 4 if d < 7 else 4)))
        return ev

    def answer(call):
        ev = [(st, ln, v) for st, ln, v in call if st < 8]
        land = pick(0, 4, 7)
        ev.append((pick(8, 10, 12), 6, key.note(land, 4)))  # a held note on the tonic, fifth or octave
        return ev
    call = motif()
    bars = [call, answer(call)]
    if R.random() < 0.5:
        bars += [motif() if R.random() < 0.6 else call, [] if energy == 'lo' else answer(call)]
    return loop_pitched(bars)


# ---------- percussion (no kick: the track has one) ----------
def drums(style, energy, section=None):
    lv = ENERGIES.index(energy)
    voices = {}
    if style == 'house':
        voices['oh'] = [2, 6, 10, 14]
        if lv >= 1:
            voices['cp'] = [4, 12]
        if lv >= 1:
            voices['hh'] = pick([0, 4, 8, 12], [1, 3, 5, 7, 9, 11, 13, 15], [3, 7, 11, 15])
        if lv >= 2:
            voices['rim'] = pick([3, 6, 11], [3, 10, 13], [6, 11, 14])
    elif style == 'prog':
        voices['hh'] = list(range(0, 16, 1 if lv >= 1 else 2))
        if lv >= 1:
            voices['cp'] = [4, 12]
        voices['oh'] = [2, 6, 10, 14] if lv != 1 or R.random() < 0.5 else [14]
        if lv >= 2:
            voices['rd'] = [0, 4, 8, 12]
    else:
        voices['hh'] = list(range(0, 16, 2 if lv == 0 else 1))
        voices['rd'] = [2, 6, 10, 14]
        if lv >= 1:
            voices['cp'] = pick([4, 12], [4, 12, 15], [4, 11, 12])
        if lv >= 1:
            voices['lt'] = pick([3, 10], [6, 13], [3, 7, 11])
        if lv >= 2:
            voices['rim'] = pick([0, 3, 6, 9, 12], [2, 5, 8, 11, 14])
    if section == 'break':  # stripped to hats and claps (hybrid-live practice)
        voices = {k: v for k, v in voices.items() if k in ('hh', 'oh', 'cp')} or {'hh': [2, 6, 10, 14]}
    # a guest layer over a full track: one voice when quiet, at most two (the page keeps the same)
    keep = R.sample(list(voices), min(1 if lv == 0 else pick(1, 2, 2), len(voices)))
    bar = [(st, 1, snd) for snd in keep for st in voices[snd]]
    bars = [bar]
    if section == 'build':  # a snare roll into the next phrase: quarters, 8ths, then 16ths
        bars.append([(st, 1, snd) for st, _, snd in bar if st < 8] + [(st, 1, 'sd') for st in (8, 10, 12, 13, 14, 15)])
    elif R.random() < 0.4:  # a second bar with a fill at its end
        drum = pick('lt', 'mt', 'ht', 'sd')  # one fill sound: each new sound is another voice line
        fill = [(st, 1, snd) for st, _, snd in bar if st < 12] + [(st, 1, drum) for st in pick([12, 14], [13, 14, 15], [12, 13, 14, 15])]
        bars.append(fill)
    return loop_drums(bars)


# ---------- effects: words after "|" that the page turns into Strudel effects (deckc/src/compose.mjs FX_WORDS) ----------
def effects(role, style, energy, section=None):
    """A plausible effect choice for a guest part that should pump the track up, by the track's section
    (techniques from hybrid DJ/live sets: build into the drop and cut the last beat, call and response
    after it, strip and wash in the breakdown); the ratings and the critic (tiny/critic.mjs) decide
    later which of them actually land."""
    low = energy != 'hi'
    odds = {'bass': {'pump': 0.8, 'build': 0.6 if low else 0.1, 'acid': 0.5 if style == 'techno' else 0.1},
            'lead': {'pump': 0.6, 'build': 0.6 if low else 0.15, 'throw': 0.5, 'wide': 0.3, 'gate': 0.15, 'dub': 0.15},
            'solo': {'throw': 0.6, 'wash': 0.4, 'wide': 0.2, 'dub': 0.2},
            'drums': {'swell': 0.5 if low else 0.1, 'build': 0.3 if low else 0.05, 'wide': 0.3}}[role]
    if section == 'build':
        odds = {'drums': {'rise': 0.6, 'cut': 0.6, 'swell': 0.3}, 'solo': {'throw': 0.6, 'cut': 0.4}}.get(
            role, {'build': 0.8, 'cut': 0.6, 'pump': 0.4})
    elif section == 'drop':
        odds = {'bass': {'pump': 0.9, 'acid': 0.3 if style == 'techno' else 0}, 'lead': {'pump': 0.6, 'call': 0.4, 'gate': 0.3},
                'solo': {'call': 0.5, 'throw': 0.4}, 'drums': {'wide': 0.3}}[role]
    elif section == 'break':
        odds = {'bass': {'wash': 0.4}, 'lead': {'wash': 0.6, 'wide': 0.4, 'dub': 0.3}, 'solo': {'wash': 0.5, 'throw': 0.5},
                'drums': {'swell': 0.5, 'wide': 0.3}}[role]
    words = [w for w, p in odds.items() if R.random() < p][:3]
    return '|' + ' '.join(words) if words else ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=40000)
    ap.add_argument('--fx', action='store_true', help='end lines with effect words (for models trained with them)')
    args = ap.parse_args()
    lines = []
    for _ in range(args.n):
        style, energy = R.choice(STYLES), R.choice(ENERGIES)
        role = R.choices(['bass', 'lead', 'solo', 'drums'], [3, 3, 3, 2])[0]
        # the section of the track the part plays over (with --fx; 15% of lines leave it out)
        section = None
        if args.fx and R.random() < 0.85:
            section = R.choices(*{'lo': (['break', 'build', 'groove'], [5, 4, 1]), 'mid': (['build', 'groove', 'break'], [35, 45, 20]),
                                  'hi': (['drop', 'groove'], [1, 1])}[energy])[0]
        tag = f'{style} {energy}' + (f' {section}' if section else '')
        fx = effects(role, style, energy, section) if args.fx else ''
        if role == 'drums':
            lines.append(f'drums {tag}>{drums(style, energy, section)}' + fx)
            continue
        key = Key(R.randrange(12), R.random() < 0.75)
        part = bass(key, style, energy, section) if role == 'bass' else {'lead': lead, 'solo': solo}[role](key, style, energy)
        lines.append(f'{role} {key.name()} {tag}>{part}' + fx)
    (HERE / 'data' / 'style.txt').write_text('\n'.join(lines) + '\n')
    print(len(lines), 'lines', sum(map(len, lines)) // 1000, 'k chars; max', max(map(len, lines)))
    for ln in lines[:6]:
        print('  ', ln[:150])


if __name__ == '__main__':
    main()
