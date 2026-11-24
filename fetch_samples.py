"""Build a local, style-tagged Strudel sample library: samples/<pack>/<sound>/NN.wav.

    uv run python fetch_samples.py              # all sources
    uv run python fetch_samples.py --only shabda

Sources
- strudel.cc drum machines (tidal-drum-machines; vintage machine samples, no stated license),
  a selection matched to styles.
- uzu-drumkit (the kit strudel.cc loads by default).
- Shabda (shabda.ndre.gr) semantic queries against Freesound, restricted to CC0, one sound per
  style x role ("dubstep_snare", "deep_house_chord_stab", ...).

Writes samples/catalog.json (one entry per file: sound, pack, role, styles, path, source, license)
and samples/strudel.json (sound → files, loadable with samples() / render.mjs --library).
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).parent / 'samples'
CDN = 'https://strudel.b-cdn.net'
ROLES = {'bd': 'kick', 'sd': 'snare', 'cp': 'clap', 'rim': 'rim', 'hh': 'hat', 'oh': 'openhat', 'cr': 'cymbal',
         'rd': 'cymbal', 'ht': 'tom', 'mt': 'tom', 'lt': 'tom', 'perc': 'perc', 'cb': 'perc', 'tb': 'perc',
         'sh': 'perc', 'brk': 'break', 'fx': 'fx', 'misc': 'fx'}
MACHINES = {  # machine → styles it is typical of
    'RolandTR909': ['deep house', 'house', 'techno', 'garage'], 'RolandTR808': ['deep house', 'house', 'trap', 'hip hop', 'dubstep'],
    'RolandTR707': ['house', 'garage'], 'LinnDrum': ['house', 'hip hop'], 'OberheimDMX': ['hip hop', 'house'],
    'AkaiMPC60': ['hip hop', 'garage'], 'EmuSP12': ['hip hop', 'drum and bass'], 'MPC1000': ['hip hop', 'dubstep'],
    'RolandMC303': ['techno', 'drum and bass'], 'KorgM1': ['house', 'garage'],
}
STYLE_ROLES = {
    'deep house': ['kick', 'clap', 'hihat', 'open hihat', 'shaker', 'rimshot', 'chord stab', 'organ bass', 'pad', 'vocal chop'],
    'dubstep': ['kick', 'snare', 'hihat', 'sub bass', 'wobble bass', 'reese bass', 'riser', 'impact', 'vocal chop', 'flute'],
    'garage': ['kick', 'snare', 'hihat', 'bass', 'chord stab', 'vocal chop'],
    'drum and bass': ['kick', 'snare', 'hihat', 'reese bass', 'pad', 'break'],
    'techno': ['kick', 'clap', 'hihat', 'rumble', 'stab', 'percussion'],
    'trap': ['kick', '808', 'snare', 'hihat', 'vocal chop'],
    'hip hop': ['kick', 'snare', 'hihat', 'vinyl', 'keys'],
    'ambient': ['pad', 'drone', 'texture', 'bell'],
    # The first kits had a single melodic source (dubstep_flute) for every style.
    'deep dubstep': ['melodica', 'saxophone', 'dub chord', 'dub siren', 'sub bass'],
    'roots dubstep': ['skank chord', 'reggae organ'],
    'progressive house': ['kick', 'clap', 'hihat', 'supersaw lead', 'pluck', 'pad', 'bass'],
}
SHABDA_ROLE = {'hihat': 'hat', 'open hihat': 'openhat', 'rimshot': 'rim', 'shaker': 'perc', 'percussion': 'perc',
               'organ bass': 'bass', 'sub bass': 'bass', 'wobble bass': 'bass', 'reese bass': 'bass', '808': 'bass',
               'rumble': 'bass', 'chord stab': 'stab', 'stab': 'stab', 'keys': 'stab', 'vocal chop': 'vocal',
               'riser': 'fx', 'impact': 'fx', 'vinyl': 'fx', 'texture': 'fx', 'drone': 'pad', 'bell': 'lead', 'flute': 'lead',
               'melodica': 'lead', 'saxophone': 'lead', 'supersaw lead': 'lead', 'pluck': 'lead', 'dub chord': 'stab',
               'skank chord': 'stab', 'reggae organ': 'stab', 'dub siren': 'fx'}


def get(url, timeout=120):
    req = urllib.request.Request(url, headers={'User-Agent': 'strudel-lm sample fetcher'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def download(jobs):
    """jobs: [(url, dest)] → number fetched (existing files are kept)."""
    def one(job):
        url, dest = job
        if dest.exists():
            return 0
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            dest.write_bytes(get(url)); return 1
        except Exception as e:
            print('  failed', url, e, file=sys.stderr); return 0
    with ThreadPoolExecutor(8) as pool:
        return sum(pool.map(one, jobs))


def drum_machines(catalog):
    index = json.loads(get(f'{CDN}/tidal-drum-machines.json'))
    jobs = []
    for key, files in index.items():
        machine, _, inst = key.rpartition('_')
        if machine not in MACHINES or inst not in ROLES:
            continue
        for i, f in enumerate(files):
            dest = ROOT / 'drum-machines' / key / f'{i:02d}{Path(f).suffix}'
            jobs.append((f'{CDN}/tidal-drum-machines/machines/{f}', dest))
            catalog.append({'sound': key, 'pack': 'drum-machines', 'role': ROLES[inst], 'styles': MACHINES[machine],
                            'path': str(dest.relative_to(ROOT)), 'source': f'tidal-drum-machines/{f}',
                            'license': 'unstated (vintage drum machine samples)'})
    print('drum machines:', download(jobs), 'new of', len(jobs))


def uzu(catalog):
    index = json.loads(get(f'{CDN}/uzu-drumkit.json'))
    base = index.pop('_base')
    jobs = []
    for inst, files in index.items():
        for i, f in enumerate(files):
            dest = ROOT / 'uzu-drumkit' / f'uzu_{inst}' / f'{i:02d}{Path(f).suffix}'
            jobs.append((base + f, dest))
            catalog.append({'sound': f'uzu_{inst}', 'pack': 'uzu-drumkit', 'role': ROLES.get(inst, 'fx'), 'styles': [],
                            'path': str(dest.relative_to(ROOT)), 'source': base + f, 'license': 'see tidalcycles/uzu-drumkit'})
    print('uzu-drumkit:', download(jobs), 'new of', len(jobs))


def shabda(catalog, per=4):
    def query(word):
        url = f'https://shabda.ndre.gr/{urllib.parse.quote(word)}:{per}.json?strudel=1&licenses=cc0'
        for attempt in range(3):  # bursts get HTTP 500 too, so retry before giving up on a word
            try:
                return json.loads(get(url, timeout=180))
            except Exception:
                time.sleep(3 * (attempt + 1))
        return None

    jobs, entries = [], {}
    for style, roles in STYLE_ROLES.items():
        for role in roles:
            # "deep_dubstep_saxophone" has no CC0 match on Freesound (also HTTP 500), "saxophone" does;
            # fall back to the role alone and tag it with the style.
            for word in (f'{style} {role}'.replace(' ', '_'), role.replace(' ', '_')):
                index = entries.get(word) or query(word)
                if index:
                    break
            if not index:
                print('  shabda failed', style, role, file=sys.stderr); continue
            entries[word] = index
            base = index['_base']
            for i, f in enumerate(index.get(word, [])):
                dest = ROOT / 'shabda' / word / f'{i:02d}.wav'
                old = next((e for e in catalog if e['path'] == str(dest.relative_to(ROOT))), None)
                if old:  # one file shared by several styles
                    old['styles'] = sorted(set(old['styles']) | {style}); continue
                jobs.append((base + f, dest))
                catalog.append({'sound': word, 'pack': 'shabda', 'role': SHABDA_ROLE.get(role, role), 'styles': [style],
                                'path': str(dest.relative_to(ROOT)), 'source': f'freesound via shabda: {word}',
                                'license': 'CC0 (shabda licenses=cc0)'})
            time.sleep(1.5)
    print('shabda:', download(jobs), 'new of', len(jobs))


def main():
    only = sys.argv[sys.argv.index('--only') + 1] if '--only' in sys.argv else None
    ROOT.mkdir(exist_ok=True)
    cat_path = ROOT / 'catalog.json'
    old = json.loads(cat_path.read_text()) if cat_path.exists() else []
    catalog = []
    for name, fn in (('drum-machines', drum_machines), ('uzu', uzu), ('shabda', shabda)):
        if only and only != name:
            catalog += [e for e in old if e['pack'] == {'uzu': 'uzu-drumkit'}.get(name, name)]
            continue
        fn(catalog)
    catalog = [e for e in catalog if (ROOT / e['path']).exists()]
    cat_path.write_text(json.dumps(catalog, indent=0))
    sounds = {}
    for e in catalog:
        sounds.setdefault(e['sound'], []).append(e['path'])
    (ROOT / 'strudel.json').write_text(json.dumps(sounds, indent=0))
    by_pack = {}
    for e in catalog:
        by_pack[e['pack']] = by_pack.get(e['pack'], 0) + 1
    print('catalog:', len(catalog), 'files,', len(sounds), 'sounds', by_pack)


if __name__ == '__main__':
    main()
