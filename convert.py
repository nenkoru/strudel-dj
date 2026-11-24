"""MIDI → Strudel loop dataset.

Takes a 4-bar window of a 4/4 MIDI file and writes it as one Strudel expression in a
small fixed dialect (see DIALECT.md): up to four lanes — drums, bass, chords, lead.
Every lane is a bar-per-step `<...>` alternation in mini notation on a 16th grid.

    uv run python convert.py data/captions.jsonl data/raw/midi data/strudel.jsonl
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import mido

BARS = 4
STEPS = 16  # per 4/4 bar
GM = {int(k): v for k, v in json.loads(Path(__file__).with_name('gm_programs.json').read_text()).items()}
GM.update({1: 'gm_piano', 2: 'gm_piano', 3: 'gm_piano'})
# GM percussion keys → TR-909 bank names. Anything else is dropped.
DRUMS = {35: 'bd', 36: 'bd', 37: 'rim', 38: 'sd', 40: 'sd', 39: 'cp', 42: 'hh', 44: 'hh', 46: 'oh',
         41: 'lt', 43: 'lt', 45: 'mt', 47: 'mt', 48: 'ht', 50: 'ht', 49: 'cr', 52: 'cr', 55: 'cr',
         57: 'cr', 51: 'rd', 53: 'rd', 59: 'rd'}
DRUM_ORDER = ['bd', 'sd', 'rim', 'cp', 'hh', 'oh', 'lt', 'mt', 'ht', 'cr', 'rd']
NAMES = ['c', 'c#', 'd', 'eb', 'e', 'f', 'f#', 'g', 'ab', 'a', 'bb', 'b']


def note_name(p):
    return f'{NAMES[p % 12]}{p // 12 - 1}'  # Strudel: c4 = 60


def read_notes(path):
    """Return (ticks_per_beat, notes, meter_ok). notes: (start, end, pitch, channel, program)."""
    mid = mido.MidiFile(path)
    notes, meter_ok = [], True
    for track in mid.tracks:
        t, program, on = 0, defaultdict(int), {}
        for msg in track:
            t += msg.time
            if msg.type == 'time_signature' and (msg.numerator, msg.denominator) != (4, 4):
                meter_ok = False
            elif msg.type == 'program_change':
                program[msg.channel] = msg.program
            elif msg.type == 'note_on' and msg.velocity > 0:
                on.setdefault((msg.channel, msg.note), []).append(t)
            elif msg.type in ('note_off', 'note_on'):
                starts = on.get((msg.channel, msg.note))
                if starts:
                    s = starts.pop(0)
                    notes.append((s, t, msg.note, msg.channel, program[msg.channel]))
    return mid.ticks_per_beat, notes, meter_ok


def quantize(notes, tpb):
    step = tpb / 4
    out = []
    for s, e, p, ch, prog in notes:
        qs = round(s / step)
        out.append({'step': qs, 'len': max(1, round(e / step) - qs), 'pitch': p, 'ch': ch, 'prog': prog,
                    'err': abs(s / step - qs)})
    return out


def assign_roles(win):
    """Pick one part per role from the notes inside a window. Parts are (channel, program)."""
    parts = defaultdict(list)
    for n in win:
        parts['drums' if n['ch'] == 9 else (n['ch'], n['prog'])].append(n)
    roles = {}
    if len(parts.get('drums', [])) >= 4:
        roles['drums'] = parts.pop('drums')
    parts.pop('drums', None)
    stats = {}
    for k, ns in parts.items():
        if len(ns) < 4:
            continue
        onsets = len({n['step'] for n in ns})
        stats[k] = (sum(n['pitch'] for n in ns) / len(ns), len(ns) / onsets, len(ns))
    bass = [k for k, (mean, poly, _) in stats.items() if (32 <= k[1] <= 39 or mean < 50) and poly < 1.3]
    if bass:
        k = max(bass, key=lambda k: stats[k][2]); roles['bass'] = parts[k]; stats.pop(k)
    chords = [k for k, (_, poly, _) in stats.items() if poly >= 1.8]
    if chords:
        k = max(chords, key=lambda k: stats[k][2]); roles['chords'] = parts[k]; stats.pop(k)
    leads = [k for k, (mean, poly, _) in stats.items() if poly < 1.5 and mean >= 55]
    if leads:
        k = max(leads, key=lambda k: (stats[k][0] > 60, stats[k][2])); roles['lead'] = parts[k]
    return roles


def resolution(bar_events, sustained):
    """Coarsest grid (slots per bar) on which every onset — and end, if sustained — falls."""
    for r in (1, 2, 4, 8, 16):
        k = STEPS // r
        if all(e['step'] % k == 0 and (not sustained or e['len'] % k == 0) for e in bar_events):
            return r
    return STEPS


def encode_bar(events, sustained, token):
    """events: [{step (0..15), len, label}] for one bar → mini notation for one cycle."""
    if not events:
        return '~'
    events = [{**e, 'len': min(e['len'], STEPS - e['step'])} for e in events]  # a lane never spills over a bar
    r = resolution(events, sustained)
    k = STEPS // r
    by_slot = defaultdict(list)
    for e in events:
        by_slot[e['step'] // k].append(e)
    slots = sorted(by_slot)
    toks, pos = [], 0
    for i, s in enumerate(slots):
        if s > pos:
            toks.append(('~', s - pos))
        nxt = slots[i + 1] if i + 1 < len(slots) else r
        dur = min(max(-(-e['len'] // k) for e in by_slot[s]), nxt - s) if sustained else 1
        toks.append((token(by_slot[s]), dur))
        pos = s + dur
    if pos < r:
        toks.append(('~', r - pos))
    if len(toks) == r and len({t for t, _ in toks}) == 1 and toks[0][0] != '~':
        return f'{toks[0][0]}*{r}' if r > 1 else toks[0][0]
    if len(toks) == 1:
        return toks[0][0]  # a weight on a whole-bar token would mean cycles inside <...>
    return '[' + ' '.join(t if d == 1 else f'{t}@{d}' for t, d in toks) + ']'


def encode_bars(bars):
    """Four per-bar strings → one cycle-per-bar pattern, collapsing repeats."""
    if len(set(bars)) == 1:
        return bars[0]
    if bars[0] == bars[2] and bars[1] == bars[3]:
        bars = bars[:2]
    return '<' + ' '.join(bars) + '>'


def pitch_token(group):
    ps = sorted({e['pitch'] for e in group})
    return note_name(ps[0]) if len(ps) == 1 else '[' + ','.join(map(note_name, ps)) + ']'


def lane_code(role, notes, start):
    per_bar = [[] for _ in range(BARS)]
    for n in notes:
        b, step = divmod(n['step'] - start, STEPS)
        per_bar[b].append({**n, 'step': step})
    if role == 'drums':
        voices = []
        for name in DRUM_ORDER:
            bars = [encode_bar([e for e in bar if DRUMS.get(e['pitch']) == name], False, lambda g: name)
                    for bar in per_bar]
            if any(b != '~' for b in bars):
                voices.append(encode_bars(bars))
        return f's("{", ".join(voices)}").bank("RolandTR909")' if voices else None
    bars = [encode_bar(bar, True, pitch_token) for bar in per_bar]
    prog = notes[0]['prog']
    return f'note("{encode_bars(bars)}").s("{GM.get(prog, "gm_piano")}")'


def convert(path):
    tpb, notes, meter_ok = read_notes(path)
    if not meter_ok or not notes:
        return None, 'meter'
    q = quantize(notes, tpb)
    last_bar = max(n['step'] for n in q) // STEPS
    best = None
    for b in range(0, max(1, last_bar - BARS + 1)):
        start, end = b * STEPS, (b + BARS) * STEPS
        win = [n for n in q if start <= n['step'] < end and (n['ch'] == 9 and n['pitch'] in DRUMS or n['ch'] != 9)]
        roles = assign_roles(win)
        score = (len(roles), min(sum(len(v) for v in roles.values()), 400))
        if best is None or score > best[0]:
            best = (score, start, roles)
    (n_roles, _), start, roles = best
    if n_roles < 2:
        return None, 'roles'
    lanes = {r: lane_code(r, roles[r], start) for r in ('drums', 'bass', 'chords', 'lead') if r in roles}
    lanes = {r: c for r, c in lanes.items() if c}
    code = 'stack(\n' + ',\n'.join(f'  {c}' for c in lanes.values()) + '\n)'
    # Reference events the code is meant to reproduce, for the round-trip check.
    ref = [{'role': r, 'step': n['step'] - start, 'len': n['len'], 'pitch': n['pitch'], 'err': round(n['err'], 3)}
           for r, ns in roles.items() if r in lanes for n in ns]
    return {'code': code, 'roles': list(lanes), 'start_bar': start // STEPS, 'ref': ref}, None


def main(captions, midi_dir, out):
    rows = [json.loads(l) for l in open(captions)]
    skipped = defaultdict(int)
    with open(out, 'w') as f:
        for i, r in enumerate(rows):
            if r['time_signature'] != '4/4':
                skipped['caption_meter'] += 1
                continue
            try:
                res, why = convert(Path(midi_dir) / r['location'].replace('/', '__'))
            except Exception as e:  # corrupt MIDI in Lakh is common
                res, why = None, type(e).__name__
            if not res:
                skipped[why] += 1
                continue
            f.write(json.dumps({'id': r['location'].split('/')[-1][:-4], 'caption': r['caption'],
                                'tempo': r['tempo'], 'key': r['key'], 'genre': r['genre'], 'mood': r['mood'],
                                'test': r['test_set'], **res}, ensure_ascii=False) + '\n')
            if i % 500 == 0:
                print(i, dict(skipped), file=sys.stderr)
    print('skipped:', dict(skipped), file=sys.stderr)


if __name__ == '__main__':
    main(*sys.argv[1:4])
