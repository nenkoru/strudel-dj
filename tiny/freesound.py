"""Loops from Freesound for the house/techno side of the corpus: every sound tagged `loop` together with
a bass, synth, drum or dance-music tag, found through the Freesound API (the owner's key in
~/.freesound_key, sent as a header), saved as its high-quality mp3 preview plus one JSON line of
metadata each (licence, author, tags, the analysed tempo and key) in data/raw/dl/freesound/.
Licences are kept per sound: CC BY needs the author credited, CC BY-NC keeps the NC question.

Search pages count against the API limits (60 a minute, 2000 a day); previews are plain files and
do not, so a page's 150 previews download 8 at a time. Resumes: sounds already in meta.jsonl are skipped.

    python3 tiny/freesound.py
"""
import json
import time
from concurrent.futures import ThreadPoolExecutor
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(__file__).parent.parent / 'data' / 'raw' / 'dl' / 'freesound'
TAGS = ['bass', 'bassline', 'synth', 'lead', 'chord', 'chords', 'pad', 'arp', 'drums', 'drum', 'beat', 'percussion',
        'techno', 'house', 'trance', 'edm', 'minimal', 'acid', 'progressive', 'deep-house', 'tech-house']
FIELDS = 'id,name,tags,license,username,duration,previews,ac_analysis,bpm,type'


def api(key, params):
    url = 'https://freesound.org/apiv2/search/text/?' + urllib.parse.urlencode(params)
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, headers={'Authorization': f'Token {key}'})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:  # 429 when over the per-minute limit, network hiccups
            print('retry', attempt, repr(e)[:80], flush=True)
            time.sleep(30 * (attempt + 1))
    raise IOError('search failed: ' + url)


def main():
    key = (Path.home() / '.freesound_key').read_text().strip()
    OUT.mkdir(parents=True, exist_ok=True)
    meta = OUT / 'meta.jsonl'
    seen = {json.loads(l)['id'] for l in open(meta)} if meta.exists() else set()
    calls = 0
    with open(meta, 'a') as fm:
        for tag in TAGS:
            page, got = 1, 0
            while True:
                res = api(key, {'query': '', 'filter': f'tag:loop tag:{tag} duration:[1 TO 60]', 'fields': FIELDS,
                                'page_size': 150, 'page': page, 'sort': 'created_desc'})
                calls += 1
                time.sleep(1.1)  # under 60 calls a minute
                new = [x for x in res.get('results', []) if x['id'] not in seen and x.get('previews', {}).get('preview-hq-mp3')]

                def fetch(x):
                    path = OUT / f"{x['id']}.mp3"
                    try:
                        urllib.request.urlretrieve(x['previews']['preview-hq-mp3'], path)
                        return x, path
                    except Exception as e:
                        print('skip', x['id'], repr(e)[:60], flush=True)
                        return x, None

                with ThreadPoolExecutor(8) as ex:
                    for x, path in ex.map(fetch, new):
                        if path is None:
                            continue
                        a = x.get('ac_analysis') or {}
                        fm.write(json.dumps({'id': x['id'], 'file': path.name, 'name': x['name'], 'tags': x['tags'],
                                             'license': x['license'], 'author': x['username'], 'duration': x['duration'],
                                             'bpm': a.get('ac_tempo') or x.get('bpm'), 'key': a.get('ac_tonality'),
                                             'loop': a.get('ac_loop'), 'query': tag}) + '\n')
                        fm.flush()
                        seen.add(x['id']); got += 1
                print(f'{tag} page {page}: {len(seen)} sounds, {calls} calls', flush=True)
                if not res.get('next'):
                    break
                page += 1
            print(f'{tag}: +{got}', flush=True)
    print('done', len(seen), 'sounds')


if __name__ == '__main__':
    main()
