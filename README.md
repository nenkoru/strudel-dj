# strudel-lm

A small language model that writes [Strudel](https://strudel.cc) loops (bass, chords, lead, percussion)
to play over a DJ's track: "AI guest decks" that join on the next 8-bar phrase and pump the track up.

The model writes a small, strictly parsed Strudel dialect ([DIALECT.md](DIALECT.md)). The page parses it
with its own grammar (model output is never `eval`'d) and Strudel's engine plays it. A part is about 400
tokens per 4 bars, so the model can be small enough to run near the music.

**Work report:** [Can a 129M music model write guest parts a DJ would keep?](https://blog.nenkoru.com/posts/strudel-guest-decks/)
explains the goal, the models, the results so far and what to try next.

## Status (2026-11-24)

- **Model.** `base130`: a 129M decoder (16 × 768, context 2048, BPE with 4096 tokens), pretrained on MIDI
  converted to the dialect (about 5.7B tokens), then fine-tuned on house, techno and progressive (FT1–FT4).
  See [reports/ft/README.md](reports/ft/README.md) (in Russian) for the evaluation.
- **Listening test.** In blind swipes by one listener, FT3 got 37% of its parts marked "fits" (14/38,
  95% interval 23–53%) against 26% for the previous small model (17/66, 17–37%) on the same moments.
- **Next.** FT3 vs FT4 on whole programs picked best-of-6 by a critic and a taste model; a fifth fine-tune.

This is research code, published as a work log. It is not a packaged library.

## Layout

| Path | What it does |
| --- | --- |
| `convert.py`, `roundtrip.py`, `evalkit.py` | MIDI → 4-bar loops in the dialect, round-trip check, metrics |
| `js/` | the dialect parser (`dialect.mjs`), Strudel/superdough offline renderer (`render.mjs`) |
| `transcribe/` | audio → loop: beat grid, Demucs stems, drums and pitched parts (own uv env) |
| `tiny/` | the models: data prep, tokenizer, training (MLX and PyTorch), fine-tune data, generation, critic, DPO, taste model, Jamendo transcription |
| `deckc/` | the deck pages: composition (`src/compose.mjs`), the browser engine, swipe batches, loudness levelling, card prerendering, the swipe page (`rate/index.html`) |
| `mixxx/` | a Mixxx controller script that sends deck clocks as SysEx (experimental) |
| `reports/`, `research_notes/` | evaluation reports and research notes (mostly in Russian) |
| [NOTES.md](NOTES.md) | the full lab notebook: every step, with numbers |

## Quick start (the parts that need no private data)

```bash
uv sync && (cd js && npm install)           # postinstall fixes @kabelsalat's CJS "main"
uv run python convert.py data/captions.jsonl data/raw/midi data/strudel.jsonl
node js/query.mjs < data/strudel.jsonl > data/strudel.events.jsonl
uv run python roundtrip.py data/strudel.jsonl data/strudel.events.jsonl
node js/render.mjs data/strudel.jsonl renders/ref --limit 50
```

`data/` is not included: it comes from public MIDI collections (MidiCaps/Lakh, Groove, PDMX, Discover MIDI,
and others listed in NOTES.md), each under its own licence. The `pyproject.toml` workspace names an `lfm`
member that is not part of this repo; drop it if `uv sync` complains.

## Not included

- **Data and corpora** (tens of GB; each source has its own licence, some non-commercial).
- **Model weights** (the FT1–FT4 checkpoints are about 0.5 GB each).
- **Listening data and the owner's tracks:** swipe ratings, the rekordbox export, prerendered cards, and
  the taste model's weights (its features name tracks). Tracks used in tests are anonymised as Track A–G.

## Licences

- This repository: **AGPL-3.0-or-later** ([LICENSE](LICENSE)), matching Strudel and superdough, which it
  builds on.
- Training data is not distributed here. Parts of it are CC BY-NC-SA; a model trained on it inherits that
  question. Check before shipping anything.

## AI use

This work was done mostly by AI under the author's direction. The design, most of the code, the training
and data runs and the analysis were done by Claude (Anthropic) as a coding agent in Claude Code. Some
routine code was written by a local Qwen model from a written spec, with Claude checking it. The author set
the goals and constraints, did every swipe and decided what to publish.
