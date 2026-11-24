"""Creative Commons dance tracks -> multitrack MIDI, for training lines in the domain the model plays in
(house, techno, trance), where the MIDI datasets are thin. Per track:

1. the tempo and a bar grid: beats from librosa, the BPM from their median spacing (dance music keeps
   one tempo), the grid's phase from the low band (the kick), so a bar starts on a beat with a kick;
2. stems with Demucs (htdemucs: bass, drums, other, vocals), loaded once per process;
3. bass and other (the leads, chords, pads) transcribed by Spotify's basic-pitch, its onsets moved 25 ms
   earlier (they came that late on a test clip; then 88% of the other stem's onsets sat within a
   quarter 16th of the grid); the bass kept monophonic (lowest note per 16th);
4. drums from the drum stem's onsets in three bands: kick below 120 Hz, clap/snare 1-5 kHz, hats above
   7 kHz (open when the hat rings past 90 ms);
5. one MIDI file: bass (GM program 38), other (81), drums (channel 10), tempo set, bar one at time 0.

Runs in the separate Python 3.11 environment with demucs and basic-pitch (see README).

    bp/bin/python tiny/audio2midi.py <tar of MTG-Jamendo audio> <genre.tsv> <out dir> [--max-seconds 270]
"""
import argparse
import csv
import json
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path

import librosa
import numpy as np
import pretty_midi
import soundfile as sf
from demucs.api import Separator, save_audio

_BP_MODEL = None


def _bp_model():
    """The basic-pitch ONNX model, loaded once and cached for the life of the process."""
    global _BP_MODEL
    if _BP_MODEL is None:
        from basic_pitch.inference import Model
        from basic_pitch import ICASSP_2022_MODEL_PATH
        _BP_MODEL = Model(ICASSP_2022_MODEL_PATH)
    return _BP_MODEL


SR = 22050
STYLE = {'house': 'house', 'deephouse': 'house', 'techno': 'techno', 'minimal': 'techno', 'trance': 'prog',
         'progressive': 'prog', 'dance': 'edm', 'electronic': 'edm', 'breakbeat': 'edm'}
WANT = {'house', 'deephouse', 'techno', 'minimal', 'trance', 'progressive', 'dance'}


def grid(drums):
    """(bpm, time of a beat with a kick) from the drum stem's low band: every BPM from 100 to 150 in 0.02
    steps and 48 phases, scored by the kick energy that falls on its beats (a comb filter). librosa's beat
    tracker gave half tempos and 3% errors on these tracks, which over four minutes is no grid at all."""
    y, _ = librosa.load(str(drums), sr=SR, mono=True)
    hop = 128
    S = np.abs(librosa.stft(y, n_fft=1024, hop_length=hop))
    f = librosa.fft_frequencies(sr=SR, n_fft=1024)
    env = librosa.onset.onset_strength(S=librosa.amplitude_to_db(S[(f >= 30) & (f < 150)]), sr=SR, hop_length=hop)
    if env.max() <= 0:
        return None
    fps = SR / hop
    best = (0.0, None, None)
    for bpm in np.arange(100, 150, 0.02):
        beat = 60 / bpm * fps  # in frames
        n = int((len(env) - beat) / beat)
        if n < 32:
            continue
        k = np.arange(n) * beat
        for ph in np.linspace(0, beat, 48, endpoint=False):
            score = env[(k + ph).astype(int)].mean()
            if score > best[0]:
                best = (score, bpm, ph / fps)
    # a beat must stand out from the half-beat between (else it is no four-on-the-floor grid)
    score, bpm, phase = best
    if bpm is None:
        return None
    beat = 60 / bpm * fps
    k = np.arange(int((len(env) - beat) / beat)) * beat
    off = env[(k + phase * fps + beat / 2).astype(int) % len(env)].mean()
    if score < 1.5 * off:
        return None
    return float(bpm), float(phase)


def notes_of(path, lo, hi, mono):
    from basic_pitch.inference import predict
    _, _, events = predict(str(path), _bp_model(), onset_threshold=0.5, frame_threshold=0.3, minimum_note_length=80)
    out = [(max(0.0, s - 0.025), max(0.0, e - 0.025), int(p), int(v * 127)) for s, e, p, v, *_ in events if lo <= p <= hi]
    if mono:  # the lowest note of each onset cluster
        out.sort(key=lambda n: (round(n[0] * 40), n[2]))
        keep, last = [], None
        for n in out:
            k = round(n[0] * 40)
            if k != last:
                keep.append(n); last = k
        out = keep
    return out


def drums_of(path):
    y, _ = librosa.load(str(path), sr=SR, mono=True)
    hits = []
    S = np.abs(librosa.stft(y, n_fft=1024, hop_length=256))
    f = librosa.fft_frequencies(sr=SR, n_fft=1024)
    for name, (lo, hi), pitch in [('kick', (30, 120), 36), ('clap', (1000, 5000), 39), ('hat', (7000, 11000), 42)]:
        band = S[(f >= lo) & (f < hi)].sum(0)
        env = librosa.onset.onset_strength(S=librosa.amplitude_to_db(S[(f >= lo) & (f < hi)]), sr=SR, hop_length=256)
        on = librosa.onset.onset_detect(onset_envelope=env, sr=SR, hop_length=256, units='frames', backtrack=False, delta=0.2)
        for fr in on:
            t = fr * 256 / SR
            p = pitch
            if name == 'hat':  # open when it still rings 90 ms on
                later = min(len(band) - 1, fr + int(0.09 * SR / 256))
                if band[later] > 0.35 * band[fr]:
                    p = 46
            hits.append((t, t + 0.05, p, 100))
    return hits


def on_grid(notes, bpm, phase):
    """Share of onsets within a quarter 16th of the grid: how well the transcription and the grid agree."""
    if not notes:
        return 0.0
    step = 15 / bpm
    x = np.array([(n[0] - phase) / step for n in notes])
    return float(np.mean(np.abs(x - np.round(x)) < 0.25))


def calibrate(notes, bpm, phase):
    """The notes moved by the constant offset (within half a 16th) that puts most onsets on the grid.
    basic-pitch's onsets came 55-85 ms late against the kick grid, the same within a track; a shift
    smaller than half a 16th cannot turn a real offbeat into an onbeat, so syncopation survives."""
    if len(notes) < 20:
        return notes, on_grid(notes, bpm, phase)
    step = 15 / bpm
    shifts = np.linspace(-step / 2, step / 2, 25)
    fit = [on_grid([(n[0] - s,) for n in notes], bpm, phase) for s in shifts]
    s = float(shifts[int(np.argmax(fit))])
    return [(max(0.0, a - s), max(0.0, b - s), p, v) for a, b, p, v in notes], max(fit)


def to_midi(bpm, phase, bass, other, drums, out):
    pm = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    bar = 240 / bpm
    shift = phase % bar  # bar one at time zero
    for prog, notes, is_drum in [(38, bass, False), (81, other, False), (0, drums, True)]:
        inst = pretty_midi.Instrument(program=prog, is_drum=is_drum)
        for s, e, p, v in notes:
            if s - shift >= 0:
                inst.notes.append(pretty_midi.Note(velocity=max(1, min(127, v)), pitch=p, start=s - shift, end=max(s - shift + 0.03, e - shift)))
        pm.instruments.append(inst)
    pm.time_signature_changes.append(pretty_midi.TimeSignature(4, 4, 0))
    pm.write(str(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('tar'); ap.add_argument('genres'); ap.add_argument('out')
    ap.add_argument('--max-seconds', type=float, default=270)
    ap.add_argument('--limit', type=int, default=0, help='stop after this many tracks (0: all)')
    ap.add_argument('--device', default='mps', help='Demucs device: cuda, cuda:0, cuda:1, mps or cpu')
    args = ap.parse_args()
    tags = {}
    with open(args.genres) as f:
        for row in list(csv.reader(f, delimiter='\t'))[1:]:
            g = [t.split('---')[1] for t in row[5:]]
            if WANT & set(g):
                tags[row[3]] = g
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    meta_path = out / 'meta.jsonl'
    done = {json.loads(l)['path'] for l in open(meta_path)} if meta_path.exists() else set()
    sep = Separator(model='htdemucs', device=args.device)
    with tarfile.open(args.tar) as tf, tempfile.TemporaryDirectory() as tmp:
        for m in tf:
            rel = '/'.join(m.name.split('/')[-2:]).replace('.low.mp3', '.mp3')
            if not m.isfile() or rel not in tags or rel in done:
                continue
            mp3 = Path(tmp) / 'track.mp3'
            mp3.write_bytes(tf.extractfile(m).read())
            t0 = time.monotonic()
            wav = Path(tmp) / 'track.wav'
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', '20', '-t', str(args.max_seconds), '-i', str(mp3), '-ac', '2', '-ar', '44100', str(wav)], check=True)
            _, stems_t = sep.separate_audio_file(str(wav))
            for name, tensor in stems_t.items():
                p = Path(tmp) / 'htdemucs' / 'track' / f'{name}.wav'
                p.parent.mkdir(parents=True, exist_ok=True)
                save_audio(tensor, p, samplerate=sep.samplerate)
            stems = Path(tmp) / 'htdemucs' / 'track'
            g = grid(stems / 'drums.wav')
            if not g:
                print(rel, 'no steady kick: skipped', f'{time.monotonic() - t0:.1f}s', flush=True)
                continue
            bpm, phase = g
            bass, fit_b = calibrate(notes_of(stems / 'bass.wav', 24, 60, mono=True), bpm, phase)
            other, fit_o = calibrate(notes_of(stems / 'other.wav', 48, 96, mono=False), bpm, phase)
            drums = drums_of(stems / 'drums.wav')
            if max(fit_b, fit_o) < 0.6:  # neither part settles on the grid: a loose or rubato track
                print(rel, 'parts off the grid: skipped', f'{time.monotonic() - t0:.1f}s', flush=True)
                continue
            name = rel.replace('/', '_').replace('.mp3', '.mid')
            to_midi(bpm, phase, bass, other, drums, out / name)
            style = next((STYLE[t] for t in tags[rel] if t in STYLE and STYLE[t] != 'edm'), 'edm')
            grid_fit = [round(on_grid(x, bpm, phase), 2) for x in (bass, other, drums)]
            with open(meta_path, 'a') as f:
                f.write(json.dumps({'path': rel, 'midi': name, 'bpm': round(bpm, 3), 'style': style, 'tags': tags[rel],
                                    'notes': [len(bass), len(other), len(drums)], 'on_grid': grid_fit}) + '\n')
            print(rel, f'{bpm:.2f} bpm', style, 'notes', len(bass), len(other), len(drums), 'on grid', grid_fit, f'{time.monotonic() - t0:.1f}s', flush=True)
            done.add(rel)
            if args.limit and len(done) >= args.limit:
                break


if __name__ == '__main__':
    main()
