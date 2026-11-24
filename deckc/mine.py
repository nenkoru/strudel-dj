"""The owner's own rekordbox tracks for the rating page: deckc/mine/mine.json and mine/tracks/*.mp4.

Private: they go only to the rating artifact (visible to its owner), never to site/ or the public demo.
rekordbox has already analysed them, and better than we would: the beat grid with downbeats (PQTZ in
the .DAT), the key, and the phrases with their kind (PSSI in the .EXT: intro / up / down / chorus /
outro, or verse / bridge for mid and low moods). We add the per-bar energy curve (build.energy).

    uv run --with pyrekordbox python deckc/mine.py [--min-plays 1]
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pyrekordbox import AnlzFile, MasterDatabase

sys.path.insert(0, str(Path(__file__).parent))
from build import energy  # noqa: E402

HERE = Path(__file__).parent
OUT = HERE / 'mine'
RB = Path.home() / 'Library/Pioneer/rekordbox'
CAMELOT_MINOR = {1: 'G# minor', 2: 'D# minor', 3: 'A# minor', 4: 'F minor', 5: 'C minor', 6: 'G minor',
                 7: 'D minor', 8: 'A minor', 9: 'E minor', 10: 'B minor', 11: 'F# minor', 12: 'C# minor'}
CAMELOT_MAJOR = {1: 'B major', 2: 'F# major', 3: 'C# major', 4: 'G# major', 5: 'D# major', 6: 'A# major',
                 7: 'F major', 8: 'C major', 9: 'G major', 10: 'D major', 11: 'A major', 12: 'E major'}
# phrase kinds by mood (rekordbox 6 PSSI; mood 1 high, 2 mid, 3 low)
KINDS = {1: {1: 'интро', 2: 'подъём', 3: 'спад', 5: 'припев', 6: 'аутро'},
         2: {1: 'интро', **{k: 'куплет' for k in range(2, 8)}, 8: 'бридж', 9: 'припев', 10: 'аутро'},
         3: {1: 'интро', **{k: 'куплет' for k in range(2, 8)}, 8: 'бридж', 9: 'припев', 10: 'аутро'}}
# a guess from the artists (rekordbox has no genre on these): melodic techno, else progressive house.
# The artist lists are private (they describe the owner's library): mine/artist_styles.json,
# {"techno": [...], "house": [...]}; without it every track is progressive.
_STYLES = json.loads((OUT / 'artist_styles.json').read_text()) if (OUT / 'artist_styles.json').exists() else {}
TECHNO = tuple(_STYLES.get('techno', ()))
HOUSE = tuple(_STYLES.get('house', ()))


def key_name(scale):
    n, mode = int(scale[:-1]), scale[-1]
    return (CAMELOT_MINOR if mode == 'A' else CAMELOT_MAJOR)[n]


def slug(s):
    return ''.join(ch if ch.isalnum() else '-' for ch in s.lower()).strip('-')[:40]


def analyse(c):
    anlz = RB / 'share' / c.AnalysisDataPath.lstrip('/')
    grid = AnlzFile.parse_file(anlz).get_tag('PQTZ').content.entries
    if len({b.tempo for b in grid}) > 1:
        return None  # a tempo change: the page plays one constant grid per track
    first = next(i for i, b in enumerate(grid) if b.beat == 1)
    bpm, bar0 = grid[0].tempo / 100, grid[first].time / 1000
    pssi = AnlzFile.parse_file(anlz.with_suffix('.EXT')).get_tag('PSSI').content
    kinds = KINDS.get(pssi.mood, KINDS[1])
    phrases = [{'bar': (e.beat - 1 - first) // 4, 'kind': kinds.get(e.kind, '')} for e in pssi.entries
               if (e.beat - 1 - first) % 4 == 0 and e.beat - 1 >= first]
    artist = c.Artist.Name if c.Artist else ''
    family = 'techno' if any(a in f'{artist} {c.Title}' for a in TECHNO) else 'house' if any(a in artist for a in HOUSE) else 'progressive'
    return {'id': slug(c.Title), 'title': c.Title, 'artist': artist, 'family': family, 'key': key_name(c.Key.ScaleName),
            'bpm': bpm, 'bar0': round(bar0, 4), 'plays': int(c.DJPlayCount or 0), 'phrases': phrases, 'src': c.FolderPath}


def build(t):
    out = OUT / 'tracks' / (t['id'] + '.mp4')
    if not out.exists():
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', t['src'], '-vn', '-c:a', 'aac', '-b:a', '80k',
                        '-movflags', '+faststart', str(out)], check=True)
    with tempfile.TemporaryDirectory() as tmp:  # energy reads the lossless source, decoded once
        wav = Path(tmp) / 'a.wav'
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', t['src'], '-ac', '1', str(wav)], check=True)
        trim, _, curve = energy(wav, t['bpm'], t['bar0'])
    del t['src']
    return {**t, 'file': out.name, 'trim': trim, 'energy': curve}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--min-plays', type=int, default=1)
    args = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:  # read a copy: rekordbox may have the database open
        shutil.copy(RB / 'master.db', Path(tmp) / 'master.db')
        db = MasterDatabase(path=str(Path(tmp) / 'master.db'))
        found = [analyse(c) for c in db.get_content() if int(c.DJPlayCount or 0) >= args.min_plays and c.Key]
    tracks = [t for t in found if t]
    (OUT / 'tracks').mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(6) as pool:
        tracks = list(pool.map(build, tracks))
    tracks.sort(key=lambda t: -t['plays'])
    (OUT / 'mine.json').write_text(json.dumps({'tracks': tracks}, ensure_ascii=False))
    for t in tracks:
        print(f"{t['plays']} {t['family'][:5]:5} {t['key']:9} {t['bpm']:6} bar0 {t['bar0']:6} phrases {len(t['phrases']):2} "
              f"first {t['phrases'][0]['bar'] if t['phrases'] else '-':3} {t['title'][:40]}")
    print(len(tracks), 'tracks', sum((OUT / 'tracks' / t['file']).stat().st_size for t in tracks) // 1000000, 'MB;',
          len(found) - len(tracks), 'skipped (tempo changes)')


if __name__ == '__main__':
    main()
