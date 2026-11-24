import json, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from taste import features
rows = [dict(role='bass', voice='acid', section='drop', track='t1', form='answer4+lift+none+build+fill', temperature=0.9, hear='kick low', family='techno', code='note("a").s("x") note("b")'),
        dict(role='chords', voice=None, section=None, track='t2', form='', temperature=None, hear=None, family='house', code=''),
        dict(role='lead', voice='pluck', section='groove', track='t3', form='plain+none+mirror+none+none', temperature=1.0, hear=['kick', 'top'], family='prog', code='x' * 1234)]
js = 'import {tasteFeatures} from "./deckc/src/taste.mjs"; const rows = JSON.parse(process.argv[1]); console.log(JSON.stringify(rows.map((r) => tasteFeatures({...r, voice: r.voice ?? undefined, section: r.section ?? undefined, temperature: r.temperature ?? undefined, hear: r.hear ?? undefined}))));'
out = json.loads(subprocess.run(['node', '--input-type=module', '-e', js, json.dumps(rows)], capture_output=True, text=True, check=True, cwd=Path(__file__).parent.parent).stdout)
for r, o in zip(rows, out):
    py = features(**r)
    assert py == o, (py, o)
print('parity ok')
