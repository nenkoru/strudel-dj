# strudel-lm

Text → Strudel loop model for a live companion deck (the "Deck B" Strudel mode in
a separate prototype, not in this repo). The model writes a small, strictly
parsed Strudel dialect ([DIALECT.md](DIALECT.md)); Strudel's own engine plays it. That keeps the
model tiny (≈400 output tokens per 4 bars, not audio tokens every 40 ms), so it can run on-device.

## Pipeline

| Step | File | What it does |
|---|---|---|
| Data | `data/captions.jsonl` | MidiCaps captions (amaai-lab/MidiCaps, CC-BY-SA) for the MIDI files streamed from the first 40 MB of `midicaps.tar.gz` (4334 files) |
| Convert | `convert.py` | 4/4 MIDI → best 4-bar window → `stack(drums, bass, chords, lead)` in the dialect |
| Parse | `js/dialect.mjs` | strict tokenizer/grammar → Strudel patterns; model output is never `eval`'d |
| Check | `roundtrip.py` + `js/query.mjs` | onset/pitch sets of the code vs the MIDI window |
| Render | `js/render.mjs` | superdough in plain Node (`node-web-audio-api`), GM soundfonts + TR-909, cached for offline use, parallel chunks |
| Eval | `evalkit.py`, `baseline.py` | prompt format, symbolic metrics, few-shot baseline through an OpenAI-compatible endpoint |

```bash
uv sync && (cd js && npm install)          # postinstall fixes @kabelsalat's CJS "main"
uv run python convert.py data/captions.jsonl data/raw/midi data/strudel.jsonl
node js/query.mjs < data/strudel.jsonl > data/strudel.events.jsonl
uv run python roundtrip.py data/strudel.jsonl data/strudel.events.jsonl
node js/render.mjs data/strudel.jsonl renders/ref --limit 50
uv run python baseline.py --model qwen3.8-27b-auto --n 30
```

## Results so far (2026-11-04)

- **Dataset**: 2813 loops from 4334 MIDI files (skipped: 675 non-4/4 captions, 383 meter changes,
  463 with fewer than two usable parts); 315 in MidiCaps' test split. Code length p50 784 chars,
  p90 1170. 76% have all four lanes.
- **Round trip**: 2813/2813 parse; onset+pitch F1 = 1.0 against the quantized window. 14% of source
  notes are off the 16th grid (triplets, swing, humanized timing) and get snapped: the dialect's
  main loss.
- **Render**: 50/50 loops, 528 s of audio in 35 s on 12 cores including first downloads;
  10 of ~7000 notes fail (pitch outside a soundfont preset's zones).

- **Baseline** (`qwen3.8-27b-auto`, 3-shot, 30 test captions, `data/baseline/`): 24/30 valid.
  5 of the 6 failures are empty replies (the auto router spent the budget thinking), 1 is a
  mini-notation error. 96% of notes in key (reference: 91%). 20 of 93 instrument names are made
  up (`gm_grand_piano`, `gm_pad_1`…), so those lanes would be silent. Loops are simpler than the
  reference (31 vs 39 events/bar; chord stabs on straight 8ths) and take ~3 min each.

## Audio → loop (`transcribe/`, own uv env: torch, demucs, beat_this, basic-pitch via ONNX)

`track2midi.py` → `ab.py` turns a track into a loop in the dialect plus `<name>.orig.wav`,
`.strudel.wav` and `.mix.wav` for the same 4 bars. `batch.sh` runs a list of tracks.

1. **Grid.** beat_this beats are only tempo candidates (×1, 2, ½, 3/2, ⅔ in 100–180 BPM); the
   drum stem's onsets pick and refine the period by their concentration on a 16th grid. Bar line
   from beat_this downbeats. Needed because beat_this flips 140↔70 in half-time music, followed a
   210 BPM (3/2) pulse on one track, and its 20 ms frames bias median intervals (140 → 140.35).
2. **Stems.** Demucs htdemucs on MPS (~2 min per track, cached).
3. **Drums.** Band-energy onsets on the drum stem → kick / snare / closed hat.
4. **Pitched parts.** Grid-synchronous: per 16th, CQT salience of the stem (bass: 1 pitch C1–G3,
   other: up to 3 pitches C3–C6); a note continues while its pitch holds and no onset hits.
   Basic Pitch (`--basic-pitch`) was tried first: its onsets on sustained sub bass were
   uniformly spread over the grid (no better than chance).
5. **Key.** The Camelot tag from the file name; a Krumhansl estimate only as fallback.

Results on 7 tracks from the author's own collection (2026-11-04):

| Track | BPM | Key | Hits on 16ths | Loop notes in key |
|---|---|---|---|---|
| Track A | 140.00 | E minor | 0.99 | 0.75 |
| Track B | 140.00 | G minor | 0.96 | 0.80 |
| Track C | 140.00 | F minor | 0.98 | 0.90 |
| Track D | 140.00 | C minor (est.) | 0.96 | 0.82 |
| Track E | 140.00 | F minor | 0.73 (triplet swing) | 0.83 |
| Track F | 150.00 | G# minor | 0.99 | 0.78 |
| Track G | 145.00 | F major | 0.62 kick / 0.95 snare / 0.81 hat | 0.72 |

Not verified by listening yet. The "other" stem (pads, wobbles, FX) comes out as clusters of
neighbouring semitones in places: probably timbre/noise rather than chords. These are personal,
commercially released tracks: fine for local testing, not for a distributed dataset.

## Fine-tuned small model

LoRA (rank 16, 16 layers, 1200 steps, `lora.yaml`) on Qwen2.5-Coder-0.5B-Instruct with MLX, on
the 2348 training loops. Same 30 held-out captions as the baseline (`eval_local.py`):

| | qwen3.8-27b, 3-shot | Qwen-Coder 0.5B + LoRA (step 800) | reference loops |
|---|---|---|---|
| Valid code | 0.80 | **1.00** | 1.00 |
| Made-up instrument names | 0.215 | **0.011** | 0 |
| Notes in key | 0.955 | 0.864 | 0.912 |
| Events per bar | 31 | 53 | 39 |
| Time per loop | ~175 s (remote) | **~9 s** (M3 Pro, 81 tok/s) | |

Val loss 1.76 → 0.586 (step 800) → 0.607 (step 1200: slight overfit, so step 800 is used).
Its loops are busier than the reference.

LFM3-1.7B (`train_lfm3.sh`, LoRA through mlx-vlm since mlx-lm cannot load it yet; same data
and steps): val loss 0.573, token accuracy 0.805. Same 30 captions (`eval_local.py --vlm`):
valid 1.00, made-up sounds 0.00, notes in key 0.904, 44 events per bar (closest to the
reference's 39), but ~21 s per loop at 23 tok/s on the M3 Pro, against ~9 s for Qwen 0.5B.

## Beat grid accuracy (found on the Third Deck demo)

The third deck sounded behind the tracks. Kick attacks measured on the clean drum stem were
27-70 ms before the analysed bar line on all six house/dub tracks: the onset detector's peaks
lag attacks. `track2midi.kick_attacks` + `refine_phase` now put the bar line on kick attacks
(residual 5-9 ms to the rise peak on the house pair). Decoders were ruled out: Chrome decodes
both the 128k MP3 and the AAC/MP4 at 0.0 ms against the raw decode. The demo ships AAC in MP4
(gapless start in Chrome and Safari). ffmpeg's atempo adds a constant 10.2 ms, which the build
measures and adds. A blind in-browser "kick calibration" on the mix was tried and dropped: the
dub-techno bass rises as hard as the kick below 100 Hz and the estimate jumped ±50 ms.

## Sample library and style (`fetch_samples.py`, `transcribe/style.py`)

`samples/` holds strudel.cc drum machines (TR-909/808/707, LinnDrum, DMX, MPC60, SP-12...),
uzu-drumkit, and CC0 Freesound sounds via Shabda queried per style and role ("dubstep_flute",
"deep_house_chord_stab", ...). `samples/catalog.json` tags each file with role, styles, source
and license; `samples/strudel.json` loads it in Strudel. Shabda's public server answers bursts
with HTTP 500, hence retries.

Style = tempo family + CLAP (laion/larger_clap_general) over subgenre descriptions taken from
how labels and press describe them. Checked against web descriptions of the test tracks:
three of five matched (early dubstep, brostep, deep dubstep); a live-jazz track came out
early dubstep ✗ and a roots track deep house ✗ (tempo from a 60 s excerpt was 131; the excerpt is now 120 s), progressive house
3/4. Kits: per role, samples ranked by CLAP similarity to "{style} {role} sample" and to the
track itself.

## Third Deck prototype (`deckc/`)

Published as a private Claude artifact.
A track plays; guests tap what joins it; the most voted request starts on the next 8-bar phrase.

- Three sets, each two tracks the page automixes (24 bars solo, 16-bar blend with a bass swap):
  house (DCM Tunnel + Motor City Wave, 124), progressive house (Marc Burt & Beat Doctor, Aerial
  Photograph in two mixes, 133), techno (Patrick Walker, Sterile Knot + Irradiation, 127). Each
  style has its own guest layers (techno: acid line, rumble, ride, toms; progressive: arpeggio,
  off-beat chords, rolling bass, riser + crash). After a transition the guest decks take the key
  of the track now leading.
- Guest decks 3, 4, ... (1-6, added with +), each playing a request for 1, 2 or 4 phrases (8 bars)
  or endlessly; a free deck takes the best-voted request on the next phrase line.
- Phrases: each track's 8-bar phrase start (`phrase` in `deckc/build.py`) comes from bar-to-bar
  novelty averaged per bar position mod 8. Tracks start and blend on their own phrase lines, so the
  page's phrase lines are the music's (Tunnel had been started 2 bars off, so every guest change
  landed mid-phrase).
- Layers avoid superdough's AudioWorklet sounds (supersaw, shape, crush): the bundle loads the
  worklets from data: URLs, which a page sandbox may refuse.
- Grids: Sterile Knot needed a tempo hint (detected 134.9, really 127). Irradiation's kick attacks
  come in two clusters 36 ms apart (a layered kick); its bar line sits between them.

- `deckc/src/engine.mjs` → `site/deckc.js` (esbuild, `NODE_PATH=js/node_modules`): superdough +
  the strict dialect parser in the browser; deck C is queried 0.25 s ahead on the track's grid.
- `deckc/build.py` → `site/data.json`, `site/kit.json`, `site/samples`, `site/tracks`. Demo tracks are
  CC BY / BY-SA from Internet Archive netlabels (credited on the page), analysed with
  `transcribe/track2midi.py` + `ab.py`; the kit is CC0 (Shabda/Freesound, VCSL sax) plus drums cut
  from those tracks (dropped: it sounded bad).
- Layer menus are built in the page from the track's style and key, so the DJ can correct the key.
- Requests: on one device by default (a kiosk at the bar: guests need no account). With the `db`
  capability, signed-in people with access share one queue; votes are one per person; only the DJ
  (editors) writes the now-playing state. Free-text requests go through `sample` (Claude writes a
  pattern, the page parses it before it can play).
- Your own tracks load from disk with a BPM and first-downbeat field and are never uploaded.

## Tiny in-page model (`tiny/`)

`prep.py` turns the MidiCaps loops into one line per lane: a prompt (`bass e minor edm>`) and the
lane's mini-notation only; the page adds the style's sound and effects. Pitched lanes are
transposed into all 12 keys (78k lines, 13.7M characters, 41-character vocabulary). `train.py`
trains a 4.9M-parameter character transformer from scratch with MLX (6 layers, 256 wide, context
448; ~0.9 s/step on the M3 Pro). `export.py` writes int8 weights with per-row scales into
`deckc/site/tiny.json` (6.6 MB, served as JSON because the artifact does not serve .bin).
`deckc/src/tiny.mjs` runs it in plain JavaScript: logits match MLX to 1e-4, ~5 ms per character
in Node, generation yields through a MessageChannel so the guest decks' scheduler keeps running
(setTimeout is clamped to 1 s in background tabs). The page's "ИИ: бас / мелодия / ритм" tiles
and the "AI deck" switch use it; drum parts drop the kick (the track has one).
Raw drafts sounded off-beat: the model's bar groups often add up to 15 or 20 steps, so notes fell
between 16ths. The page now reads each draft back as events, snaps them to 16ths, cuts 1- and
2-bar loops and keeps the loop whose density fits the style and the leading track's energy over the
coming phrase (per-bar energy curves from `deckc/build.py`), with a pitch-variety term for melodies
(density alone chose eight repeats of one note). Notes outside the key's scale move a semitone down
(the model mixes up major and minor). Final model: 2500 steps, valid loss 0.508; 24/24 test drafts parse.

### Style corpus and ratings

`tiny/style_corpus.py` writes 40k rule-made house / prog / techno parts (bass, synth lead, solo
phrases, percussion without kick) at three energies (`lo`/`mid`/`hi` in the prompt), in the page's
16-step encoding. `train.py --resume --extra tiny/data/style.txt` fine-tunes on them mixed with all
of MidiCaps (kept for general musicality): valid loss 0.508 -> 0.405 (1300 steps). Composition lives in
`deckc/src/compose.mjs` (shared by both pages): bass and solo are reduced to one voice, melodic
parts accept only note names.

AI percussion burst into the phrase: track energy is normalised per track, so most bars read `hi`,
and a `hi` draft stacked 4-5 voices at gain 0.45 (a ready-made layer is one voice at 0.3-0.5). Now a
drum loop keeps at most two sounds (one when the track is quiet), each at its ready-made layer's gain,
and both pages set `Mixer.level`: AI percussion eases in over two bars and rides the leading track's
per-bar energy (`drumLevel` in compose.mjs, about a third of full level in a breakdown). The corpus
writes percussion the same way (at most two voices, one fill sound) for the second fine-tune
(1000 steps from the first, valid 0.433 on the new held-out lines; the first one is kept as
`tiny/tiny-style1.*`). Drum scoring also drops half a fill bar (a steady voice that stops for the
last beat) and a fill looped every bar.

`deckc/rate/index.html` (a private Claude artifact with the `db` capability): a phone page
that plays a composed part over 8 bars of a set track at a phrase of chosen energy and stores a
verdict (good / meh / bad) and reasons (off-beat, off-key, too dense, too sparse, boring, wrong
style, bad sound) with the prompt, draft and code in the `ratings` collection, for the next
fine-tune (rejection sampling / preference pairs). The questions ask about fit, not taste.

First 51 ratings (model step 1000): 17 good, 34 meh, none bad; reasons mostly "too sparse" and
"boring", and 18 of 21 parts at quiet phrases were meh. compose.mjs raised the quiet ends of its
density targets, lets percussion keep two voices at any energy (`Mixer.level` still keeps it quiet)
and marks a one-note bass down.

35 more ratings on the owner's tracks (14 good): the prog "rolling" bass, one note in 16ths, was meh
9 times out of 9 (the track already has one); moving parts (octave/fifth jumps, 16th arps, 16th hats
in rises and choruses) were good. The owner's brief: guest decks are there to pump the track up. So
the corpus prog bass moves (a figure per half bar), prog arps and hats play 16ths from `mid`, the
scorer marks down a loop that repeats one 4-step cell, parts are written a notch above the track's
energy (`drive`), and melodic parts get phrase-long effects (`FX`: a kick-ducked level, a filter
opening over the 8 bars below the peak, an echo throw on the last bar). `tiny/rated.py` turns the
"good" ratings into training lines (x20 next to the style corpus) for the third fine-tune.

`deckc/mine.py` (`uv run --with pyrekordbox python deckc/mine.py`) packs the owner's played rekordbox
tracks into `deckc/mine/` for the rating page only (that artifact is private; the public demo never
gets them): rekordbox's own beat grid (first downbeat), key (Camelot) and phrases with their kinds
(PSSI: intro / up / down / chorus / outro), plus our per-bar energy, AAC 80 kb/s. When
`mine/mine.json` is published with the page, parts start on rekordbox's phrase lines of those
tracks and the card shows the phrase kind; the style tag is a guess from the artists.

## Mixxx mode (`mixxx/`, local page only)

For playing with a DDJ-FLX4 in Mixxx (2.5.6 has its mapping; no Ableton Link). The mapping
`ThirdDeck-Clock` (put it on an IAC bus) sends each deck's position, tempo, file tempo, duration,
beat phase and level as SysEx every 40 ms. Mixxx has no downbeat (mixxxdj/mixxx#5218), so the page
matches the deck's track to its analysed library by duration and takes bars and phrases from there
(tracks it does not know get beats from Mixxx's grid). The page plays only the guest decks, into
BlackHole, which Mixxx takes as Aux 1. `Mixer.follow` eases small clock corrections and snaps on
jumps (cue, loop, tempo). Checked with simulated SysEx only, not yet with Mixxx and the FLX4.

## Known gaps

- No triplet/swing grid; no velocity; one part per role.
- Strudel packages are AGPL-3.0-or-later; MidiCaps captions CC-BY-SA, Lakh MIDI has mixed provenance.
  Fine for research; check before shipping anything.
- `superdough` is pinned to 1.2.6 (what `@strudel/soundfonts` 1.2.6 uses); 1.2.6 has no context
  setter and its `initAudio` awaits `resume()`, both worked around in `render.mjs`.

### Bigger model, effects, sections, critic loop (night of 5 Nov)

- `tiny/prep_big.py`: all 4/4 MidiCaps files read straight from `midicaps.tar.gz` (Lakh MIDI; no
  extraction), up to 12 four-bar windows per file instead of one, each lane with a level from its
  onsets per bar and up to two MidiCaps moods (dark, epic, energetic, ...); plus Groove MIDI drums.
  6.9M lines, 1.17G chars (`tiny/data/big-*.txt`).
- `tiny/train.py --data big --layers 8 --dim 320 --out big`: 10M parameters (13.6 MB int8 JSON, about
  2x slower per character in JS than the 5M one; the demo asks it for 2 drafts and composes from
  bar 2 of a phrase). `--init <name>` fine-tunes with the pretrained vocabulary.
- Effect words after `|` (style corpus `--fx`, `FX_WORDS` in compose.mjs): pump, build, throw, wide,
  wash, acid, swell, and from hybrid DJ/live practice cut, call, rise, fade, dub, gate. Section tags
  in the prompt (build / drop / break / groove): the demo derives them from the energy curve, the
  rating page from rekordbox phrase kinds. In a break the corpus strips percussion to hats and claps
  and holds the bass root; a build ends its 2-bar loop with a snare roll.
- Critic loop (`tiny/night.sh`): `sample.py` (MLX, KV cache) writes 8 drafts per prompt,
  `critic.mjs` scores them with the page's own `scoreDraft` + an in-key term + a logistic model of the
  ratings (`reward.py`), keeps the best quarter per role in model spelling, `mix.py` mixes them with
  the style corpus, ratings and a slice of the pretraining corpus, and the model is fine-tuned on
  that; two rounds, then every model is compared on the same 200 prompts. The comparison uses the
  critic the rounds optimise, so it flatters them: listening and new ratings decide.
- Results (critic on 200 prompts, best of 8; rule score best of 2 is what the page gets):
  pretrained `big` valid 0.412; `bigft` / `bigrest1` / `bigrest2` best of 8 −0.52 / −0.51 / −0.49
  (with section tags), `big` −0.45, old `tiny-style3` −0.52 (plain prompts). Best of 2 is within
  0.02 for all of them. `big` was pretrained before cut / call / rise / dub / gate existed and puts
  the same effects in every section; the fine-tuned ones follow sections (build: cut, rise; break:
  4.7 notes per bar, wash, swell, dub; drop: call, gate, pump). Published: `bigrest2`.
  The critic rounds moved the scores by noise-sized amounts: the rules are saturated, more ratings
  are what can move it now. `scoreDraft` returns null on drafts that do not parse (unbalanced
  brackets used to crash the critic); `night.sh` skips steps whose output exists.
- Speed: 1.7 s per draft in Node on an M-series Mac (old model 0.34 s; drafts are also longer, 170
  vs 70 characters, because the new one writes 2-bar `<[..] [..]>` loops and effect words).

### A/B pairs, preference training, hearing the track (5 Nov, day)

- Rating page, «Сравнить две» (default): two parts for the same moment of the same track, one draft
  each at a random temperature (0.75 / 0.95 / 1.1), A plays and then B; one tap picks the one that
  pumps the track up better (or both fit / neither). Rows go to the artifact's `pairs` collection with
  both raw drafts. «По одной» is the old single rating.
- `tiny/dpo.py`: DPO on pairs of drafts (chosen vs rejected for the same prompt) against a frozen copy
  of the starting model, plus 0.2 x next-character loss on a fine-tune corpus so it keeps its music.
  Page pairs count 3x. `node tiny/critic.mjs pairs` makes pairs without a listener (best vs worst of 8
  by the critic); `tiny/dpo.sh <from> <out> [page pairs dir]` runs sample -> pairs -> DPO -> compare.
- `deckc/hear.py`: per bar of every track, which of kick / low / mid / top play, from band power on
  the beats vs between them (kick), between them (bassline) and overall (mid, top), each against the
  track's own loud bars; the frame offset is searched per track because some beat grids sit 30-60 ms
  ahead of the kick. Written into data.json and mine.json as `hear` (rerun after build.py / mine.py).
- `tiny/prep_big.py --hear`: the same MidiCaps windows, each lane with `on <words>` from the other
  parts of its window (kick: bass drum on 2+ beats per bar; low: a bass part; mid: chords or lead; top:
  hats / rides / cymbals), on 85% of lines -> big-hear-*.txt. `mix.py --hear` adds plausible words to
  style lines by section. `tiny/hear.sh <from>` fine-tunes and sets `cfg.hear`; the pages then put
  the track's words for the coming phrase in the prompt (`heardOver`: words in half its bars or more).
- First DPO run on critic pairs (bigrest2 -> bigdpo1, 550 pairs, beta 0.1, 150 steps): held-out pair
  accuracy 0.96, but the model fell apart: drafts that parse 1.00 -> 0.56, first-draft critic score
  -0.74 -> -1.21 (best of 8 rose, the Goodhart signature). Discarded. Now: pairs need both drafts to
  parse, beta 0.3, one pass, anchor weight 1.0; page pairs are what DPO is for, critic pairs at most a
  supplement.
- Rating page on a phone: swipe view (right fits, left doesn't; twins of one moment give DPO pairs
  where verdicts differ; one card in ten returns unannounced and the stats show how often the second
  verdict matches the first), sliders for track and part volume, and the track's phrase before and
  after the part (24 bars, the part's 8 drawn tall). Parts are composed ahead on the Mac:
  `deckc/batch.mjs` (8 in parallel, ~3 min for 416 moments) -> `deckc/mine/batch.json`, published with
  the page; the phone loads the model only when the batch runs out, and keeps the decoded audio of the
  last two tracks only (iOS reloaded the page with the model plus every visited track in memory).
  Regenerate the batch after deploying a new model.
- First swipe session (121 swipes, 18 A/B): fits by role bass 30/47, lead 18/24, solo 12/35, drums 2/8;
  by sampling temperature 1.1: 27/42, 0.95: 25/46, 0.75: 10/26 -> default temperature 0.8 -> 1.0 and
  batches sample 0.9 / 1.1 / 1.3; parts with effect words 54/93 vs 8/21 without. Repeats agreed 5 of 7.
  Twins got the same verdict 45 times out of 55, so only 10 swipe pairs (+10 A/B) for DPO: the verdict
  follows the moment and role more than the draft; too few pairs to train on yet.
- `bighear` (bigrest2 + 3000 steps on 1M `--hear` lines and the style lines with words; valid 0.269):
  critic on section prompts -0.734 first / -0.508 best of 8 vs bigrest2 -0.735 / -0.493: the same.
  The words move it only a little and towards matching the arrangement, not filling its gaps: drums
  `on mid` (no kick, no top) write hats in 9 of 40 drafts vs 18 with `on kick low mid top`. In MIDI
  songs sparse sections are sparse in every part; filling gaps would need it from ratings or rules.
  Published as the pages' model. `VOICES` in compose.mjs: 6 bass, 6 lead, 5 solo timbres and 4 drum
  kits, one picked per part (the style's own 40%), the name saved with each rating.
  `deckc/batch.sh [seed]` regenerates the rating batch.
- Development across phrases: `composePart(..., { prev })` writes a part's next phrase: same timbre,
  the track's energy / section / sound for that phrase, and candidates (fresh drafts and crosses of
  each with the last loop: first half-bar of each bar from one, second half from the other) ranked by
  the page's rules minus 1.5 x |overlap - 0.55| (share of (step, note) events in common). Fresh drafts
  alone shared 5-47%; with crosses a 4-phrase arc stays recognisable (batch median 0.46). The demo's AI
  deck develops its part for as many phrases as the deck's length chips say; batches carry `dev` (the
  next three phrases per part) and the rating page plays them at 2 or 4 phrases.
- Track sounds (the owner: the synths stood out from the track's sound): `engine.useTrackSounds(track)`
  cuts two one-shots from the playing track and registers them as Strudel sounds: `chop` (an 8th from
  the offbeat of the loudest bar with mids, pitched by the part's notes against the track's key root,
  base midi 66-77) and `trackhat` (a 16th from the offbeat of the loudest bar with tops, high-passed at
  6.5 kHz in the code). Lead and solo pick `chop` and drums the `track` kit 40% of the time, the
  style's sound 30%, the rest evenly; the synths got lower filters and more room; supersaw voices were
  dropped (their worklet loads from a data: URL). The rating page cuts per track it plays; the demo
  before each composition, from the leading deck. Neural timbre transfer (RAVE, DDSP) would be the
  next step and is too heavy for a phone.
- Phrase forms (`composePhrase`, compose.mjs FORMS): a phrase is the part's loop A and two variations
  B and C (A with the second half of its bars crossed from other cuts, ~60% kept) arranged as one of:
  (26 in all; first eight here) answer4 A A A A', answer2 A A' A A', abac, lift (second half an octave up), fourth (second half on
  the iv, snapped to key), build (downbeats only for 4 bars, then full, then a fill), fill (a 16th
  run on the last beat), shift (bars 4 and 8 an 8th later). A first version built phrases from
  different pieces and got 4 of 19 swipes (the bass jumped notes, solos lost the thread). Twins in a
  batch get different forms and rows save `form`, so swipes compare forms; the demo's AI deck keeps
  one form for a part's phrases.
- Extra data fine-tune (`tiny/prep_extra.py`, `tiny/swipes.py`, `tiny/data1.sh`): Strudel-Synth
  (21k model-written programs via their MIDI, keys estimated, 20k of 258k lines electronic) and
  NeuralAcid (9k basslines), the liked lines from the rating page x20, 400k hearing lines.
  drum_space was skipped: its bitmask instrument order is undocumented.
- `bigdata` (bighear + 2500 steps on data1: Strudel-Synth, NeuralAcid, liked lines, hearing lines;
  valid 0.259): critic on hear prompts -0.730 / -0.507 vs bighear -0.715 / -0.509 (the same); drum
  drafts that are flat 16th hats 36% -> 26%, more claps and open hats. Published.
- Sampled instruments (`deckc/instruments.py`, 5 MB of mono mp3 in site/samples/, note maps in
  kit.json): FreePats (CC0) lately-bass, fm-piano1 (DX7 E.Piano), new-age, sweep-pad,
  synth-strings-1, synth-pad-choir, synth-fifths, synth-calliope, synth-brass-2
  (https://github.com/freepats); VCSL TX81Z FM Piano (CC0, https://github.com/sgossner/VCSL);
  Wurlitzer EP200 by Greg Sullivan (CC BY 3.0, via https://github.com/sfzinstruments; 3 of its 12
  m4a files were truncated and are skipped). They are VOICES for bass (lately), lead (wurli, dxpiano,
  fmpiano, fifths, brass) and solo (wurli, fmpiano, calliope, choir, strings, newage, sweep); the
  style's own synth now comes 25% of the time. Only one-shot drums are warmed at start; a part's
  instrument notes are fetched by `engine.prepare(code)` before it plays.
- Recipes stacking up to five moves went 3 for 13 in swipes: a part now gets a shape (mostly an
  answer form) plus none, one or two moves. Sampled instruments are normalised by loudness (RMS of
  the first half second), not peak (they were 6x apart), sample voice gains 0.6 (pads 0.5).
  More instruments: FluidR3 GM (CC BY 3.0, Frank Wen; mp3s by gleitz/midi-js-soundfonts), 23 of them
  at C and F# (an artifact version holds 511 files): ep1/ep2, organs, clav, vibes, marimba, kalimba,
  steel drums, music box, pizzicato, string ensemble, warm/poly/halo pads, aahs/oohs, orchestra hit,
  brass section, pan flute, two synth basses, fretless. 9 bass, 22 lead, 25 solo voices in all.
- Training speed on the M3 Pro (24M params, 10 x 448): float32 2.19 s/step, `--bf16` 1.44 s/step;
  `--muon 0.02` (Muon on the blocks' 2-D weights, AdamW for the rest) reached valid 0.513 at step 300
  vs AdamW's 0.617. big24 = 5000 steps of both.
- Audio -> MIDI (`tiny/audio2midi.py`, Python 3.11 env with demucs + basic-pitch): basic-pitch on a
  CC track's Demucs stems put 92% (bass) / 100% (other) of notes in key; onsets come ~25 ms late, then
  88% (other) / 57% (bass) sit within a quarter 16th. Source: MTG-Jamendo (CC / CC-NC), ~6k tracks
  tagged house / techno / minimal / trance, fetched per 1.7 GB part from cdn.freesound.org.
- Audio -> MIDI pipeline, as it runs now: Demucs stems first; tempo and phase from the drum stem's kick
  band by a comb search (100-150 BPM in 0.02 steps x 48 phases; librosa's beat tracker gave half
  tempos and 3% errors), tracks without a steady kick skipped; basic-pitch's bass / other notes moved
  by the per-stem offset (within half a 16th) that puts most onsets on the grid (they came 55-85 ms
  late), tracks where neither part settles (< 60% on the grid) skipped. Pilot: kicks 90-99% on the
  grid, bass 55-83%, other 56-89%; about a third of tracks skipped; ~40 s per 4.5-minute track.
  `tiny/jamendo.sh` runs all 100 parts (download, transcribe, delete), `tiny/prep_jamendo.py` makes
  lines (drum lanes left out: the band-onset drums mix claps with hats). 8 pilot tracks -> 501 lines.
- Variety (the owner: "only synths", "more variety, layering", "dope ear candy", "the AI bass sounds
  very synthy, go through all the others the same way"): played instruments are each role's default
  (HOME: bass fingerbass / Lately / acid, lead ep1 / polysynth / perc. organ, solo sax / ep1 / vibes,
  chords organ / polysynth / dub chord) and bare oscillators get a third of a sample's odds; four
  FluidR3 basses (finger, pick, slap, upright). A `chords` role (stabs: organ, pianos, dub chord,
  strings, brass, orchestra hit), each role equally often on the rating page (drums were 1 in 6).
  Hand percussion from VCSL (CC0, `deckc/perc.py`) as drum kits latin / perc / wood (congas, bongos,
  claves, cowbell, agogo, shaker, tambourine, woodblock, cabasa, darbuka, triangle). Layers: a third
  of lead / solo / chords parts double their notes an octave up on a pad, vibes or strings, some
  basses get a sine sub an octave down. Ear candy on half the parts (`CANDY`): riser, reversed cymbal,
  sub impact, downlifter, laser zap, sleigh bells, finger cymbal, flexatone, slapstick, guiro, cymbal
  swell, each on a fixed spot of the phrase. All in one flat stack (the dialect allows no nesting);
  octave layers shift the note names (no transpose() without @strudel/tonal). Rows save layer, candy.
- Grid alignment (`deckc/align.py`, the owner: parts come in "sharply off"): against kick-band onsets
  the rekordbox grid in mine.json was -85..+95 ms off per track, mostly the mp4s' AAC encoder delay.
  Each track's bar0 now moves by the shift in 0..+100 ms that puts the most kick onset strength on
  the beats (34-90 ms, median ~52; `grid_shift` keeps it). A +-150 ms window let some tracks lock onto
  the 16th before the kick. data.json's demo tracks got the same.
- Entry points (the owner: parts start "neither here nor there", e.g. over a talking intro a bar before
  the music slams in): batch moments come only from rekordbox phrase lines where, over the part's first
  8 bars, the kick neither arrives nor leaves and the loudness does not jump by more than 0.35; a
  change 4 bars in moves the start there, any other change drops the line (829 lines -> 572 as they
  are, plus the moved ones). Drums and bass only where the track has a kick; over a kickless stretch
  lead / solo / chords get soft voices (ep, vibes, kalimba, strings, pads). Parts fade in over their
  first bar (0.3 -> 1) except on a drop, on the rating page and for the demo's fresh AI parts; the
  demo's AI deck skips drums and bass where the leading track has no kick.

## More data (plan, 2026-11-05)

The owner wants a base model that "understands music very well", then genre fine-tunes; two V100 32 GB
are coming for training. Today's pretraining corpus is Lakh (via MidiCaps, 168k files, up to 12 4-bar
windows each, key + 2 transpositions) plus Groove: 1.3 B characters. The 24M model ended at train 0.416 /
valid 0.386 with no overfitting, so it is size-bound on this data, and a bigger model wants more data.

Sources, in order (sizes from the dataset pages; yields are estimates until converted):

| Step | Source | Licence | Size | Expected yield |
|---|---|---|---|---|
| 0 | Lakh: all windows instead of 12 per file, content dedup | CC BY 4.0 | have it | ~x1.5 of the Lakh part |
| 1 | PDMX (`tiny/prep_midi.py pdmx`), clean + dedup subset, 77k scores | CC BY 4.0 | 0.2 GB | done: 62 M chars (tiny/data/pdmx-*.txt; mostly classical, solo pieces give no 2-part windows) |
| 1 | MetaScore, 963k MuseScore scores (.mscz, needs MuseScore CLI to MIDI) | CC BY 4.0 on Zenodo, underlying scores unclear | 6.1 GB | ~0.5-1 B, overlaps PDMX |
| 2 | Los Angeles MIDI v4, 405k | CC BY-NC-SA 4.0 | 9.2 GB | unknown overlap with Lakh |
| 2 | Aria-MIDI deduped, 371k solo piano transcriptions | CC BY-NC-SA 4.0 | 2 GB | not usable yet: performance timing on a default 120 BPM grid (bars don't line up) and one part; needs beat tracking from the notes and a hand split |
| 2 | Discover MIDI, 6.74M (stream the tar.gz, never stored) | CC BY-NC-SA 4.0 | 29 GB | the big one: ~1.7k chars a file, ~11 B before dedup; streaming at ~67 files/s (~28 h on the Mac) into tiny/data/discover-*.txt.gz |
| 3 | GigaMIDI v2, 2.1M (gated: the owner accepts the terms on HF) | CC BY-NC 4.0, research | 5.5 GB zip | overlaps Lakh, MetaMIDI, Discover |
| 4 | Jamendo / FMA electronic audio -> MIDI (tiny/audio2midi.py) | CC per track | streamed | the house/techno share; Demucs on CUDA makes it ~10x faster |

Dedup across collections by a hash of each window's quantised notes (file hashes miss re-exports; a
2025 study finds ~21% of Lakh itself duplicated). Target: 10-20 B characters, x10-15 today's corpus,
with ~15% electronic. Lines files that big belong on the V100 machine (20 B chars = 20 GB of text).

Compute: 6 x params x chars; 50M on 10 B chars = 3e18 FLOPs, ~17 h on two V100s at ~25 TFLOPS each
(longer while the owner's LLM shares the cards; ~3-4 GB per card is enough with batch 16 and gradient
accumulation). Then a format step for "understanding" across parts: whole-window lines with every part
(bass + chords + lead + drums together) and 8-bar windows, which needs a context of ~1.5k characters.

Licences: only the CC BY rows are safe for anything commercial; a model trained on NC data inherits that
question. The owner decides; the NC sets are kept apart (their own lines files) so they can be dropped.

Grid shift reverted (2026-11-05 evening). deckc/align.py moved every track's bar0 34-90 ms later (median
52) by where kick-band onset strength peaks. Likes fell from 7/8 (16:50, before) to 6/26 and then 0/8
after it. The owner had already said the problem was phrase choice, not milliseconds, and an onset-
strength peak lags the true attack (the 1024-sample window), so the "delay" was likely the measurement.
bar0 is back to rekordbox's grid in mine.json and data.json; align.py is kept but not applied. Rating
batches are now small (deckc/batch.sh [seed] 5 -> 40 moments) so each listen-and-fix round is quick.

## Richer sounds (2026-11-06)

The owner: the sounds are "too simple". Two research passes (research_notes/sounds_synthesis.md and
sounds_samples.md) led to:
- Synth voices from recipes verified by an offline render (compose.mjs SYNTHS): filter-envelope stabs and
  plucks, an acid line on a resonant filter, a click sub, a vowel bass and pad, FM bells and plucks, an
  additive organ, a dub-techno chord, a warm saw pad, a vibrato lead. Native Web Audio nodes only:
  supersaw, pulse, the ladder filter, distortion and tremolo are AudioWorklets loaded from data: URLs the
  artifact may refuse. They are complete sounds (no role FX on top); gains levelled to rms ~0.04-0.08.
- The dialect takes the shaping calls they need (lpenv..., fm..., penv..., vib, vowel, orbit, postgain) with
  clamps on numbers that can blow up a mix (Q in dB, FM index, pitch envelope, feedback, gain), up to 18
  calls a lane.
- Analog synth samples (deckc/modular.py): 12 instruments from Modular Samples on Freesound (CC0): Juno-6,
  JX-3P (rave stabs, brass, snap bass), JX-8P, Jupiter-4, SH-2, Xpander, Minitaur. To stay under 511 files
  a version, calliope, fifths, new age, sweep, pan flute, steel drum, choir and orchestra hit were dropped.
- js/render.mjs passes the hap's cycle position to superdough (LFOs and tremolo restarted on every note).
- Styles use them: stabs on rave stabs and filter-envelope stabs, pads/gates/drones on Juno and JX pads,
  arps and sequences on plucks, acid on the 303 recipe, vocal chops on the vowel pad.

## Genre fine-tune and offline swiping (2026-11-06, evening)

- `tiny/prep_midi.py jamendo <folder> jamendo` (PIECES=1): the transcribed Jamendo clips with their
  style tags, drums left out. 2108 files, 15 M characters of programs. Noisy (the base model's loss on
  them is about 3 per token against 1.3 on Discover), but the only real house/techno/progressive audio.
- `tiny/genre.py` (on the GPU server): the fine-tune corpus. Genre programs (Jamendo, a third of Lakh's
  electronic files, NRG-CP, Groove, Strudel-Synth: 130 M characters), genre lines (195 M) and a replay
  of general programs (130 M). Packed by `tiny/ft.sh`: 119 M tokens, about 1800 steps.
- `tiny/ft.sh`: waits for the base model's pretraining to end, fine-tunes base130 to base130ft at a
  third of its rates, then runs `tiny/evalft.py`. The evaluation reports held-out loss on genre and
  general data, plus checks on 48 programs per model: whether they end, whether brackets are balanced,
  how many parts, and how many notes are in key.
- The base model forgot the Strudel-Synth code style during part B (loss above 10 per token on it). The
  fine-tune corpus has it again.
- `tiny/serve.py <model>`: the model over HTTP on the GPU. `MODEL=http://localhost:8787 deckc/batch.sh`
  composes a swipe batch with it through an ssh tunnel. The page needs no change; items carry the
  model's name.
- Rating page offline mode: "Скачать для офлайна" stores the batch's tracks and all samples in Cache
  Storage (about 175 MB), and fetch serves them from there. Every swipe first goes to localStorage and
  is sent from there, so swipes made without a network go out once it returns. The page itself comes
  from claude.ai, so it must be opened online and the tab kept open.
- Jamendo transcriptions cleaned (2026-11-07, `clean_transcribed` and `loopify` in `tiny/prep_midi.py`).
  The raw ones were noisy: the bass jumped octaves and stacked onsets into chords, the lead had octave
  overtones, and above all no two bars matched (the onsets wander). After cleaning, the bass keeps one
  note per 16th folded into its octave. The lead stays between C3 and C6, in the key's scale, one note
  per pitch class. Each part keeps only the notes that repeat in at least half the 2-bar cycles of
  each 8 bars, which is the loop a dance track plays. The base model's loss went from 0.574 to 0.301
  nats per character (real MIDI from Discover: 0.216). The genre corpus was rebuilt with
  `jamendo-clean-*` (`repack.sh` on the GPU server) before the fine-tune started.

## Layers, pockets, even levels (2026-11-07)

Research: `reports/Продюсерские приёмы для гостевых партий.md` (layering, pockets, loudness).

- Levels: `deckc/loudness.py` renders every part of a batch offline, measures BS.1770 loudness and
  stores a gain `norm` per part, at a target per role (lead/acid/bass -21 LUFS ... pads and drones
  -26). The page multiplies it in. The batch of 2026-11-07 spread 16 dB between its 10th and 90th
  percentile parts (vowelpad -45, fmbell -12 LUFS); after levelling, 5 dB. Silent parts are dropped.
- The silent parts had a cause: Strudel's `struct` keeps only notes that begin exactly on a hit, so
  stabs, gates and vocal chops over a melody that rests or sustains there lost most hits (0 of 4 in a
  test), and `arp("0")` drones lost all. The dialect now makes `struct` sample-and-hold: each hit plays
  the notes that last began at or before it. Drones hold the bar's chord (`struct("x")`), arps hold the
  chord on every 16th before arpeggiating. The dialect also does `transpose`/`octave` by numbers
  (@strudel/tonal is not installed) and allows orbit ducking.
- Layers (`compose.mjs` LAYER_SOUND): a sine sub under the bass (the bass high-passed at 110 Hz; the
  sub leaves each beat's first 16th to the kick), air on chords, stabs, arps and gates (a thin
  bright saw an octave up), a twin 12 cents off for pads and drones, a triangle an octave over leads.
  The older second timbres stay in the pool. Styles pick from their own list (STYLES `layers`), and
  their rhythm applies to the layer too.
- Pump: where the track has a kick, a silent lane on every beat ducks the guest orbit (bass deepest,
  solos least): the sidechain of house and techno, in the browser only.
- Pockets: `deckc/hear.py pockets` writes `deckc/mine/pockets.json`: per bar and 16th, how full the
  track's low, mid and high bands are. The batch composer prefers loops whose onsets land where their
  band is emptier than average (`pocketFit`, also stored on the part), picks the style rhythm that
  hits emptier mids, and lifts a lead or solo an octave when the mids are full and the highs open.
- `deckc/batch.mjs` now takes two drafts per part, so there is more to choose from.

## Prerendered swipe cards (2026-11-07)

On an iPhone the rating page took long to start and iOS reloaded it: it decoded whole 6-minute tracks
(~130 MB each in memory) and synthesized every part with superdough. Now `deckc/prerender.py` renders
each card on the Mac into one AAC file, `deckc/mine/moments/<pairId>.mp4` (~1 MB). The file holds a
click, the track's stretch (8 bars before the moment, the part's bars, 8 after, at the track's
`trim`) and both parts. Each part is two phrases rendered by `js/render.mjs --keep-level`, with
what the live mixer did baked in: `norm`, the entry ramp, the percussion level and the kick pump. The
page plays such a batch with a small Web Audio player (`Player` in `deckc/rate/index.html`). It
decodes the card's file, finds the click, and starts the stretch and the part together on two gains
(the volume sliders and solo still work). It never loads superdough, the samples or the model. First
card in about 0.2 s, next in about 0.1 s (local test). The artifact holds about 190 cards (256 MB per
version); the full tracks, samples and browser model are no longer published with it. If a batch
has no `audio`, the page plays it live as before.
