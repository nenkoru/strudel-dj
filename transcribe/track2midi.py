"""Audio track → beat-aligned MIDI that ../convert.py can turn into a Strudel loop.

    uv run python track2midi.py "<track.mp3>" <outdir>

1. beat_this: beats + downbeats on the full mix. MIDI ticks are interpolated between beats, so
   tempo drift and a late first downbeat do not smear the 16th grid.
2. Demucs htdemucs: drums / bass / other / vocals stems.
3. Basic Pitch (ONNX): notes for the bass and "other" stems; bass is cut to < C4 and made monophonic.
4. Drums: band-energy onsets on the drum stem → kick (36), snare (38), closed hat (42).
Writes <outdir>/<name>.mid, the stems, and <name>.json with tempo, beats and downbeats.
"""
import json
import subprocess
import sys
from pathlib import Path

import librosa
import mido
import numpy as np
import soundfile as sf

TPB = 480
SR = 44100


def beats_of(path):
    from beat_this.inference import File2Beats
    import torch
    device = 'mps' if torch.backends.mps.is_available() else 'cpu'
    beats, downbeats = File2Beats(checkpoint_path='final0', device=device, dbn=False)(str(path))
    return np.asarray(beats), np.asarray(downbeats)


def separate(path, outdir):
    stem_dir = Path(outdir) / 'htdemucs' / Path(path).stem
    stems = {s: stem_dir / f'{s}.wav' for s in ('drums', 'bass', 'other', 'vocals')}
    if not all(p.exists() for p in stems.values()):
        subprocess.run([sys.executable, '-m', 'demucs', '-n', 'htdemucs', '-d', 'mps', '-o', str(outdir), str(path)],
                       check=True, capture_output=True)
    return stems


def pitched_notes(stem, lo=None, hi=None):
    from basic_pitch import ICASSP_2022_MODEL_PATH
    from basic_pitch.inference import predict
    model = Path(ICASSP_2022_MODEL_PATH).with_suffix('.onnx')
    _, _, events = predict(str(stem), str(model), onset_threshold=0.5, frame_threshold=0.3,
                           minimum_note_length=80, minimum_frequency=lo, maximum_frequency=hi)
    return [(float(s), float(e), int(p), float(v)) for s, e, p, v, *_ in events]


def monophonic(notes):
    """Keep the loudest note at each onset and cut each note at the next onset."""
    notes = sorted(notes, key=lambda n: (n[0], -n[3]))
    out = []
    for n in notes:
        if out and n[0] - out[-1][0] < 0.03:
            continue
        if out and out[-1][1] > n[0]:
            out[-1] = (out[-1][0], n[0], out[-1][2], out[-1][3])
        out.append(n)
    return out


KEY_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
KK_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KK_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def key_of(*stems):
    """Krumhansl–Kessler key from summed CQT chroma of the pitched stems: a fallback only.
    On 6 tagged tracks the Camelot tag fit the transcribed notes as well or better every time,
    while this estimate landed a fifth away on three of them (C vs F, D vs G, C# vs G# minor)."""
    c = sum(librosa.feature.chroma_cqt(y=librosa.load(str(s), sr=22050, mono=True)[0], sr=22050,
                                       hop_length=2048).sum(1) for s in stems)
    scores = [(np.corrcoef(c, np.roll(p, k))[0, 1], f'{KEY_NAMES[k]} {mode}')
              for k in range(12) for p, mode in ((KK_MAJOR, 'major'), (KK_MINOR, 'minor'))]
    score, key = max(scores)
    return key, round(float(score), 3)


def grid_notes(stem, period, bar0, lo, hi, poly):
    """Grid-synchronous transcription: one decision per 16th step instead of free note onsets.

    Basic Pitch misses the attacks of sustained, wobbling sub bass (its onsets land uniformly
    on the grid), but with an exact beat grid the pitch content of each step is enough. Per step:
    CQT magnitude over the step (skipping the attack), harmonic salience, up to `poly` pitches
    above half the step's peak. A note continues while its pitch persists and no onset hits.
    """
    sr, hop = 22050, 128
    y, _ = librosa.load(str(stem), sr=sr, mono=True)
    C = np.abs(librosa.cqt(y, sr=sr, hop_length=hop, fmin=librosa.midi_to_hz(lo), n_bins=hi - lo + 25,
                           bins_per_octave=12))
    sal = C[:hi - lo + 1] + 0.5 * C[12:hi - lo + 13] + 0.33 * C[19:hi - lo + 20]  # f0 + octave + twelfth
    rms = librosa.feature.rms(y=y, frame_length=1024, hop_length=hop)[0]
    onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    onset = onset / (np.percentile(onset, 99) + 1e-9)
    step = period / 4
    n_steps = int((len(y) / sr - bar0) / step)
    floor = 0.12 * np.percentile(rms, 95)
    notes, active = [], {}  # pitch → start time
    for k in range(n_steps):
        t = bar0 + k * step
        a, b = int((t + 0.25 * step) * sr / hop), int((t + step) * sr / hop)
        if b <= a or b > sal.shape[1]:
            break
        s = sal[:, a:b].mean(axis=1)
        loud = rms[a:b].mean() > floor
        hit = onset[max(0, a - 3):a + 2].max(initial=0) > 0.35
        pitches = set()
        if loud:
            order = np.argsort(s)[::-1]
            pitches = {lo + int(i) for i in order[:poly] if s[i] > 0.5 * s[order[0]]}
        for p in list(active):
            if p not in pitches or hit:
                notes.append((active.pop(p), t, p, 0.8))
        for p in pitches:
            active.setdefault(p, t)
    end = bar0 + n_steps * step
    notes += [(s0, end, p, 0.8) for p, s0 in active.items()]
    return sorted(notes)


def grid_mono(stem, period, bar0, fmin=28, fmax=200, sr=11025):
    """One monophonic line per 16th step from pYIN f0 (median over the step, attack skipped):
    the bass (defaults) or a lead such as track C's flute (fmin=180, fmax=1600, sr=22050).

    CQT salience (grid_notes) put track A's sub at F1/F#1 while pYIN heard G1/G#1/A1, which
    also matches the track's E minor tag; on track C both agreed. Same note logic as
    grid_notes: a note continues while its pitch holds and no onset hits. A single step whose
    pitch differs from two equal neighbours is taken as vibrato or an ornament and joined to them
    (v3 of the flute changed note on nearly every 16th).
    """
    hop = 256
    y, _ = librosa.load(str(stem), sr=sr, mono=True)
    f0, voiced, _ = librosa.pyin(y, fmin=fmin, fmax=fmax, sr=sr, frame_length=2048, hop_length=hop)
    onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    onset = onset / (np.percentile(onset, 99) + 1e-9)
    step = period / 4
    pitches, hits = [], []
    for k in range(int((len(y) / sr - bar0) / step)):
        t = bar0 + k * step
        a, b = int((t + 0.25 * step) * sr / hop), int((t + step) * sr / hop)
        if b > len(f0):
            break
        seg = f0[a:b][voiced[a:b]]
        pitches.append(int(round(float(librosa.hz_to_midi(np.median(seg))))) if len(seg) >= max(1, (b - a) // 2) else None)
        hits.append(onset[max(0, a - 2):a + 1].max(initial=0) > 0.35)
    for k in range(1, len(pitches) - 1):
        if pitches[k - 1] is not None and pitches[k - 1] == pitches[k + 1] != pitches[k]:
            pitches[k] = pitches[k - 1]; hits[k] = False
    notes, cur = [], None  # cur = (pitch, start)
    for k, (pitch, hit) in enumerate(zip(pitches, hits)):
        t = bar0 + k * step
        if cur and (pitch != cur[0] or hit):
            notes.append((cur[1], t, cur[0], 0.8)); cur = None
        if pitch is not None and cur is None:
            cur = (pitch, t)
    if cur:
        notes.append((cur[1], bar0 + len(pitches) * step, cur[0], 0.8))
    return notes


DRUM_KEYS = (36, 38, 42)  # kick, snare, closed hat


def drum_hits(stem, detail=False):
    """(time, gm_key) per drum onset: one onset pass, then each hit gets exactly one class.

    Per-band onset envelopes (the first version) fired kick and snare on the same broadband hits,
    so 3 of 4 bars had identical kick and snare patterns. Now: onsets of the whole drum stem,
    each band's share of the energy (low 30-150 Hz, mid 150-4 kHz, high 6-11 kHz) over the first
    60 ms; the largest share names the hit. Shares, not absolute energies: dubstep snares carry a
    lot of low end. Medians on track C by grid position: step 0 low 0.48, step 8 mid 0.55,
    the rest high 0.67. (3-cluster k-means on the same shares still merged kick and snare.)
    """
    y, sr = librosa.load(str(stem), sr=22050, mono=True)
    hop = 256
    times = librosa.onset.onset_detect(y=y, sr=sr, hop_length=hop, units='time', backtrack=False)
    S = np.abs(librosa.stft(y, n_fft=1024, hop_length=hop))
    f = librosa.fft_frequencies(sr=sr, n_fft=1024)
    bands = [(f >= 30) & (f < 150), (f >= 150) & (f < 4000), (f >= 6000) & (f < 11000)]
    feats = []
    for t in times:
        a = int(t * sr / hop); b = a + max(1, int(0.06 * sr / hop))
        feats.append([S[m, a:b].sum() for m in bands])
    E = np.asarray(feats)
    Z = E / (E.sum(1, keepdims=True) + 1e-9)  # band shares
    labels = Z.argmax(1)
    hits = [(float(t), DRUM_KEYS[l]) for t, l in zip(times, labels)]
    if not detail:
        return hits
    loud = np.log1p(E.sum(1))
    top2 = np.sort(Z, axis=1)[:, -2:]
    dist = top2[:, 0] - top2[:, 1]  # negative margin: lower is a purer hit
    return hits, [{'t': float(t), 'key': DRUM_KEYS[l], 'loud': float(v), 'dist': float(d)}
                  for t, l, v, d in zip(times, labels, loud, dist)]


def one_shots(stem, detail, outdir):
    """Cut one representative hit per drum class from the stem: isolated (next onset far enough
    away for the sample's length), loud (top half) and typical (closest to its cluster centre)."""
    y, sr = sf.read(str(stem), always_2d=True)
    times = np.asarray([h['t'] for h in detail])
    outdir.mkdir(parents=True, exist_ok=True)
    lengths = {36: 0.45, 38: 0.35, 42: 0.12}
    names = {36: 'bd', 38: 'sd', 42: 'hh'}
    for key, length in lengths.items():
        cands = [h for h in detail if h['key'] == key]
        if not cands:
            continue
        loud_cut = np.median([h['loud'] for h in cands])
        def gap(h):
            later = times[times > h['t'] + 0.01]
            return later[0] - h['t'] if len(later) else 9
        pool = [h for h in cands if h['loud'] >= loud_cut] or cands
        best = min(pool, key=lambda h: (gap(h) < length * 0.6, h['dist']))
        a = max(0, int((best['t'] - 0.004) * sr))
        n = int(min(length, gap(best) - 0.003) * sr) if gap(best) < length else int(length * sr)
        clip = y[a:a + n].copy()
        fade = min(len(clip), int(0.02 * sr))
        clip[-fade:] *= np.linspace(1, 0, fade)[:, None]
        clip /= np.abs(clip).max() + 1e-9
        sf.write(outdir / f'{names[key]}.wav', clip * 0.9, sr)


def grid(beats, downbeats, hits, bpm=None):
    """Constant-tempo grid (period, time of a bar line) for electronic tracks.

    beat_this's beat list is only a source of candidates: it drops beats in breakdowns, flips
    between 140 and 70 BPM in half-time music, and on one swung track followed a 210 BPM
    (3/2) pulse. Candidates are its interval clusters times 1, 2, 1/2, 3/2, 2/3 within
    100-180 BPM; the drum stem's onsets decide. On the right period they all sit on 16ths, so
    their circular concentration on a 16th grid peaks; over a whole track that peak is narrower
    than 1e-4 in relative period, which also gives the exact tempo (140.00, not 140.35 from a
    median of 20 ms-quantized intervals). The bar line is the 16th offset that the most
    downbeats land on (kicks break ties).
    """
    d = np.diff(beats)
    if bpm:
        cands = [60 / bpm]
    else:
        clusters = {float(np.mean(d[np.abs(d / c - 1) < 0.08])) for c in np.unique(np.round(d, 2))
                    if np.mean(np.abs(d / c - 1) < 0.08) >= 0.1}
        cands = sorted({c * m for c in clusters for m in (1, 2, 0.5, 1.5, 2 / 3) if 100 <= 60 / (c * m) <= 180})
    t = np.asarray([h for h, _ in hits])
    kicks = np.asarray([h for h, k in hits if k == 36])

    def concentration(P):
        return np.abs(np.exp(2j * np.pi * t / (P / 4)).mean())

    def refine(P):  # coarse ±1.5% scan, then a fine one around its peak
        for span, n in ((0.015, 1501), (4e-5, 81)):
            r, P = max((concentration(q), q) for q in P * (1 + np.linspace(-span, span, n)))
        return r, P

    period = float(max(refine(P) for P in cands)[1])
    sixteenth = period / 4
    # Phase from kicks only: swung or flammed hats pulled the mean of all hits half a 16th off
    # (AFM "Sometimes", DCM "Osc 3": kicks split between steps 0 and 1, the third deck ~60 ms late).
    ref = kicks if len(kicks) >= 32 else t
    phase = float(np.angle(np.exp(2j * np.pi * ref / sixteenth).mean()) / (2 * np.pi) * sixteenth) % sixteenth
    bar = 4 * period

    def near(times, line):
        dist = (times - line) % bar
        return np.sum(np.minimum(dist, bar - dist) < 0.07)

    j = max(range(16), key=lambda j: (near(downbeats, phase + j * sixteenth), near(kicks, phase + j * sixteenth)))
    return period, (phase + j * sixteenth) % bar


def kick_attacks(stem, sr=11025, hop=32):
    """Kick attack times from the drum stem's 30-100 Hz band at ~3 ms resolution: the start of
    each rise, not the onset detector's peak, which lags the attack by tens of milliseconds."""
    y, _ = librosa.load(str(stem), sr=sr, mono=True)
    S = np.abs(librosa.stft(y, n_fft=1024, hop_length=hop))
    f = librosa.fft_frequencies(sr=sr, n_fft=1024)
    low = np.log1p(S[(f >= 30) & (f < 100)].sum(0))
    rise = np.maximum(0, np.diff(low, prepend=low[0]))
    peaks = librosa.util.peak_pick(rise, pre_max=20, post_max=20, pre_avg=100, post_avg=100,
                                   delta=0.3 * np.percentile(rise, 99), wait=60)
    # the attack starts where the rise first reaches half its peak, a few frames earlier
    out = []
    for p in peaks:
        a = p
        while a > 0 and rise[a - 1] > 0.5 * rise[p]:
            a -= 1
        out.append(a * hop / sr)
    return np.asarray(out)


def refine_phase(period, bar0, kicks, span=0.09):
    """Shift the bar line so kick attacks fall on beats: the onset-based phase was 27-70 ms late
    on all six house and dub tracks checked, so the third deck sounded behind the track."""
    if len(kicks) < 16:
        return bar0
    def score(d):
        x = (kicks - bar0 - d) / period
        return np.sum(np.abs(x - np.round(x)) < 0.02)
    d = max(np.arange(-span, span + 1e-9, 0.001), key=score)
    return bar0 + float(d)


def to_ticks(t, period, bar0):
    return int(round((t - bar0) / period * TPB))


def write_midi(path, parts, period, bar0):
    bpm = 60 / period
    mid = mido.MidiFile(ticks_per_beat=TPB)
    meta = mido.MidiTrack(); mid.tracks.append(meta)
    meta.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(bpm)))
    meta.append(mido.MetaMessage('time_signature', numerator=4, denominator=4))
    for channel, program, notes in parts:
        tr = mido.MidiTrack(); mid.tracks.append(tr)
        tr.append(mido.Message('program_change', channel=channel, program=program, time=0))
        msgs = []
        for s, e, p, v in notes:
            a, b = to_ticks(s, period, bar0), to_ticks(e, period, bar0)
            if a < 0:
                continue
            vel = max(1, min(127, int(v * 127)))
            msgs += [(a, 1, mido.Message('note_on', channel=channel, note=p, velocity=vel)),
                     (max(b, a + 30), 0, mido.Message('note_off', channel=channel, note=p, velocity=0))]
        t = 0
        for tick, _, m in sorted(msgs, key=lambda x: (x[0], x[1])):
            tr.append(m.copy(time=tick - t)); t = tick
    mid.save(path)
    return bpm, bar0


def main(track, outdir):
    track, outdir = Path(track), Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    name = track.stem.split(' -  - ')[0]
    beats, downbeats = beats_of(track)
    stems = separate(track, outdir / 'stems')
    hits, detail = drum_hits(stems['drums'], detail=True)
    one_shots(stems['drums'], detail, outdir / 'samples' / name)
    bpm_hint = float(sys.argv[sys.argv.index('--bpm') + 1]) if '--bpm' in sys.argv else None
    period, bar0 = grid(beats, downbeats, hits, bpm_hint)
    kicks = kick_attacks(stems['drums'])
    bar0 = refine_phase(period, bar0, kicks)
    if '--basic-pitch' in sys.argv:
        bass = monophonic([n for n in pitched_notes(stems['bass'], hi=262) if n[2] < 60])
        lead = []
        other = pitched_notes(stems['other'], lo=110)
    else:
        # Tuning correction (librosa.estimate_tuning) was tried and lowered bass in-key rate 0.62 → 0.54.
        bass = grid_mono(stems['bass'], period, bar0)
        lead = grid_mono(stems['other'], period, bar0, fmin=180, fmax=1600, sr=22050)
        other = grid_notes(stems['other'], period, bar0, lo=48, hi=84, poly=3)  # C3–C6
    drums = [(t, t + 0.05, k, 0.9) for t, k in hits]
    bpm, t0 = write_midi(outdir / f'{name}.mid', [(9, 0, drums), (0, 38, bass), (1, 89, other), (2, 73, lead)], period, bar0)
    key, key_score = key_of(stems['bass'], stems['other'])
    tag = track.stem.split(' -  - ')[-1] if ' -  - ' in track.stem else None
    info = {'name': name, 'tempo': round(float(bpm), 3), 'bar0': float(t0), 'key': key, 'key_score': key_score,
            'camelot_tag': tag, 'kicks': [round(float(k), 4) for k in kicks], 'beats': beats.tolist(), 'downbeats': downbeats.tolist(),
            'stems': {k: str(v) for k, v in stems.items()},
            'counts': {'drums': len(drums), 'bass': len(bass), 'other': len(other), 'lead': len(lead)}}
    (outdir / f'{name}.json').write_text(json.dumps(info))
    print(json.dumps({k: info[k] for k in ('name', 'tempo', 'bar0', 'key', 'camelot_tag', 'counts')}))


if __name__ == '__main__':
    main(*sys.argv[1:3])
