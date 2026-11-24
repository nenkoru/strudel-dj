"""Freesound loops (tiny/freesound.py) -> MIDI, for the genre data: short dance loops are the material the
loop cleaning (prep_midi.py clean_transcribed) suits best, and Jamendo had little clean house or techno.

Melodic loops only (a bass, synth, lead, chord, pad or arp tag and no drum tag), CC0, CC BY or CC BY-NC
(not Sampling+), with a tempo from the metadata (Freesound's analysis or the uploader's) and a length
that is a whole number of bars at it (within 4%), so bar one starts at the file's start. No stem
separation: a loop is mostly one instrument. basic-pitch transcribes it (bass loops kept monophonic,
as audio2midi.py), the onsets are moved by the constant offset that puts most on the 16th grid
(audio2midi.calibrate), and the loop is repeated to 8 bars. One MIDI file per loop: bass on program 38,
the rest on 81 (the programs prep_midi.py's cleaning reads), the tempo set; meta.jsonl in the same
format as Jamendo's (style from the tags), so `prep_midi.py jamendo data/raw/dl/freesound/midi loops`
converts them. Resumes: loops already in meta.jsonl are skipped.

    $BP_PYTHON tiny/loops2midi.py
"""
import ast
import json
import math
from pathlib import Path

import pretty_midi

from audio2midi import calibrate, notes_of

SRC = Path(__file__).parent.parent / 'data' / 'raw' / 'dl' / 'freesound'
OUT = SRC / 'midi'
MELODIC = {'bass', 'bassline', 'synth', 'lead', 'chord', 'chords', 'pad', 'arp', 'arpeggio', 'acid', 'melody', 'stab', 'pluck'}
DRUMS = {'drums', 'drum', 'beat', 'percussion', 'drumloop', 'kick', 'hihat', 'snare', 'breakbeat', 'beats'}
STYLE = [('techno', 'techno'), ('minimal', 'techno'), ('acid', 'techno'), ('house', 'house'), ('deep-house', 'house'),
         ('tech-house', 'house'), ('trance', 'prog'), ('progressive', 'prog')]


def tags_of(row):
    t = row.get('tags') or []
    return {x.lower() for x in (ast.literal_eval(t) if isinstance(t, str) else t)}


def main():
    OUT.mkdir(exist_ok=True)
    meta_path = OUT / 'meta.jsonl'
    done = {json.loads(l)['path'] for l in open(meta_path)} if meta_path.exists() else set()
    rows = [json.loads(l) for l in open(SRC / 'meta.jsonl')]
    kept = 0
    for row in rows:
        tags, lic = tags_of(row), row.get('license') or ''
        if row['file'] in done or not (tags & MELODIC) or tags & DRUMS or 'sampling' in lic:
            continue
        try:
            bpm, dur = float(row.get('bpm') or 0), float(row['duration'])
        except (TypeError, ValueError):
            continue
        while 0 < bpm < 90:
            bpm *= 2
        while bpm > 180:
            bpm /= 2
        bar = 240 / bpm if bpm else 0
        bars = dur / bar if bar else 0
        n = round(bars)
        if not bpm or n < 1 or n > 16 or abs(bars - n) > 0.04 * n:
            continue
        bass = bool(tags & {'bass', 'bassline'})
        try:
            notes = notes_of(SRC / row['file'], 24 if bass else 36, 60 if bass else 96, mono=bass)
        except Exception as e:
            print(row['file'], 'failed:', e, flush=True)
            continue
        notes, fit = calibrate(notes, bpm, 0.0)
        if len(notes) < 4 or fit < 0.6:
            continue
        loop = n * bar
        notes = [(s, min(e, loop), p, v) for s, e, p, v in notes if s < loop - 0.01]
        pm = pretty_midi.PrettyMIDI(initial_tempo=bpm)
        inst = pretty_midi.Instrument(program=38 if bass else 81)
        for k in range(math.ceil(8 / n)):  # the loop over 8 bars
            for s, e, p, v in notes:
                inst.notes.append(pretty_midi.Note(velocity=max(1, min(127, v)), pitch=p, start=s + k * loop, end=max(s + 0.03, e) + k * loop))
        pm.instruments.append(inst)
        pm.time_signature_changes.append(pretty_midi.TimeSignature(4, 4, 0))
        name = row['file'].replace('.mp3', '.mid')
        pm.write(str(OUT / name))
        style = next((s for t, s in STYLE if t in tags), 'edm')
        with open(meta_path, 'a') as f:
            f.write(json.dumps({'path': row['file'], 'midi': name, 'bpm': round(bpm, 3), 'style': style, 'bars': n,
                                'part': 'bass' if bass else 'other', 'notes': len(notes), 'on_grid': round(fit, 2),
                                'license': lic, 'author': row.get('author')}) + '\n')
        kept += 1
        if kept % 100 == 0:
            print(kept, 'loops', flush=True)
    print('done', kept)


if __name__ == '__main__':
    main()
