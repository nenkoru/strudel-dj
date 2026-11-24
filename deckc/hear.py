"""What plays in a track, bar by bar, in the words the model's prompts use after `on`:
kick (a four-on-the-floor low thump on the beats), low (a bassline between the beats), mid (chords,
leads, vocals) and top (hats, shakers, cymbals). The rating and demo pages put them in the prompt so a
part fills what the track leaves open (tiny/prep_big.py --hear writes the same words from the other
parts of multitrack MIDI).

Each band's level per bar is compared with the same band's loud bars in the same track, so a quiet
mix and a loud master give the same words.

Pockets: where in the bar the track leaves room. For each bar and each of three bands (low 40-220 Hz,
mid 250-2500, high 2500-12000) a string of 16 digits, one per 16th: how full that band is on that step
(0 empty to 9 as loud as the band gets in this track: the 90th percentile of its steps, 20 dB below it
is 0). The batch composer prefers parts whose notes land where their band is emptier than the bar's
average (deckc/src/compose.mjs pocketFit) and moves a melody up an octave when the mids are full.

    uv run python deckc/hear.py                # adds "hear" to deckc/site/data.json and deckc/mine/mine.json
    uv run python deckc/hear.py <audio> <bpm> <bar0>   # print one track's bars
    uv run python deckc/hear.py pockets        # deckc/mine/pockets.json: {track id: [[low, mid, high] per bar]}
"""
import json
import sys
from pathlib import Path

import numpy as np

from build import decode

SR, N = 44100, 4096
BANDS = {'kick': (40, 110), 'low': (40, 220), 'mid': (300, 3000), 'top': (6000, 16000)}
WORDS = ['kick', 'low', 'mid', 'top']


def hear(path, bpm, bar0):
    """One string per bar: the words present, space-separated ('' when the bar is near silent)."""
    y = decode(path)
    step = 15 / bpm  # a 16th
    n = int((len(y) / SR - bar0) / (16 * step))
    freqs = np.fft.rfftfreq(N, 1 / SR)
    win = np.hanning(N)
    band = {k: (freqs >= lo) & (freqs < hi) for k, (lo, hi) in BANDS.items()}
    db = lambda x: 10 * np.log10(x + 1e-9)

    def powers(shift):
        """Power per band summed on the beat (steps 0 4 8 12) and between (2 6 10 14, the offbeat 8ths)."""
        on, off = {k: np.zeros(n) for k in BANDS}, {k: np.zeros(n) for k in BANDS}
        for b in range(n):
            for s in range(0, 16, 2):
                i = int((bar0 + (b * 16 + s + shift) * step) * SR)
                frame = y[i:i + N]
                if len(frame) < N:
                    continue
                p = np.abs(np.fft.rfft(frame * win)) ** 2
                for k, m in band.items():
                    (on if s % 4 == 0 else off)[k][b] += p[m].sum()
        return on, off

    # the frames start where the grid says; some grids sit 30-60 ms ahead of the kick's body, and a frame
    # there catches the gap before it: the offset where the beats stand out most is the one to use
    on, off = max((powers(s) for s in (0, 0.25, 0.5, 0.75)), key=lambda p: np.nanmedian(db(p[0]['kick']) - db(p[1]['kick'])))
    level = {'kick': db(on['kick']) - db(off['kick']),  # the thump stands out on the beats
             'low': db(off['low']),                      # a bassline fills the gaps between them
             'mid': db(on['mid'] + off['mid']),
             'top': db(on['top'] + off['top'])}
    total = db(sum(on[k] + off[k] for k in ('low', 'mid', 'top')))
    loud = np.nanpercentile(total, 90)
    # how far the beats stand out of the gaps differs a lot: 12 dB over a sparse bass, 3-4 dB under a
    # rolling one; half of the track's own typical gap, never under 2.5 dB
    kick_gap = max(2.5, 0.5 * np.nanpercentile(level['kick'], 75))
    out = []
    for b in range(n):
        if total[b] < loud - 30:
            out.append('')
            continue
        words = []
        if level['kick'][b] > kick_gap and db(on['kick'][b]) > np.nanpercentile(db(on['kick']), 90) - 12:
            words.append('kick')
        for k in ('low', 'mid', 'top'):
            if level[k][b] > np.nanpercentile(level[k], 90) - (10 if k == 'top' else 8):
                words.append(k)
        out.append(' '.join(words))
    return out


POCKET_BANDS = {'low': (40, 220), 'mid': (250, 2500), 'high': (2500, 12000)}


def pockets(path, bpm, bar0, frame=2048):
    """Per bar, [low, mid, high]: 16 digits each, how full the band is on each 16th (see the module doc)."""
    y = decode(path)
    step = 15 / bpm
    n = int((len(y) / SR - bar0) / (16 * step))
    freqs = np.fft.rfftfreq(frame, 1 / SR)
    win = np.hanning(frame)
    masks = [(freqs >= lo) & (freqs < hi) for lo, hi in POCKET_BANDS.values()]
    e = np.full((n, 16, 3), np.nan)
    for b in range(n):
        for st in range(16):
            i = int((bar0 + (b * 16 + st) * step) * SR)
            f = y[i:i + frame]
            if len(f) == frame:
                p = np.abs(np.fft.rfft(f * win)) ** 2
                e[b, st] = [10 * np.log10(p[m].sum() + 1e-9) for m in masks]
    top = np.nanpercentile(e.reshape(-1, 3), 90, axis=0)
    full = np.clip((e - (top - 20)) / 20, 0, 1)
    full = np.nan_to_num(full)
    return [[''.join(str(min(9, int(v * 10))) for v in full[b, :, k]) for k in range(3)] for b in range(n)]


def main():
    if sys.argv[1:] == ['pockets']:
        here = Path(__file__).parent
        out = {}
        for t in json.loads((here / 'mine' / 'mine.json').read_text())['tracks']:
            out[t['id']] = pockets(here / 'mine' / 'tracks' / t['file'], t['bpm'], t['bar0'])
            print(t['id'], len(out[t['id']]), 'bars', flush=True)
        (here / 'mine' / 'pockets.json').write_text(json.dumps(out))
        return
    if len(sys.argv) == 4:
        for i, w in enumerate(hear(sys.argv[1], float(sys.argv[2]), float(sys.argv[3]))):
            print(i, w)
        return
    here = Path(__file__).parent
    for doc, folder in ((here / 'site' / 'data.json', here / 'site' / 'tracks'), (here / 'mine' / 'mine.json', here / 'mine' / 'tracks')):
        if not doc.exists():
            continue
        d = json.loads(doc.read_text())
        for t in d['tracks']:
            t['hear'] = hear(folder / t['file'], t['bpm'], t['bar0'])
            print(doc.parent.name, t['id'], len(t['hear']), 'bars', flush=True)
        doc.write_text(json.dumps(d, ensure_ascii=False))


if __name__ == '__main__':
    main()
