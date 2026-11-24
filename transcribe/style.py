"""Style detection and style-matched sample picking: groove rules + CLAP.

    uv run python style.py index                         # embed every sample in ../samples/catalog.json
    uv run python style.py track "<audio>" [start_sec]   # style of a track + a picked kit

Style is decided in two steps, because zero-shot CLAP alone got 6/9 on 5 dubstep and 4
progressive house tracks (it called half-time dubstep "hip hop"):
1. Tempo → family (track2midi.grid on a 60 s excerpt): 112-132 → house/techno, 133-155 →
   dubstep and relatives, 160-185 → drum and bass. A beat-vs-two-beats pulse test on the mix was
   tried for four-on-the-floor vs half-time and was wrong on 4 of 5 dubstep tracks.
2. CLAP (laion/larger_clap_general) picks the subgenre within the family. The prompts describe
   subgenres as labels and press write about them (Deep Medi, Tempa, early UK dubstep, brostep,
   jazz-dub crossovers), not just a genre name: "dubstep" covers very different sounds.
   laion/larger_clap_music loads but scores every prompt at ~0 under transformers 5.22.
Kit: per role, catalog samples ranked by similarity to "{style} {role} sample" and to the excerpt
itself (timbre match), plus a bonus for samples tagged with the style.
"""
import json
import sys
import tempfile

from functools import lru_cache
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

import track2midi as T

LIB = Path(__file__).resolve().parent.parent / 'samples'
MODEL = 'laion/larger_clap_general'
SR = 48000
PROMPTS = {
    'deep house': 'deep house with a steady four-on-the-floor kick, warm chords and a groovy bassline',
    'progressive house': 'progressive house with a four-on-the-floor kick, synth leads, big pads and long builds',
    'tech house': 'tech house with a punchy kick, rolling bassline and percussive loops',
    'techno': 'techno with a driving kick, rumble bass and hypnotic percussion',
    'deep dubstep': 'minimal deep dubstep at 140 bpm in half-time, clean sine sub bass, dub reverb and delay, '
                    'meditative and spacious, sound system culture',
    'jazz dubstep': 'dubstep with live jazz instruments, saxophone or flute melodies, jazzy chords over '
                    'half-time drums and deep sub bass',
    'roots dubstep': 'organic roots dubstep with reggae and dub influences, skanking chords and weighty sub bass',
    'early dubstep': 'early uk dubstep from garage, shuffled two-step drums, dark wobble bass and eerie synths',
    'brostep': 'loud mainstream dubstep with aggressive midrange growl and wobble bass, big drops and vocal samples',
    'riddim': 'riddim dubstep with repetitive metallic bass stabs and heavy half-time drums',
    'trap': 'trap with 808 bass, rolling hi-hats and half-time snares',
    'drum and bass': 'fast drum and bass with breakbeats and reese bass',
    'hip hop': 'hip hop with boom bap drums and rap vocals',
    'ambient': 'ambient music with pads and no drums',
}
FAMILIES = {'four': ['deep house', 'progressive house', 'tech house', 'techno'],
            'halftime': ['deep dubstep', 'jazz dubstep', 'roots dubstep', 'early dubstep', 'brostep', 'riddim', 'trap'],
            'dnb': ['drum and bass'],
            'other': list(PROMPTS)}
ROLES = ['kick', 'snare', 'clap', 'hat', 'openhat', 'perc', 'bass', 'stab', 'pad', 'lead', 'vocal', 'fx']


@lru_cache
def clap():
    from transformers import ClapModel, ClapProcessor
    import torch
    return ClapModel.from_pretrained(MODEL).eval(), ClapProcessor.from_pretrained(MODEL), torch


def _norm(x):
    return x / (np.linalg.norm(x, axis=-1, keepdims=True) + 1e-9)


def _vec(out):
    """transformers 5 returns a ModelOutput whose pooler_output is the projected embedding."""
    return (out.pooler_output if hasattr(out, 'pooler_output') else out).numpy()


def embed_audio(clips):
    model, proc, torch = clap()
    out = []
    for i in range(0, len(clips), 16):
        inp = proc(audio=clips[i:i + 16], sampling_rate=SR, return_tensors='pt')
        with torch.no_grad():
            out.append(_vec(model.get_audio_features(**inp)))
    return _norm(np.concatenate(out))


def embed_text(texts):
    model, proc, torch = clap()
    inp = proc(text=texts, return_tensors='pt', padding=True)
    with torch.no_grad():
        return _norm(_vec(model.get_text_features(**inp)))


def index():
    catalog = json.loads((LIB / 'catalog.json').read_text())
    clips = [librosa.load(LIB / e['path'], sr=SR, mono=True, duration=4)[0] for e in catalog]
    np.save(LIB / 'clap.npy', embed_audio(clips))
    (LIB / 'clap.json').write_text(json.dumps([e['path'] for e in catalog]))
    print('indexed', len(catalog), 'samples')


def groove(path, start=60, dur=120):  # 60 s of a swung track gave 131 instead of 140 BPM
    """Tempo of an excerpt and its family: {bpm, family}."""
    from beat_this.inference import File2Beats
    import torch
    y, sr = librosa.load(path, sr=44100, mono=True, offset=start, duration=dur)
    with tempfile.NamedTemporaryFile(suffix='.wav') as tmp:
        sf.write(tmp.name, y, sr)
        device = 'mps' if torch.backends.mps.is_available() else 'cpu'
        beats, downbeats = File2Beats(checkpoint_path='final0', device=device, dbn=False)(tmp.name)
        hits = T.drum_hits(tmp.name)
    period, _ = T.grid(np.asarray(beats), np.asarray(downbeats), hits)
    bpm = 60 / period
    family = ('dnb' if 160 <= bpm <= 185 else 'four' if 112 <= bpm <= 132 else
              'halftime' if 133 <= bpm <= 155 else 'other')
    return {'bpm': round(bpm, 2), 'family': family}


def style_of(path, start=60):
    g = groove(path, start)
    clips = [librosa.load(path, sr=SR, mono=True, offset=start + o, duration=10)[0] for o in (0, 20, 40)]
    a = embed_audio(clips)
    ref = _norm(a.mean(0))
    names = FAMILIES[g['family']]
    t = embed_text([PROMPTS[n] for n in names])
    scores = (a @ t.T).mean(0)
    order = np.argsort(scores)[::-1]
    return g, [(names[i], float(scores[i])) for i in order], ref


def pick_kit(style, ref, top=3, w_text=0.5, w_ref=0.5, bonus=0.05):
    catalog = json.loads((LIB / 'catalog.json').read_text())
    emb = np.load(LIB / 'clap.npy')
    pos = {p: i for i, p in enumerate(json.loads((LIB / 'clap.json').read_text()))}
    kit = {}
    for r, tvec in zip(ROLES, embed_text([f'{style} {r} sample' for r in ROLES])):
        cands = [e for e in catalog if e['role'] == r and e['path'] in pos]
        if not cands:
            continue
        E = emb[[pos[e['path']] for e in cands]]
        tagged = np.array([any(s in style or style in s for s in e['styles']) for e in cands])
        score = w_text * (E @ tvec) + w_ref * (E @ ref) + bonus * tagged
        kit[r] = [{'sound': cands[i]['sound'], 'path': cands[i]['path'], 'pack': cands[i]['pack'],
                   'score': round(float(score[i]), 3)} for i in np.argsort(score)[::-1][:top]]
    return kit


if __name__ == '__main__':
    if sys.argv[1] == 'index':
        index()
    elif sys.argv[1] == 'track':
        start = float(sys.argv[3]) if len(sys.argv) > 3 else 60
        g, ranked, ref = style_of(sys.argv[2], start)
        print('groove:', g, '| style:', ', '.join(f'{s} {v:.3f}' for s, v in ranked[:3]))
        for role, picks in pick_kit(ranked[0][0], ref).items():
            print(f'  {role:8}', ' | '.join(f"{p['sound']} ({p['pack']}, {p['score']})" for p in picks))
