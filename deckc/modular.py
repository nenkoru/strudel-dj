"""Analog synths for the guest parts, from Modular Samples on Freesound (CC0: freesound.org/people/
modularsamples, 465 packs of single notes of Junos, JX-3P/8P, Jupiter-4, SH-2, Xpander, Minitaur...).
The owner found the sounds "too simple"; these are real polysynth and monosynth patches.

For each chosen pack: its notes listed through the Freesound API (the owner's key in ~/.freesound_key,
sent as a header), C and F# kept in the instrument's range (an artifact version holds 511 files),
the high-quality mp3 preview downloaded once to data/raw/dl/modular/, cut to its attack, faded, RMS-
levelled like deckc/instruments.py, saved to site/samples/<name>/ and mapped in site/kit.json.
Instruments that made room for these (DROP) leave kit.json and their folders.

    python3 deckc/modular.py
"""
import json
import re
import shutil
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
DL = HERE.parent / 'data' / 'raw' / 'dl' / 'modular'
SR = 44100
NAMES = ['c', 'c#', 'd', 'd#', 'e', 'f', 'f#', 'g', 'g#', 'a', 'a#', 'b']
PC = {'c': 0, 'c#': 1, 'd': 2, 'd#': 3, 'e': 4, 'e#': 5, 'f': 5, 'f#': 6, 'g': 7, 'g#': 8, 'a': 9, 'a#': 10, 'b': 11, 'b#': 12}

# name: (pack id, lowest midi kept, highest, seconds kept)
PACKS = {
    'junobass': (17476, 24, 54, 1.5),    # Roland Juno 6 - Pulse Bass
    'sh2bass': (17608, 24, 54, 1.5),     # Roland SH-2 - Two Finger Bass
    'snapbass': (17564, 24, 54, 1.2),    # Roland JX-3P - SnapBass
    'moogbass': (17451, 24, 54, 1.5),    # Moog Minitaur - Slight Detune
    'ravestab': (17557, 42, 78, 1.0),    # Roland JX-3P - Rave Stabbing
    'bigstack': (17452, 42, 78, 1.5),    # Oberheim Xpander - Big Stack
    'junopad': (17475, 42, 78, 3.0),     # Roland Juno 6 - Open Pad
    'darkpad': (17573, 42, 78, 3.0),     # Roland JX-8P - Dark Pad Chorus
    'unipad': (17534, 42, 78, 3.0),      # Roland Jupiter 4 - Unison Pad
    'junopluck': (17478, 48, 84, 1.2),   # Roland Juno 6 - Rich pluck
    'buzzlead': (17572, 48, 84, 2.0),    # Roland JX-8P - Buzzy Lead
    'brassy': (17540, 42, 78, 2.0),      # Roland JX-3P - Brassy
}
DROP = ['calliope', 'fifths', 'newage', 'sweep', 'panflute', 'steeldrum', 'choir', 'orchhit']


def api(key, url):
    req = urllib.request.Request(url, headers={'Authorization': f'Token {key}'})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception:
            time.sleep(10 * (attempt + 1))
    raise IOError(url)


def decode(path):
    out = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', str(path), '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(out, np.float32).copy()


def main():
    key = (Path.home() / '.freesound_key').read_text().strip()
    kit_path = HERE / 'site' / 'kit.json'
    kit = json.loads(kit_path.read_text())
    for name in DROP:
        kit.pop(name, None)
        shutil.rmtree(HERE / 'site' / 'samples' / name, ignore_errors=True)
    total = 0
    for name, (pack, lo, hi, keep) in PACKS.items():
        src, out = DL / name, HERE / 'site' / 'samples' / name
        src.mkdir(parents=True, exist_ok=True); out.mkdir(parents=True, exist_ok=True)
        url = f'https://freesound.org/apiv2/packs/{pack}/sounds/?' + urllib.parse.urlencode({'page_size': 150, 'fields': 'id,name,license,previews'})
        sounds = []
        while url:
            d = api(key, url); sounds += d['results']; url = d.get('next'); time.sleep(1.1)
        notes = {}
        for s in sounds:
            m = re.search(r' - ([A-G](?:#)?)(-?\d) \(', s['name'])
            if not m or 'zero' not in s['license']:
                continue
            midi = PC[m[1].lower()] + 12 * (int(m[2]) + 1)
            if not (lo <= midi <= hi) or midi % 6:  # C and F# only
                continue
            note = f'{NAMES[midi % 12]}{midi // 12 - 1}'
            if note in notes:
                continue
            raw = src / f'{s["id"]}.mp3'
            if not raw.exists():
                urllib.request.urlretrieve(s['previews']['preview-hq-mp3'], raw)
            y = decode(raw)[:int(keep * SR)]
            start = int(np.argmax(np.abs(y) > 0.02 * np.abs(y).max()))
            y = y[max(0, start - int(0.002 * SR)):]
            fade = min(len(y), int(0.3 * SR))
            y[-fade:] *= np.linspace(1, 0, fade)
            body = y[:SR // 2]
            y = y * (0.1 / max(1e-6, float(np.sqrt((body ** 2).mean()))))
            y = (y * min(1.0, 0.95 / max(1e-6, np.abs(y).max()))).astype(np.float32)
            file = f"{note.replace('#', 's').upper()}.mp3"
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-',
                            '-b:a', '96k', str(out / file)], input=y.tobytes(), check=True)
            notes[note] = [f'{name}/{file}']
            total += (out / file).stat().st_size
        for old in out.iterdir():
            if old.name not in {v[0].split('/')[1] for v in notes.values()}:
                old.unlink()
        kit[name] = dict(sorted(notes.items(), key=lambda kv: PC[kv[0][:-1]] + 12 * int(kv[0][-1])))
        print(f'{name}: {len(notes)} notes', flush=True)
    kit_path.write_text(json.dumps(kit))
    print(f'{total / 1e6:.1f} MB')


if __name__ == '__main__':
    main()
