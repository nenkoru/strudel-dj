"""Prompt format and symbolic metrics shared by the baseline, SFT data and (later) RL reward."""
import json
import subprocess
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).parent
SYSTEM = (ROOT / 'DIALECT.md').read_text() + '\nAnswer with the Strudel code only: no prose, no code fences.'
# Fine-tuned models learn the dialect from data, so they get a one-line instruction.
SYSTEM_SHORT = 'Write a 4-bar Strudel loop in the loop dialect. Code only.'
PCS = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7,
       'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}
MAJOR, MINOR = [0, 2, 4, 5, 7, 9, 11], [0, 2, 3, 5, 7, 8, 10, 11]  # minor includes the raised 7th
GM_SOUNDS = set(json.loads((ROOT / 'gm_programs.json').read_text()).values())


def prompt(row):
    return f"{row['caption']}\nTempo: {row['tempo']} BPM. Key: {row['key']}.\nWrite the 4-bar loop."


def clean(text):
    """Model reply → bare code (drops think blocks and markdown fences)."""
    if '</think>' in text:
        text = text.split('</think>', 1)[1]
    text = text.strip()
    if '```' in text:
        parts = text.split('```')
        text = max(parts[1::2], key=len)
        text = text.split('\n', 1)[1] if text.split('\n', 1)[0].strip().isalpha() else text
    return text.strip()


def query(rows):
    """[{id, code}] → {id: {ok, events|error}} through the strict Node parser."""
    payload = ''.join(json.dumps({'id': r['id'], 'code': r['code']}) + '\n' for r in rows)
    out = subprocess.run(['node', str(ROOT / 'js/query.mjs')], input=payload, capture_output=True, text=True,
                         check=True).stdout
    return {r['id']: r for r in map(json.loads, out.splitlines())}


def scale(key):
    tonic, mode = key.split()
    return {(PCS[tonic] + i) % 12 for i in (MINOR if mode == 'minor' else MAJOR)}


def lane_roles(code):
    """Rough role per lane from its sound, for coverage stats."""
    roles = []
    for line in code.split('\n'):
        if 'bank(' in line or line.strip().startswith('s('):
            roles.append('drums')
        elif 'note(' in line:
            roles.append('bass' if '_bass' in line else 'pitched')
    return roles


def metrics(row, result):
    if not result['ok']:
        return {'valid': 0, 'error': result['error']}
    ev = result['events']
    pitched = [e['midi'] for e in ev if e['midi'] is not None]
    sounds = {e['s'] for e in ev if e['s'] and e['s'].startswith('gm_')}
    m = {'valid': 1, 'events_per_bar': len(ev) / 4, 'lanes': len({e['lane'] for e in ev}),
         'has_drums': int(any(e['midi'] is None for e in ev)),
         'in_key': mean((p % 12) in scale(row['key']) for p in pitched) if pitched else None,
         'sounds': sorted(sounds),
         'unknown_sounds': len(sounds - GM_SOUNDS) / len(sounds) if sounds else None}  # those lanes are silent
    return m


def summarize(ms):
    ok = [m for m in ms if m['valid']]
    agg = lambda k: round(mean(m[k] for m in ok if m.get(k) is not None), 3) if ok else None
    return {'n': len(ms), 'valid': round(len(ok) / len(ms), 3), 'events_per_bar': agg('events_per_bar'),
            'lanes': agg('lanes'), 'has_drums': agg('has_drums'), 'in_key': agg('in_key'),
            'unknown_sounds': agg('unknown_sounds')}
