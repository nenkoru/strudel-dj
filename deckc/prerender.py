"""A swipe batch rendered on the Mac, so the phone only plays audio (the owner: the page took long to
start and reloaded on an iPhone, which had to decode whole 6-minute tracks and synthesize every part).

For each card (a moment of a track with its twin parts a and b) one AAC file, deckc/mine/moments/<pairId>.mp4:

    [0.25 s silence, a one-sample click, 0.25 s] [the track's stretch] [0.5 s] [part a] [0.5 s] [part b]

- the track's stretch: 8 bars before the moment, the part's bars, 8 after (as far as the track goes), at
  the track's `trim`, cut from deckc/mine/tracks with ffmpeg;
- each part: its first PHRASES phrases (the code, then its developed phrases `dev`), 8 bars each rendered
  by js/render.mjs with the page's kit and overlapped with their tails, then given what the page's mixer
  did live: the part's `norm` (deckc/loudness.py), the entry over its first bar (not on a drop), for
  percussion the level that eases in and rides the track's energy, and where the track has a kick the
  pump (the page ducked the guest orbit on every beat; superdough's ducking does not run offline).

The click lets the page find where the decoded audio starts (AAC decoders differ in how much of the
encoder's priming they drop). The item gets `audio`: the file, each segment's start and length in seconds
after the click, the bar length, how many bars of the stretch come before the part, and how many phrases.
Items whose track or parts fail are left as they are (the page plays those live).

    uv run --with soundfile --with numpy python deckc/prerender.py [deckc/mine/batch.json] [max items]
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

HERE = Path(__file__).parent
SR = 44100
PHRASES = 2
PUMP = {'bass': 0.6, 'chords': 0.4, 'lead': 0.25, 'solo': 0.2}  # as compose.mjs PUMP
DRUMLIKE = {'drums', 'fill'}
BITRATE = '64k'


def excerpt(track, start, seconds):
    out = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', str(HERE / 'mine' / 'tracks' / track['file']), '-ss', f'{max(0, start):.4f}',
                          '-t', f'{seconds:.4f}', '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True, check=True).stdout
    y = np.frombuffer(out, np.float32).reshape(-1, 2).copy()
    want = int(round(seconds * SR))
    if start < 0:  # the grid starts a little before the file
        y = np.concatenate([np.zeros((int(round(-start * SR)), 2), np.float32), y])
    y = y[:want]
    return np.pad(y, ((0, want - len(y)), (0, 0))) * float(track.get('trim') or 1)


def envelope(item, n, bar, energy):
    """The page's live level for the part, per sample: entry ramp, percussion level, pump."""
    t = np.arange(n) / SR
    b = t / bar  # bars since the part came in
    g = np.ones(n, np.float32)
    if item.get('section') != 'drop':
        g *= np.minimum(1, 0.3 + 0.7 * b)
    if item['role'] in DRUMLIKE:
        idx = np.minimum(item['fromBar'] + b.astype(int), len(energy) - 1)
        g *= np.minimum(1, 0.35 + 0.325 * b) * (0.35 + 0.65 * np.asarray(energy)[idx])
    depth = PUMP.get(item.get('base') or item['role'])
    if depth and 'kick' in (item.get('hear') or ''):
        low, attack = 1 - np.sqrt(depth), 0.16  # superdough: down at once, an exponential ramp back over `attack`
        since = (t % (bar / 4))
        g *= np.where(since < attack, low * (1 / low) ** (since / attack), 1).astype(np.float32)
    return g


def main(path=HERE / 'mine' / 'batch.json', limit=None):
    doc = json.loads(Path(path).read_text())
    tracks = {t['id']: t for t in json.loads((HERE / 'mine' / 'mine.json').read_text())['tracks']}
    items = doc['items'][:int(limit)] if limit else doc['items']
    tmp = Path(tempfile.mkdtemp(prefix='pre-'))
    kit = tmp / 'kit'
    kit.mkdir()
    (kit / 'strudel.json').write_text((HERE / 'site' / 'kit.json').read_text())
    for d in (HERE / 'site' / 'samples').iterdir():
        (kit / d.name).symlink_to(d.resolve())
    rows = []
    for it in items:
        for w in 'ab':
            codes = [it[w]['code'], *(d['code'] for d in it[w].get('dev') or [])][:PHRASES]
            for k, code in enumerate(codes):
                rows.append({'id': f"{it['pairId']}{w}{k}", 'code': code, 'tempo': tracks[it['track']]['bpm']})
    (tmp / 'parts.jsonl').write_text('\n'.join(json.dumps(r) for r in rows))
    print(f'rendering {len(rows)} phrases of {len(items)} cards', flush=True)
    subprocess.run(['node', 'render.mjs', str(tmp / 'parts.jsonl'), str(tmp / 'wav'), '--bars', '8', '--samples', str(kit),
                    '--jobs', '6', '--keep-level'], cwd=HERE.parent / 'js', check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    out_dir = HERE / 'mine' / 'moments'
    out_dir.mkdir(exist_ok=True)
    done = 0
    for it in items:
        tr = tracks[it['track']]
        bar = 240 / tr['bpm']
        phrases = min(PHRASES, 1 + len(it['a'].get('dev') or []), 1 + len(it['b'].get('dev') or []),
                      max(1, (len(tr['energy']) - it['fromBar']) // 8))
        part_bars = 8 * phrases
        lead = min(8, it['fromBar'])
        tail = max(0, min(8, len(tr['energy']) - it['fromBar'] - part_bars))
        stems = {}
        try:
            for w in 'ab':
                n = int(round((part_bars * bar + 1.5) * SR))
                y = np.zeros((n, 2), np.float32)
                for k in range(phrases):
                    f = tmp / 'wav' / f"{it['pairId']}{w}{k}.wav"
                    z, _ = sf.read(f, dtype='float32')
                    at = int(round(k * 8 * bar * SR))
                    m = min(len(z), n - at)
                    y[at:at + m] += z[:m]
                y *= (it[w].get('norm') or 1) * envelope(it, n, bar, tr['energy'])[:, None]
                peak = np.abs(y).max()
                stems[w] = y * (0.98 / peak if peak > 0.98 else 1)
            stretch = excerpt(tr, tr['bar0'] + (it['fromBar'] - lead) * bar, (lead + part_bars + tail) * bar)
        except Exception as e:
            print('skip', it['pairId'], e)
            continue
        gap = np.zeros((int(0.5 * SR), 2), np.float32)
        head = np.zeros((int(0.5 * SR), 2), np.float32)
        head[int(0.25 * SR)] = 0.9  # the click
        segs, starts, t = [stretch, stems["a"], stems["b"]], [], 0.5
        body = [head]
        for s in segs:
            starts.append(t)
            body += [s, gap]
            t += len(s) / SR + 0.5
        wav = tmp / 'm.wav'
        sf.write(wav, np.concatenate(body), SR, subtype='PCM_16')
        name = f"moments/{it['pairId']}.mp4"
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', str(wav), '-c:a', 'aac', '-b:a', BITRATE, '-movflags', '+faststart',
                        str(HERE / 'mine' / name)], check=True)
        it['audio'] = {'file': f'mine/{name}', 'stretch': [round(starts[0] - 0.25, 4), round(len(stretch) / SR, 4)],
                       'a': [round(starts[1] - 0.25, 4), round(len(stems['a']) / SR, 4)], 'b': [round(starts[2] - 0.25, 4), round(len(stems['b']) / SR, 4)],
                       'bar': bar, 'lead': lead, 'phrases': phrases, 'tail': tail}
        done += 1
    Path(path).write_text(json.dumps(doc))
    size = sum(f.stat().st_size for f in out_dir.glob('*.mp4'))
    print(f'{done} cards rendered, {size / 1e6:.0f} MB in {out_dir}')


if __name__ == '__main__':
    main(*sys.argv[1:3])
