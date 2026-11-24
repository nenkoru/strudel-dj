---
title: Strudel DJ
emoji: 🎛️
colorFrom: indigo
colorTo: pink
sdk: static
app_file: index.html
pinned: false
license: agpl-3.0
models:
- nenkoru/strudel-dj-129m
short_description: A 129M model writes Strudel loops in your browser
---

# Strudel DJ

A demo of [strudel-dj-129m](https://huggingface.co/nenkoru/strudel-dj-129m). Pick a key, a style and a model, and
it writes a short [Strudel](https://strudel.cc) program: drums, bass, chords and lead. The embedded strudel.cc
player plays it.

Nothing runs on a server. The page downloads int8 weights (about 130 MB, once, then cached) from the model
repo and runs the model in a Web Worker. `model.mjs` is plain JavaScript; its matrix products use a small
WebAssembly SIMD kernel (`linear.wat`). On a laptop a program takes roughly 5–30 s.

- Code: [github.com/nenkoru/strudel-dj](https://github.com/nenkoru/strudel-dj) (AGPL-3.0; the runtime is in `space/`)
- Work report: [Can a 129M music model write guest parts a DJ would keep?](https://blog.nenkoru.com/posts/strudel-guest-decks/)

The JS runtime matches PyTorch on the same int8 weights to within 3e-5 in the logits. Against the fp32
weights, its top choice agreed at every position of a test prompt.

**AI use:** the model, this page and its text were made mostly by Claude (Anthropic) as a coding agent,
under the author's direction.
