"""Build the Third Deck page's data: site/data.json (tracks, the sets), site/kit.json and the files
they point to under site/samples and site/tracks. The page builds its layer menus itself.

    uv run python deckc/build.py     # after transcribe/track2midi.py on each demo track

Everything published is redistributable: the demo tracks are CC BY / CC BY-SA (credited on the
page); the kit is CC0 (Freesound via Shabda, VCSL) and Unlicense (tidalcycles/uzu-drumkit).
"""
import json
import shutil
import subprocess
import urllib.request
from pathlib import Path

import numpy as np
import soundfile as sf

HERE = Path(__file__).parent
SITE = HERE / 'site'
LIB = HERE.parent / 'samples'
ANALYSIS = HERE / 'tracks' / 'analysis'
VCSL = 'https://strudel.b-cdn.net/VCSL/'

# key: set by hand where the estimate is ambiguous (Krumhansl lands a fifth or a relative key off).
# The house pair is matched on energy as well as tempo and key: the first pair (AFM "Sometimes" +
# Callejas "Páramo 1") had the same key and tempo but Sometimes was far brighter and busier
# (spectral centroid 3090 vs 1402 Hz, 6.7 vs 4.3 onsets/s), and the blend sounded wrong.
TRACKS = [
    {'id': 'tunnel', 'phrase': 2, 'file': 'tunnel.mp4', 'raw': '01_DCM_-_Tunnel.mp3', 'analysis': '01_DCM_-_Tunnel',
     'title': 'Tunnel', 'artist': 'DCM', 'release': 'MNF025 Tunnel EP (Monofonicos)', 'license': 'CC BY-SA 3.0',
     'license_url': 'https://creativecommons.org/licenses/by-sa/3.0/',
     'source': 'https://archive.org/details/MNF025_DCM--Tunnel_EP', 'family': 'house', 'key': 'G minor'},
    # 121 BPM in the original: stretched to 124 without changing pitch, so neither deck is detuned
    # (playbackRate alone would shift it 41 cents against Tunnel).
    {'id': 'motorcity', 'phrase': 2, 'file': 'motor-city-wave.mp4', 'raw': '02_DCM_-_Motor_City_Wave.mp3',
     'analysis': '02_DCM_-_Motor_City_Wave', 'title': 'Motor City Wave', 'artist': 'DCM',
     'release': 'MNF025 Tunnel EP (Monofonicos)', 'license': 'CC BY-SA 3.0',
     'license_url': 'https://creativecommons.org/licenses/by-sa/3.0/',
     'source': 'https://archive.org/details/MNF025_DCM--Tunnel_EP', 'family': 'house', 'key': 'G minor', 'stretch_to': 124.0},
    {'id': 'aerial-mb', 'phrase': 0, 'file': 'aerial-photograph-mb.mp4', 'raw': 'tou220a.mp3', 'analysis': 'tou220a',
     'title': 'Aerial Photograph (Marc Burt mix)', 'artist': 'Marc Burt & Beat Doctor', 'release': 'Aerial Photograph [tou220]',
     'license': 'CC BY-SA 2.5', 'license_url': 'https://creativecommons.org/licenses/by-sa/2.5/',
     'source': 'https://archive.org/details/tou220', 'family': 'progressive', 'key': 'F minor'},
    # Two mixes of the same song: same bass pitch classes (C, F, G#, A#), so the same key.
    {'id': 'aerial-bd', 'phrase': 0, 'file': 'aerial-photograph-bd.mp4', 'raw': 'tou220b.mp3', 'analysis': 'tou220b',
     'title': 'Aerial Photograph (Beat Doctor mix)', 'artist': 'Marc Burt & Beat Doctor', 'release': 'Aerial Photograph [tou220]',
     'license': 'CC BY-SA 2.5', 'license_url': 'https://creativecommons.org/licenses/by-sa/2.5/',
     'source': 'https://archive.org/details/tou220', 'family': 'progressive', 'key': 'F minor'},
    # Both E minor by their bass and lead pitch classes (the full-mix Krumhansl estimate said G).
    {'id': 'sterile-knot', 'phrase': 0, 'file': 'sterile-knot.mp4', 'raw': 'Patrick_Walker-Irradiation_EP-02_Sterile_Knot.mp3',
     'analysis': 'Patrick_Walker-Irradiation_EP-02_Sterile_Knot', 'title': 'Sterile Knot', 'artist': 'Patrick Walker',
     'release': 'Irradiation EP [AVXMP3 001]', 'license': 'CC BY-SA 2.0', 'license_url': 'https://creativecommons.org/licenses/by-sa/2.0/',
     'source': 'https://archive.org/details/avxmp3_001_irradiation_ep', 'family': 'techno', 'key': 'E minor'},
    # 126 → 127 like Motor City. Its kick attacks fall in two clusters 36 ms apart (a layered kick);
    # the grid sits between them (`shift`), so a guest hit is at most ~18 ms off either.
    {'id': 'irradiation', 'phrase': 6, 'file': 'irradiation.mp4', 'raw': 'Patrick_Walker-Irradiation_EP-01_Irradiation.mp3',
     'analysis': 'Patrick_Walker-Irradiation_EP-01_Irradiation', 'title': 'Irradiation', 'artist': 'Patrick Walker',
     'release': 'Irradiation EP [AVXMP3 001]', 'license': 'CC BY-SA 2.0', 'license_url': 'https://creativecommons.org/licenses/by-sa/2.0/',
     'source': 'https://archive.org/details/avxmp3_001_irradiation_ep', 'family': 'techno', 'key': 'E minor',
     'stretch_to': 127.0, 'shift': 0.018},
]
# 'phrase': the track bar (counted from bar0, mod 8) where its 8-bar phrases start. Found from
# bar-to-bar novelty (band energies, and 4 bands x 16 steps) averaged per position mod 8: Tunnel 2
# and the Aerial mixes 0 are clear; Motor City peaks at 1 and 2 (a fill bar, then the phrase), Irradiation
# at 6. Sterile Knot is flat (minimal techno changes slowly): 7 and 0 both peak, so 7 is taken as
# the fill and 0 as the phrase. The page starts and blends tracks on these lines, so the guest decks'
# phrase lines fall where the music turns. Starting Tunnel at bar 84 (≡ 4) put every guest change
# 2 bars before its phrase.
# One set per style: two tracks of matching tempo, key and energy that the page automixes.
SETS = [{'id': 'house', 'label': 'Хаус', 'a': 'tunnel', 'b': 'motorcity', 'family': 'house'},
        {'id': 'progressive', 'label': 'Прогрессив-хаус', 'a': 'aerial-mb', 'b': 'aerial-bd', 'family': 'progressive'},
        {'id': 'techno', 'label': 'Техно', 'a': 'sterile-knot', 'b': 'irradiation', 'family': 'techno'}]
TARGET_DB = -13.0  # every deck is trimmed to this RMS level, like a DJ's gain knob

# Kit sound → (catalog sound, file index). Drums are uzu-drumkit (the produced kit strudel.cc
# loads): the first Freesound clap sounded thin. The riser is CC0 Freesound via Shabda.
KIT = {'house_kick': ('uzu_bd', 0), 'clap': ('uzu_cp', 0), 'house_hat': ('uzu_hh', 0), 'tight_hat': ('uzu_hh', 2),
       'open_hat': ('uzu_oh', 0), 'shaker': ('uzu_sh', 0), 'rim': ('uzu_rim', 0), 'ride': ('uzu_rd', 0),
       'crash': ('uzu_cr', 0), 'tom': ('uzu_lt', 0), 'riser': ('dubstep_riser', 0)}


def fetch(url, dest):
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={'User-Agent': 'deckc build'})
        dest.write_bytes(urllib.request.urlopen(req, timeout=60).read())


def shrink(path, seconds=3):
    """VCSL notes are ~2 MB of 24-bit stereo; mono 22 kHz, 3 s with a fade-out is ~130 KB."""
    if path.stat().st_size < 400_000:
        return
    tmp = path.with_suffix('.tmp.wav')
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', str(path), '-ac', '1', '-ar', '22050', '-sample_fmt', 's16',
                    '-t', str(seconds), '-af', f'afade=t=out:st={seconds - 0.4}:d=0.4', str(tmp)], check=True)
    tmp.replace(path)


def trim_attack(src, dest):
    """Copy a one-shot starting 2 ms before its attack. Several Freesound hits had 13-45 ms of
    silence first, which made them land late against the grid."""
    y, sr = sf.read(src, always_2d=True)
    level = np.abs(y).max(axis=1)
    start = int(np.argmax(level > 0.1 * level.max()))
    sf.write(dest, y[max(0, start - int(0.002 * sr)):], sr)


def energy(path, bpm, bar0, phrase=0, window=32):
    """(trim, from_bar, curve): a gain that brings the track's body to TARGET_DB; the phrase start
    (≡ `phrase` mod 8) of the loudest `window`-bar stretch in its first 60%, so the mix starts and
    blends at full energy, on a phrase line; and the energy of every bar, 0-1 between the track's
    10th and 90th percentile loudness (the page sizes its AI parts by it: sparse in a breakdown)."""
    y, sr = sf.read(path, always_2d=True)
    y = y.mean(axis=1)
    bar = 240 / bpm
    n = int((len(y) / sr - bar0) / bar)
    rms = np.array([np.sqrt(np.mean(y[int((bar0 + i * bar) * sr):int((bar0 + (i + 1) * bar) * sr)] ** 2) + 1e-12) for i in range(n)])
    body = rms[int(n * 0.15):int(n * 0.85)]
    trim = 10 ** ((TARGET_DB - 20 * np.log10(np.mean(body))) / 20)
    last = max(1, int(n * 0.6) - window)
    best = max(range(8 + phrase, last, 8), key=lambda i: rms[i:i + window].mean()) if last > 8 + phrase else phrase
    db = 20 * np.log10(rms)
    lo, hi = np.nanpercentile(db, [10, 90])  # the last bar can be empty (nan)
    curve = [round(float(v), 2) for v in np.nan_to_num(np.clip((db - lo) / max(hi - lo, 1e-6), 0, 1))]
    return round(float(min(trim, 1.2)), 3), int(best), curve  # never boost a quiet track into clipping


def decode(path):
    out = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', str(path), '-f', 'f32le', '-ac', '1', '-ar', '44100', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(out, np.float32)


def stretch_delay(raw, stretched, ratio, at=100.0, span=30.0, hop=64):
    """Seconds by which the time-stretched file lags raw time / ratio. ffmpeg's atempo added a
    constant 10.2 ms on Motor City Wave (same at 100 s and 200 s), enough to blur the grid."""
    def env(y):
        y = y[:len(y) // hop * hop].reshape(-1, hop)
        return np.sqrt((y ** 2).mean(1))
    er, es = env(decode(raw)), env(decode(stretched))
    a = er[int(at * 44100 / hop):int((at + span) * 44100 / hop)]
    n = int(len(a) / ratio)
    a = np.interp(np.arange(n) * ratio, np.arange(len(a)), a)
    s0, lag = int(at / ratio * 44100 / hop), int(0.08 * 44100 / hop)
    seg = es[s0 - lag:s0 + n + lag]
    corr = [np.corrcoef(a, seg[k:k + n])[0, 1] for k in range(2 * lag)]
    return (int(np.argmax(corr)) - lag) * hop / 44100


def main():
    if SITE.joinpath('samples').exists():
        shutil.rmtree(SITE / 'samples')  # rebuilt from scratch: no stale one-shots get published
    (SITE / 'samples').mkdir(parents=True)
    (SITE / 'tracks').mkdir(exist_ok=True)
    kit = {}
    catalog = {}
    for e in json.loads((LIB / 'catalog.json').read_text()):
        catalog.setdefault(e['sound'], []).append(e)
    for name, (sound, i) in KIT.items():
        trim_attack(LIB / catalog[sound][i]['path'], SITE / 'samples' / f'{name}.wav')
        kit[name] = [f'{name}.wav']
    vcsl = json.loads(urllib.request.urlopen('https://strudel.b-cdn.net/vcsl.json', timeout=60).read())
    kit['sax'] = {}
    for key, files in vcsl['sax_vib'].items():
        path = files if isinstance(files, str) else files[0]  # values are strings here, lists elsewhere
        if any(key.endswith(o) for o in ('2', '3', '4', '5')):
            dest = SITE / 'samples' / 'sax' / f'{key.replace("#", "s")}.wav'
            for base in (VCSL, vcsl['_base']):  # paths are already URL-encoded; a few files exist on neither
                try:
                    fetch(base + path, dest); break
                except Exception:
                    pass
            if dest.exists():
                shrink(dest)
                kit['sax'][key.lower()] = [f'sax/{dest.name}']

    tracks, library = [], []
    for t in TRACKS:
        info = json.loads((ANALYSIS / f"{t['analysis']}.json").read_text())
        out = SITE / 'tracks' / t['file']
        info['bar0'] += t.get('shift', 0.0)
        ratio = t['stretch_to'] / info['tempo'] if t.get('stretch_to') else 1.0
        if not out.exists():
            stretch = ['-filter:a', f'atempo={ratio:.6f}'] if ratio != 1.0 else []
            # AAC in MP4 (.mp4: .m4a is not a served type): its encoder priming is stored in the edit list, which Chrome and Safari trim,
            # so the decode starts on the analysed timeline (checked in Chrome: 0.0 ms against the
            # raw decode; MP3 padding handling differs between decoders).
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', str(HERE / 'tracks' / 'raw' / t['raw']), '-vn', *stretch,
                            '-ac', '2', '-ar', '44100', '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', str(out)], check=True)
        trim, from_bar, curve = energy(HERE / 'tracks' / 'raw' / t['raw'], info['tempo'], info['bar0'], t.get('phrase', 0))
        delay = stretch_delay(HERE / 'tracks' / 'raw' / t['raw'], out, ratio) if ratio != 1.0 else 0.0
        # Mixxx mode plays the raw files: their own timeline, matched to Mixxx's decks by duration.
        library.append({'id': t['id'], 'title': t['title'], 'artist': t['artist'], 'family': t['family'], 'key': t.get('key') or info['key'],
                        'duration': round(sf.info(str(HERE / 'tracks' / 'raw' / t['raw'])).duration, 3),
                        'bpm': info['tempo'], 'bar0': round(info['bar0'], 4), 'phrase': t.get('phrase', 0), 'energy': curve})
        t = {k: v for k, v in t.items() if k not in ('analysis', 'raw', 'stretch_to', 'shift', 'phrase')}
        # Times are in the analysed (raw) file's timeline, divided by the stretch.
        t.update(bpm=round(info['tempo'] * ratio, 3), bar0=round(info['bar0'] / ratio + delay, 4), key=t.get('key') or info['key'],
                 trim=trim, from_bar=from_bar, energy=curve)
        tracks.append(t)
    (SITE / 'kit.json').write_text(json.dumps(kit, indent=1))
    (SITE / 'data.json').write_text(json.dumps({'tracks': tracks, 'sets': SETS, 'library': library, 'sounds': sorted(kit)}, indent=1))
    for t in tracks:
        print(t['id'], t['bpm'], t['key'], t['bar0'], 'trim', t['trim'], 'from bar', t['from_bar'])
    print('kit sounds:', len(kit))


if __name__ == '__main__':
    main()
