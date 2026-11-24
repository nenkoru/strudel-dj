"""Transcribed MIDI → Strudel loop → A/B audio against the original bars.

    uv run python ab.py <outdir>/<name>.json [--bars-from N]

Writes next to the JSON: <name>.loop.json (caption, code, window), <name>.orig.wav (the same 4
bars of the track), <name>.strudel.wav and <name>.mix.wav (original + loop), and prints
in-key rates and a chroma similarity between the loop and the original bars.
"""
import json
import subprocess
import sys
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from convert import BARS, convert  # noqa: E402
from evalkit import scale  # noqa: E402

CAMELOT = {'1A': 'G# minor', '2A': 'D# minor', '3A': 'A# minor', '4A': 'F minor', '5A': 'C minor',
           '6A': 'G minor', '7A': 'D minor', '8A': 'A minor', '9A': 'E minor', '10A': 'B minor',
           '11A': 'F# minor', '12A': 'C# minor', '1B': 'B major', '2B': 'F# major', '3B': 'C# major',
           '4B': 'G# major', '5B': 'D# major', '6B': 'A# major', '7B': 'F major', '8B': 'C major',
           '9B': 'G major', '10B': 'D major', '11B': 'A major', '12B': 'E major'}


def track_sound(code, roles, sampled, lead_sample=False, lead=None):
    """Recreation voicing: drums on the track's own one-shots, bass as a sine sub, the pYIN lead
    line from the "other" stem as a flute, and no chords.

    The dataset voicing (TR-909 + General MIDI) made the first A/B unrecognisable, and the
    polyphonic "other" transcription of this genre (wobbles, pads, FX) is semitone clusters, not
    chords. Dropping "other" entirely in v2 also dropped track C's flute melody.
    """
    lines = [l.strip().rstrip(',') for l in code.split('\n')[1:-1]] if code.startswith('stack(') else [code]
    out = []
    for role, line in zip(roles, lines):
        if role == 'drums':
            out.append(line.replace('.bank("RolandTR909")', '.bank("trk")') if sampled else line)
        elif role == 'bass':
            out.append(line.split('.s(')[0] + '.s("sine").attack(0.005).release(0.08).shape(0.3).gain(0.8)')
        elif role == 'lead':
            voice = (f'.s("{lead}").clip(1).room(0.3).gain(0.8)' if lead else
                     '.s("trk_lead").clip(1).room(0.3).gain(0.8)' if lead_sample else '.s("gm_flute").room(0.3).gain(0.7)')
            out.append(line.split('.s(')[0] + voice)  # trk_lead: kit.py's library pick, pitched per note
    return 'stack(\n' + ',\n'.join(f'  {l}' for l in out) + '\n)'


def main(info_path):
    info_path = Path(info_path)
    info = json.loads(info_path.read_text())
    base = info_path.with_suffix('')
    res, why = convert(info_path.with_suffix('.mid'))
    if not res:
        raise SystemExit(f'convert failed: {why}')
    # The DJ library's Camelot tag (file name / TKEY) wins; the stem estimate is the fallback
    # (it lands a fifth off on half the tagged tracks, see track2midi.key_of).
    tag_key = CAMELOT.get(info.get('camelot_tag') or '')
    key = tag_key or info['key']
    samples = base.parent / 'samples' / info['name']
    gm = '--gm' in sys.argv  # dataset voicing (TR-909 + General MIDI) instead of the track's sounds
    kit = json.loads((samples / 'strudel.json').read_text()) if (samples / 'strudel.json').exists() else {}
    lead = sys.argv[sys.argv.index('--lead') + 1] if '--lead' in sys.argv else None
    code = res['code'] if gm else track_sound(res['code'], res['roles'], (samples / 'bd.wav').exists(), 'trk_lead' in kit, lead)
    tag = f'.{lead}' if lead else ''
    loop = {'id': base.name.replace(' ', '_'), 'caption': f"Loop transcribed from {info['name']}.",
            'tempo': info['tempo'], 'key': key, **res, 'code_recreation': code}
    (base.parent / f'{base.name}.loop.json').write_text(json.dumps(loop, ensure_ascii=False, indent=1))

    # Same 4 bars of the original: tick 0 is the bar line at bar0 on the constant-tempo grid.
    bar_sec = 4 * 60 / info['tempo']
    t0 = info['bar0'] + res['start_bar'] * bar_sec
    dur = BARS * bar_sec
    stems = {k: librosa.load(v, sr=44100, mono=False, offset=t0, duration=dur)[0] for k, v in info['stems'].items()}
    orig = sum(stems.values())
    sf.write(base.parent / f'{base.name}.orig.wav', orig.T, 44100)

    # Render the loop with the project renderer.
    tmp = base.parent / f'{base.name}{tag}.loop.jsonl'
    tmp.write_text(json.dumps({'id': 'loop', 'code': code, 'tempo': info['tempo']}) + '\n')
    rdir = base.parent / f'{base.name}{tag}.render'
    out = subprocess.run(['node', str(ROOT / 'js/render.mjs'), str(tmp), str(rdir), '--samples', str(samples)],
                         capture_output=True, text=True)
    print('render:', out.stdout.strip()[:300])
    loop_audio, _ = librosa.load(rdir / 'loop.wav', sr=44100, mono=False)
    loop_audio = loop_audio[:, :orig.shape[1]]
    n = min(orig.shape[1], loop_audio.shape[1])
    sf.write(base.parent / f'{base.name}{tag}.strudel.wav', loop_audio[:, :n].T, 44100)
    mix = 0.6 * orig[:, :n] / (np.abs(orig).max() + 1e-9) + 0.5 * loop_audio[:, :n] / (np.abs(loop_audio).max() + 1e-9)
    sf.write(base.parent / f'{base.name}{tag}.mix.wav', mix.T, 44100)

    # How well the loop follows the original: harmony (chroma) per lane against its stem.
    def chroma(y):
        return librosa.feature.chroma_cqt(y=librosa.to_mono(y), sr=44100, hop_length=4096)
    a, b = chroma(orig[:, :n]), chroma(loop_audio[:, :n])
    m = min(a.shape[1], b.shape[1])
    sim = float(np.mean(np.sum(a[:, :m] * b[:, :m], 0) / (np.linalg.norm(a[:, :m], axis=0) * np.linalg.norm(b[:, :m], axis=0) + 1e-9)))
    pitched = [e['pitch'] for e in res['ref'] if e['role'] != 'drums']
    in_key = float(np.mean([(p % 12) in scale(key) for p in pitched])) if key and pitched else None
    print(json.dumps({'name': info['name'], 'key': key, 'est_key': info['key'], 'tempo': info['tempo'], 'roles': res['roles'],
                      'window_bar': res['start_bar'], 'window_sec': round(float(t0), 2),
                      'in_key': in_key and round(in_key, 3), 'chroma_sim': round(sim, 3)}))
    print(code)


if __name__ == '__main__':
    main(sys.argv[1])  # [--gm] [--lead <strudel sound>]
