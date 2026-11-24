"""Line each track's bar grid up with its kicks as the files actually decode. The owner heard parts
come in "sharply off" on the rating page: against kick onsets the rekordbox grid in mine.json was
-85..+95 ms off, track by track (a 16th at 124 BPM is 121 ms), likely the AAC encoder delay of the mp4s
plus a few grids rekordbox had started early. For every track (mine/mine.json and site/data.json) this
finds the shift within 0..+100 ms that puts the most kick-band onset strength on the beats and moves
`bar0` by it (the shift is kept as `grid_shift`, and re-running starts from the original bar0).

Runs in the Python 3.11 environment with librosa (see README).

    bp/bin/python deckc/align.py   (NOT applied: the owner heard parts get worse after it, 2026-11-05; see README)
"""
import json
import subprocess
from pathlib import Path

import librosa
import numpy as np

HERE = Path(__file__).parent
SR = 22050
HOP = 64


def decode(path):
    out = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', str(path), '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(out, np.float32)


def shift_of(path, bpm, bar0):
    y = decode(path)
    S = np.abs(librosa.stft(y, n_fft=1024, hop_length=HOP))
    f = librosa.fft_frequencies(sr=SR, n_fft=1024)
    env = librosa.onset.onset_strength(S=librosa.amplitude_to_db(S[(f >= 30) & (f < 150)]), sr=SR, hop_length=HOP)
    beat = 60 / bpm
    beats = bar0 + np.arange(8, int((len(y) / SR - bar0) / beat) - 8) * beat
    # 0..+100 ms: the mp4s all carry the same encoder delay (~+50 ms); a wider window let some tracks
    # lock onto the 16th before the kick (a double kick or a bass hit), 120 ms off
    offs = np.arange(0.0, 0.1001, 0.002)
    score = [env[np.clip(((beats + o) * SR / HOP).astype(int), 0, len(env) - 1)].mean() for o in offs]
    i = int(np.argmax(score))
    contrast = score[i] / max(1e-9, np.median(score))  # how clearly the kick picks one offset
    return float(offs[i]), float(contrast)


def main():
    for doc, folder in ((HERE / 'mine' / 'mine.json', HERE / 'mine' / 'tracks'), (HERE / 'site' / 'data.json', HERE / 'site' / 'tracks')):
        if not doc.exists():
            continue
        d = json.loads(doc.read_text())
        for t in d['tracks']:
            base = t['bar0'] - t.get('grid_shift', 0.0)
            shift, contrast = shift_of(folder / t['file'], t['bpm'], base)
            if contrast < 1.3:  # no clear kick (ambient intros, broken beats): leave the grid alone
                shift = 0.0
            t['grid_shift'] = round(shift, 3)
            t['bar0'] = round(base + shift, 4)
            print(f"{doc.parent.name:5s} {t['id'][:26]:26s} shift {shift * 1000:+5.0f} ms  (contrast {contrast:.1f})", flush=True)
        doc.write_text(json.dumps(d, ensure_ascii=False))


if __name__ == '__main__':
    main()
