"""Assemble a per-track kit for the recreation: the track's own drum one-shots plus a pitched
lead sample from the library, chosen by timbre against the track's own melody.

    uv run python kit.py out/<name>.json      # needs out/<name>.loop.json from ab.py

Lead candidates (catalog role "lead") must hold a steady pitch (pYIN: voiced >= 30% of the first
2 s, spread < 0.7 semitone); the rest are ranked by CLAP similarity to the "other" stem over the
loop's 4 bars. Writes out/samples/<name>/strudel.json: trk_bd/sd/hh as before, and trk_lead
keyed by the sample's own pitch, so superdough repitches it to each note.
"""
import json
import shutil
import sys
from pathlib import Path

import librosa
import numpy as np

import style as S

NAMES = ['c', 'c#', 'd', 'eb', 'e', 'f', 'f#', 'g', 'ab', 'a', 'bb', 'b']


def note_name(midi):
    return f'{NAMES[midi % 12]}{midi // 12 - 1}'


def steady_pitch(path):
    y, sr = librosa.load(path, sr=22050, mono=True, duration=2)
    f0, voiced, _ = librosa.pyin(y, fmin=80, fmax=1600, sr=sr, frame_length=2048, hop_length=256)
    if voiced.mean() < 0.3:
        return None
    m = librosa.hz_to_midi(f0[voiced])
    return int(round(float(np.median(m)))) if np.std(m) < 0.7 else None


def main(info_path):
    info_path = Path(info_path)
    info = json.loads(info_path.read_text())
    loop = json.loads(info_path.with_suffix('.loop.json').read_text())
    bar = 4 * 60 / info['tempo']
    t0 = info['bar0'] + loop['start_bar'] * bar
    melody = librosa.load(info['stems']['other'], sr=S.SR, mono=True, offset=t0, duration=4 * bar)[0]
    ref = S.embed_audio([melody])[0]

    catalog = json.loads((S.LIB / 'catalog.json').read_text())
    emb = np.load(S.LIB / 'clap.npy')
    pos = {p: i for i, p in enumerate(json.loads((S.LIB / 'clap.json').read_text()))}
    ranked = []
    for e in catalog:
        if e['role'] != 'lead' or e['path'] not in pos:
            continue
        pitch = steady_pitch(S.LIB / e['path'])
        sim = float(emb[pos[e['path']]] @ ref)
        ranked.append((pitch is not None, sim, e, pitch))
    # Repitching a sample by more than about an octave smears it, so samples far from the
    # melody's register lose (the first pick was a flute at c6 for a melody around f#3-c5).
    lead = [e['pitch'] for e in loop['ref'] if e['role'] == 'lead']
    center = float(np.median(lead)) if lead else 72
    fit = lambda r: r[1] - (0.01 * max(0, abs(r[3] - center) - 7) if r[3] is not None else 0)
    ranked.sort(key=lambda r: (r[0], fit(r)), reverse=True)
    print(f'melody centre {note_name(int(round(center)))}')
    for ok, sim, e, pitch in ranked[:8]:
        print(f"  {'ok ' if ok else 'no pitch'} {sim:.3f} {e['sound']:28} {e['path']:45} {note_name(pitch) if pitch else ''}")

    kit = info_path.parent / 'samples' / info['name']
    sounds = {f'trk_{n}': [f'{n}.wav'] for n in ('bd', 'sd', 'hh') if (kit / f'{n}.wav').exists()}
    best = next((r for r in ranked if r[0]), None)
    if best:
        _, sim, e, pitch = best
        shutil.copy(S.LIB / e['path'], kit / 'lead.wav')
        sounds['trk_lead'] = {note_name(pitch): ['lead.wav']}
        print('lead:', e['sound'], e['path'], note_name(pitch), f'sim {sim:.3f}', '|', e['source'], '|', e['license'])
    (kit / 'strudel.json').write_text(json.dumps(sounds, indent=1))


if __name__ == '__main__':
    main(sys.argv[1])
