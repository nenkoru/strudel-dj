"""Pieces: the general format of the base model. A window of 4 to 16 bars of a MIDI file with every part
in it, written as a Strudel program that plays it:

    // key: f# minor | style: edm | bars: 8 | parts: 3 | mood: dark, epic
    setcps(124/60/4)
    stack(
      s("<[bd ~ bd ~]!3 [bd bd bd ~]>, <~ sd>").bank("RolandTR909"),  // drums
      note("<[f#2 ~ f#2 a2] [~ f#2 ~ e2]>").s("gm_synth_bass_1"),  // bass
      note("<[f#3,a3,c#4]@4 [e3,g#3,b3]@4>").s("gm_pad_warm")  // chords
    )

so the base learns arrangements (several parts together), longer form (up to 16 bars) and the language
the page plays, not only one part's mini-notation. To keep it open for later uses, the header's fields
are each left out now and then (a request may say little), the parts are in a random order half the
time (any part can be written given the others), and a MidiCaps caption sometimes leads the header (a
request in words). Repeats are collapsed the Strudel way: a repeating cycle `<a b>`, runs `a!3`.
"""
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from convert import DRUMS, DRUM_ORDER, GM, STEPS, encode_bar, pitch_token  # noqa: E402
from prep import key_name  # noqa: E402

LENGTHS = [4, 8, 8, 12, 16, 16]  # bars per window, drawn per window
MAX_PARTS, MAX_WINDOWS, MAX_CHARS = 8, 6, 9000
ORDER = {'drums': 0, 'bass': 1, 'chords': 2, 'lead': 3}


def collapse(bars):
    """Per-bar strings -> one cycle-per-bar pattern: a period of 1, 2, 4 or 8 bars is kept once, then runs
    of the same bar become `bar!n`."""
    n = len(bars)
    for p in (1, 2, 4, 8):
        if p < n and n % p == 0 and all(bars[i] == bars[i % p] for i in range(n)):
            bars = bars[:p]
            break
    if len(bars) == 1:
        return bars[0]
    out, i = [], 0
    while i < len(bars):
        j = i
        while j + 1 < len(bars) and bars[j + 1] == bars[i]:
            j += 1
        out.append(bars[i] if j == i else f'{bars[i]}!{j - i + 1}')
        i = j + 1
    return '<' + ' '.join(out) + '>'


def part_code(notes, start, nbars, drums):
    per_bar = [[] for _ in range(nbars)]
    for n in notes:
        b, step = divmod(n['step'] - start, STEPS)
        per_bar[b].append({**n, 'step': step})
    if drums:
        voices = []
        for name in DRUM_ORDER:
            bars = [encode_bar([e for e in bar if DRUMS.get(e['pitch']) == name], False, lambda g: name) for bar in per_bar]
            if any(b != '~' for b in bars):
                voices.append(collapse(bars))
        return f's("{", ".join(voices)}").bank("RolandTR909")' if voices else None
    bars = [encode_bar(bar, True, pitch_token) for bar in per_bar]
    return f'note("{collapse(bars)}").s("{GM.get(notes[0]["prog"], "gm_piano")}")'


def role_of(ns, prog):
    onsets = len({n['step'] for n in ns})
    mean, poly = sum(n['pitch'] for n in ns) / len(ns), len(ns) / onsets
    if (32 <= prog <= 39 or mean < 50) and poly < 1.3:
        return 'bass'
    if poly >= 1.8:
        return 'chords'
    if mean >= 55 and poly < 1.5:
        return 'lead'
    return 'part'


def pieces(q, key, style, bpm, seed, min_parts=2, caption=None, moods=()):
    """Program texts from a quantised file (convert.quantize notes)."""
    if not q:
        return []
    rng = random.Random(seed)
    total = max(n['step'] for n in q) // STEPS + 1
    taken, docs = [], []
    starts = list(range(0, total, 4))
    rng.shuffle(starts)
    for s0 in starts:
        if len(docs) >= MAX_WINDOWS:
            break
        nb = rng.choice(LENGTHS)
        if s0 + nb > total or any(s0 < e and a < s0 + nb for a, e in taken):
            continue
        start, end = s0 * STEPS, (s0 + nb) * STEPS
        parts = defaultdict(list)
        for n in q:
            if start <= n['step'] < end:
                if n['ch'] == 9:
                    if n['pitch'] in DRUMS:
                        parts['drums'].append(n)
                else:
                    parts[(n['ch'], n['prog'])].append(n)
        parts = {k: v for k, v in parts.items() if len(v) >= 4}
        if len(parts) < min_parts:
            continue
        keep = sorted(parts, key=lambda k: -len(parts[k]))[:MAX_PARTS]
        shift = [0] + ([rng.choice([-5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6])] if rng.random() < 0.5 else [])
        for k in shift:
            lanes = []
            for p in keep:
                drums = p == 'drums'
                ns = parts[p] if drums or not k else [{**n, 'pitch': n['pitch'] + k} for n in parts[p]]
                if not drums and not all(12 <= n['pitch'] <= 108 for n in ns):
                    lanes = None
                    break
                code = part_code(ns, start, nb, drums)
                if code:
                    lanes.append(('drums' if drums else role_of(ns, p[1]), code))
            if not lanes or len(lanes) < min_parts:
                continue
            if rng.random() < 0.5:
                rng.shuffle(lanes)
            else:
                lanes.sort(key=lambda r: ORDER.get(r[0], 4))
            try:
                kn = key_name(key, k) if key else None
            except ValueError:
                kn = None
            fields = [('key', kn), ('style', style), ('bars', nb), ('parts', len(lanes)),
                      ('mood', ', '.join(moods) if moods else None)]
            head = ' | '.join(f'{f}: {v}' for f, v in fields if v and (f == 'bars' or rng.random() < 0.75))
            doc = ''
            if caption and rng.random() < 0.5:
                doc += f'// {caption}\n'
            doc += f'// {head}\n'
            if bpm and rng.random() < 0.8:
                doc += f'setcps({round(bpm)}/60/4)\n'
            doc += 'stack(\n' + '\n'.join(f'  {c}{"," if i < len(lanes) - 1 else ""}  // {r}' for i, (r, c) in enumerate(lanes)) + '\n)'
            if len(doc) <= MAX_CHARS:
                docs.append(doc)
        taken.append((s0, s0 + nb))
    return docs
