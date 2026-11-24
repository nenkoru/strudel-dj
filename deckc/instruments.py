"""Pitched instruments for the guest parts, from freely licensed multisamples (the owner tired of the
same oscillator squeak on every melody): each note file decoded, peak-normalised, cut to a few seconds
with a fade, saved as mono mp3 under site/samples/<name>/, and added to site/kit.json as a note map
({"wurli": {"a1": ["wurli/A1.mp3"], ...}}) that superdough pitches between.

Sources (data/raw/dl/, see README for links):
- FreePats (CC0): lately-bass, fm-piano1 (DX7 E.Piano 1, the v80 layer), new-age, sweep-pad,
  synth-strings-1, synth-pad-choir, synth-fifths, synth-calliope, synth-brass-2
- Versilian Community Sample Library (CC0): TX81Z FM Piano (the vl3 layer)
- Greg Sullivan E-Pianos (CC BY 3.0, credit: Greg Sullivan, via sfzinstruments): Wurlitzer EP200 (f layer)
- FluidR3 GM (CC BY 3.0, credit: Frank Wen; mp3s by gleitz/midi-js-soundfonts): every third semitone of
  23 General MIDI instruments (keys, organs, mallets, pads, voices, strings, brass, synth basses)

    uv run python deckc/instruments.py
"""
import json
import re
import subprocess
from pathlib import Path

import numpy as np

from build import decode

HERE = Path(__file__).parent
DL = HERE.parent / 'data' / 'raw' / 'dl'
SR = 44100
NAMES = ['c', 'c#', 'd', 'd#', 'e', 'f', 'f#', 'g', 'g#', 'a', 'a#', 'b']
PC = {'c': 0, 'c#': 1, 'db': 1, 'd': 2, 'd#': 3, 'eb': 3, 'e': 4, 'f': 5, 'f#': 6, 'gb': 6, 'g': 7, 'g#': 8, 'gs': 8, 'ab': 8,
      'a': 9, 'a#': 10, 'bb': 10, 'b': 11, 'cs': 1, 'ds': 3, 'fs': 6, 'as': 10}

# name: (files glob, note from file stem, seconds kept: short for keys and plucks, long for pads)
INSTRUMENTS = {
    'lately': ('freepats/lately-bass/samples/*.wav', r'^([A-G]#?)(\d)$', 1.5),
    'dxpiano': ('freepats/fm-piano1/samples/*v80.flac', r'^([A-G]#?)(\d)v80$', 2.5),
    'fmpiano': ('fmpiano/*.wav', r'^FMPiano_([A-G]s?)(\d)$', 2.5),
    'wurli': ('wurli/*.m4a', r'^([a-g]b?)(\d)f$', 2.5),
    'newage': ('freepats/new-age/samples/*.flac', r'^([A-G]#?)(\d)$', 4),
    'sweep': ('freepats/sweep-pad/samples/*.flac', r'^([A-G]#?)(\d)$', 4),
    'strings': ('freepats/synth-strings-1/samples/*.flac', r'^([A-G]#?)(\d)$', 4),
    'choir': ('freepats/synth-pad-choir/samples/*.flac', r'^([A-G]#?)(\d)$', 4),
    'fifths': ('freepats/synth-fifths/samples/*.flac', r'^([A-G]#?)(\d)$', 2),
    'calliope': ('freepats/synth-calliope/samples/*.flac', r'^([A-G]#?)(\d)$', 3),
    'brass': ('freepats/synth-brass-2/samples/*.flac', r'^([A-G]#?)(\d)$', 2),
}
FLUID = {  # short name: (General MIDI name, seconds kept)
    'ep1': ('electric_piano_1', 2.5), 'ep2': ('electric_piano_2', 2.5), 'organ': ('drawbar_organ', 2), 'porgan': ('percussive_organ', 2),
    'clav': ('clavinet', 1.5), 'vibes': ('vibraphone', 2.5), 'marimba': ('marimba', 1.5), 'kalimba': ('kalimba', 1.5),
    'steeldrum': ('steel_drums', 1.5), 'musicbox': ('music_box', 2), 'pizz': ('pizzicato_strings', 1.5),
    'ensemble': ('string_ensemble_1', 3), 'warmpad': ('pad_2_warm', 4), 'polysynth': ('pad_3_polysynth', 3), 'halo': ('pad_7_halo', 4),
    'aahs': ('choir_aahs', 3), 'oohs': ('voice_oohs', 3), 'orchhit': ('orchestra_hit', 1.5), 'brasssec': ('brass_section', 2),
    'panflute': ('pan_flute', 2.5), 'synbass1': ('synth_bass_1', 1.5), 'synbass2': ('synth_bass_2', 1.5), 'fretless': ('fretless_bass', 1.5),
    'upright': ('acoustic_bass', 1.5), 'fingerbass': ('electric_bass_finger', 1.5), 'pickbass': ('electric_bass_pick', 1.5), 'slapbass': ('slap_bass_1', 1.2),
}
# C and F# only (every 6 semitones): an artifact version holds at most 511 files
INSTRUMENTS.update({k: (f'fluidr3/{gm}/*.mp3', r'^(C|Gb)(\d)$', sec) for k, (gm, sec) in FLUID.items()})


def main():
    kit_path = HERE / 'site' / 'kit.json'
    kit = json.loads(kit_path.read_text())
    total = 0
    for name, (pattern, note_re, keep) in INSTRUMENTS.items():
        out_dir = HERE / 'site' / 'samples' / name
        out_dir.mkdir(parents=True, exist_ok=True)
        notes = {}
        for f in sorted(DL.glob(pattern)):
            m = re.match(note_re, f.stem)
            if not m or f.stat().st_size < 1000:  # failed downloads are empty
                continue
            midi = PC[m[1].lower()] + 12 * (int(m[2]) + 1)
            note = f'{NAMES[midi % 12]}{midi // 12 - 1}'
            try:
                y = decode(f)[:int(keep * SR)].copy()
            except Exception:  # a few of the Wurlitzer's m4a files are cut off (no moov atom)
                print('  skipped', f.name)
                continue
            start = int(np.argmax(np.abs(y) > 0.02 * np.abs(y).max()))  # no silence before the attack
            y = y[max(0, start - int(0.002 * SR)):]
            fade = min(len(y), int(0.3 * SR))
            y[-fade:] *= np.linspace(1, 0, fade)
            # the same loudness for every instrument (RMS of the first half second), not the same peak: peak
            # normalising left them 6x apart (kalimba 0.06, electric piano 0.38) and too loud next to the synths
            body = y[:SR // 2]
            y = y * (0.1 / max(1e-6, float(np.sqrt((body ** 2).mean()))))
            y = (y * min(1.0, 0.95 / max(1e-6, np.abs(y).max()))).astype(np.float32)
            file = f"{note.replace('#', 's').upper()}.mp3"
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-',
                            '-b:a', '96k', str(out_dir / file)], input=y.tobytes(), check=True)
            notes[note] = [f'{name}/{file}']
            total += (out_dir / file).stat().st_size
        keep = {v[0].split('/')[1] for v in notes.values()}
        for old in out_dir.iterdir():  # notes an earlier run wrote and this one no longer uses
            if old.name not in keep:
                old.unlink()
        kit[name] = dict(sorted(notes.items(), key=lambda kv: PC[kv[0][:-1]] + 12 * int(kv[0][-1])))
        print(f'{name}: {len(notes)} notes')
    kit_path.write_text(json.dumps(kit))
    print(f'{total / 1e6:.1f} MB')


if __name__ == '__main__':
    main()
