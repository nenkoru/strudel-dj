"""One-shot percussion and ear candy for the guest parts, added to site/kit.json as plain samples:

- hand percussion from the Versilian Community Sample Library (CC0, https://github.com/sgossner/VCSL):
  bongos, congas, claves, cowbell, agogo, shaker, tambourine, woodblock, claps, triangle, cabasa,
  darbuka; for the drum kits in compose.mjs VOICES.drums (latin, perc, wood)
- ear candy: from VCSL a slapstick, sleigh bells, a flexatone, a guiro, finger cymbals and a cymbal
  crescendo (a riser) and the same cymbal's hit reversed; synthesised here a noise riser, a downlifter,
  a sub impact and a laser zap. Placed by compose.mjs candy() at phrase lines and ends.

Each is downloaded once to data/raw/dl/vcsl/, trimmed to its attack, cut to a length, normalised by
peak and saved as mono mp3 under site/samples/.

    uv run python deckc/perc.py
"""
import json
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np

from build import decode

HERE = Path(__file__).parent
DL = HERE.parent / 'data' / 'raw' / 'dl' / 'vcsl'
SR = 44100
RAW = 'https://raw.githubusercontent.com/sgossner/VCSL/master/'
M, I = 'Membranophones/Struck Membranophones/', 'Idiophones/Struck Idiophones/'
VCSL = {  # name: (path in VCSL, seconds kept, reversed)
    'bongo_hi': (M + 'Bongos/BongoH_Hit1_v2_rr1_Mid.wav', 0.5, False),
    'bongo_lo': (M + 'Bongos/BongoL_Hit1_v2_rr1_Mid.wav', 0.5, False),
    'conga': (M + 'Conga/Conga_HitN_v2_rr1_Sum.wav', 0.6, False),
    'quinto': (M + 'Conga/Quinto_HitN_v2_rr1_Sum.wav', 0.6, False),
    'claves': (I + 'Claves/Claves1_Hit_v2_rr1_Mid.wav', 0.4, False),
    'cowbell': (I + 'Cowbells/Cowbell1_Normal_v2_rr1_Mid.wav', 0.5, False),
    'agogo': (I + 'Agogo Bells/Agogo_High_v2_rr1_Mid.wav', 0.6, False),
    'shaker2': (I + 'Shaker, Small/Mid_ShakerDouble_Down_rr1.wav', 0.3, False),
    'tamb': (I + 'Tambourine 1/Tamb1_Hit_v2_rr1_Mid.wav', 0.5, False),
    'tambshake': (I + 'Tambourine 1/Tamb1_Shake_rr1_Mid.wav', 0.6, False),
    'woodblock': (I + 'Woodblock/wood_click_mp.wav', 0.4, False),
    'clap2': (I + 'Claps/Clap_rr1.wav', 0.5, False),
    'triangle': (I + 'Triangles/Triangle1_HitM_v1_rr2_Mid.wav', 1.0, False),
    'cabasa': (I + 'Cabasa/Cabasa1_Hit_rr1_Mid.wav', 0.4, False),
    'darbuka': (M + 'Darbuka/Darbuka_1_hit_vl2_rr1.wav', 0.5, False),
    'slapstick': (I + 'Slapstick/slapstick_rr2.wav', 0.6, False),
    'sleigh': (I + 'Sleigh Bells/Sleighbells_Hit_rr1_Mid.wav', 1.2, False),
    'flexatone': (I + 'Flexatone/flexatone_slap1.wav', 1.2, False),
    'guiro': (I + 'Guiro/Guiro_Fast_rr1_Mid.wav', 0.8, False),
    'fingercym': (I + 'Finger Cymbals/Fing_Cymb.wav', 2.0, False),
    'cymswell': (I + 'Suspended Cymbal 1/susCymb1_cresc_2s.wav', 2.2, False),
    'revcym': (I + 'Suspended Cymbal 1/susCymb1_hit_f1.wav', 2.0, True),
}


def synth():
    """Ear candy made here: noise riser and downlifter, sub impact, laser zap (1 channel, 44.1 kHz)."""
    rng = np.random.default_rng(7)
    t2 = np.arange(int(2.0 * SR)) / SR
    noise = rng.standard_normal(len(t2))
    # riser: noise through a resonator whose centre rises 300 Hz -> 8 kHz, getting louder
    centre = 300 * (8000 / 300) ** (t2 / t2[-1])
    phase = 2 * np.pi * np.cumsum(centre) / SR
    riser = noise * 0.4 + np.sin(phase) * 0.6
    riser = np.convolve(riser, np.ones(8) / 8, mode='same') * (t2 / t2[-1]) ** 2
    t15 = np.arange(int(1.5 * SR)) / SR
    boom = np.sin(2 * np.pi * np.cumsum(30 + 50 * np.exp(-t15 * 6)) / SR) * np.exp(-t15 * 3)
    boom[:int(0.03 * SR)] += rng.standard_normal(int(0.03 * SR)) * np.linspace(1, 0, int(0.03 * SR))
    tz = np.arange(int(0.25 * SR)) / SR
    zap = np.sin(2 * np.pi * np.cumsum(3000 * np.exp(-tz * 18) + 150) / SR) * np.exp(-tz * 8)
    return {'riser': riser, 'downlifter': riser[::-1].copy(), 'impact': boom, 'zap': zap}


def save(name, y, kit, out):
    y = np.asarray(y, np.float32)
    fade = min(len(y), int(0.05 * SR))
    y[-fade:] *= np.linspace(1, 0, fade)
    y = (y / max(1e-6, np.abs(y).max()) * 0.9).astype(np.float32)
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-', '-b:a', '96k',
                    str(out / f'{name}.mp3')], input=y.tobytes(), check=True)
    kit[name] = [f'perc/{name}.mp3']


def main():
    DL.mkdir(parents=True, exist_ok=True)
    out = HERE / 'site' / 'samples' / 'perc'
    out.mkdir(parents=True, exist_ok=True)
    kit_path = HERE / 'site' / 'kit.json'
    kit = json.loads(kit_path.read_text())
    for name, (path, keep, reverse) in VCSL.items():
        src = DL / f'{name}.wav'
        if not src.exists():
            urllib.request.urlretrieve(RAW + urllib.parse.quote(path), src)
        y = decode(src).copy()
        if reverse:
            y = y[:int(keep * SR)][::-1].copy()
        else:
            start = int(np.argmax(np.abs(y) > 0.05 * np.abs(y).max()))
            y = y[max(0, start - int(0.002 * SR)):][:int(keep * SR)].copy()
        save(name, y, kit, out)
    for name, y in synth().items():
        save(name, y, kit, out)
    kit_path.write_text(json.dumps(kit))
    print(len(VCSL) + 4, 'one-shots,', sum(f.stat().st_size for f in out.iterdir()) // 1000, 'KB')


if __name__ == '__main__':
    main()
