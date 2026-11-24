# Layering and processing recipes for "finished" synth guest parts (house / techno / progressive), mapped to Strudel/superdough

Researched 2026-11-07. Builds on `research_notes/sounds_synthesis.md` (control reference, 15 single-voice recipes,
pitfalls, performance) and does not repeat it. Focus here: **multi-layer stacks, movement, per-role processing
chains, genre specifics**, and how to express them in *this project's dialect* (`js/dialect.mjs`).

Tempo maths used throughout (computed, not sourced): one beat = 60000/BPM ms. At 124 BPM: 1/4 = 484 ms,
1/8 = 242 ms, dotted 1/8 = 363 ms, 1/16 = 121 ms, 1/32 = 60 ms. In Strudel one cycle = one bar, so 1/16 = 1/16 cycle.

Local code checks done for this note (verified against `js/node_modules`, superdough 1.2.6, @strudel/core 1.2.6):
- **`transpose` is whitelisted but broken.** `note("a1 c2").transpose(12)` through `compile()` throws
  `pat[m] is not a function`, because `transpose` lives in `@strudel/tonal`, which is not installed or imported.
- **`octave` is a no-op for synths.** It is accepted and sets `{octave:1}`, but superdough 1.2.6 never reads it.
  `getFrequencyFromValue` uses only `note`/`freq`.
- So **octave and detune layers must be written as explicit notes in each lane's mini string**. Fractional MIDI
  numbers work: `note("57.1")` goes straight into `midiToFreq`, so 57.1 = A3 + 10 cents.
- Mini-notation weights give micro-timing and swing. `[a1@1.15 a1@0.85]*2` puts the off-16th at 0.2875 instead of
  0.25 of the beat-pair, i.e. 57.5 % swing (verified with `queryArc`). `a1*8?0.3` keeps ~70 % of hits (23 of 32 over 4 bars).
- A per-step `gain("0.9 0.5 0.8 0.5")` lands on each step (verified), so accents and ghost notes can be written as step patterns.
- superdough 1.2.6 has **no reverb pre-delay control and no ping-pong delay** (grep: no `predelay`/`ping` in superdough sources).
  The delay is one feedback delay per orbit, default `delaysync` 3/16 cycle = dotted 1/8.
- `velocity` only multiplies gain (superdough.mjs l.505 comment: "velocity currently only multiplies with gain"), so it
  **does not open the filter**. Accent has to be written explicitly with `lpenv`/`lpf`/`lpdecay` step patterns.
- `nudge` (timing offset) is implemented only in `sampler.mjs`, so it does nothing on synth voices.
- Dialect limits: ≤ 8 lanes in `stack(...)`, ≤ 18 methods per lane, single-argument methods, ≤ 256 events/cycle.
  No `superimpose`/`off`/`jux`/`layer`/`echo` (they need function arguments). **Layering = several lanes with
  the same rhythm string and different notes, sound, filter, pan and gain.**
- **Missing from the current whitelist** (these exist in superdough 1.2.6): `unison`, `detune`, `spread`, `distort`,
  `ftype`, `drive`, `tremolosync`/`tremolodepth`, `phaser`, `pw`, `compressor`, `djf`, `noise`.
  `s("supersaw")` still works with its defaults (unison 5, detune .18 = ±9 c, spread .6).

---

## 1. Layering: how producers stack bass, stabs/chords, pads and leads

### Takeaway
Pro parts are almost always 2–4 layers, **each band-limited to its own job**:
- **Bass:** a sine sub low-passed at ~80–190 Hz and kept mono, plus a saw/square mid layer an octave or two up,
  high-passed at ~65–150 Hz and low-passed at ~350 Hz–3 kHz, plus an optional wide percussive top.
- **Chords:** stacked saws (intervals inside one patch, or octave doubling of the root), a noise layer for top
  detail, high-pass at ~250 Hz, widening only above ~2 kHz.
- **Supersaw-style leads and pads:** 7 voices; the "common" JP-8000 spread is 40–90 cents in total.

Our "too simple" sound is a single unfiltered oscillator per part.

### Cited Findings
**Bass (three layers)**
- Attack's "Layering Synths" builds a three-layer stack:
  - **Sine sub** with its notes around F#0, "peaking around 60 Hz"; 40–60 Hz is suggested for sub. Rolled off above
    190 Hz, low-cut at 30 Hz. The first note of each 2-bar section is muted to avoid clashing with the kick. Ducked with LFO Tool.
  - **Lower-mid bass layer**: the same MIDI **two octaves up** (F#2) on a VA synth. Osc A is a saw at 0, Osc B a
    triangle **one octave lower**. Cutoff low (19.5 on the dial), envelope amount high (59.5), filter-envelope sustain
    reduced and amp sustain 0 for tightness. Soft-clip distortion (amount up, mix down) and tape saturation. EQ cut up to
    ~130 Hz, roll-off above 3 kHz, 2–3 dB of compression.
  — [Attack Magazine, Layering Synths](https://www.attackmagazine.com/technique/synth-secrets/layering-synths/)
- Attack's "Warehouse Rolling Techno Bass" (G, 4/4):
  - **Sub sample**: transient shaper with attack fully down and sustain up, **low-pass ~80 Hz at 12 dB/oct**, overdrive at
    ~35 % wet "keeping the low end intact".
  - **Bassline**: saw or square with a fast attack or a fast filter envelope, C2 range (mostly G2), **first 16th of every
    beat left empty**. **HP ~65 Hz, LP ~350 Hz**, slight cut at 100 Hz, slight boost at ~330 Hz. LFO-Tool sidechain whose
    slower release adds swing.
  - **Percussive top**: the kick copied, through a **1/16 delay at 100 % wet**, then stereo-widened (ADT/chorus).
  - **Kick**: a −4.5 dB bell at 98 Hz to make room for the bass.
  — [Attack Magazine, Warehouse Rolling Techno Bass](https://www.attackmagazine.com/technique/tutorials/warehouse-rolling-techno-bass/)
- A 150 Hz split between sub and "high bass" is suggested. The same source cuts ~4.5 dB at 264 Hz on the bass and boosts
  the kick near 46 Hz. — [Audiotent, Mixing Kick and Bass](https://www.audiotent.com/blogs/production-tips/mixing-kick-and-bass)
- A rolling-techno top layer is widened with chorus/stereo tools so it "stands apart" from the mono low end.
  — [Attack Magazine, Warehouse Rolling Techno Bass](https://www.attackmagazine.com/technique/tutorials/warehouse-rolling-techno-bass/)

**Chords and stabs**
- Attack's chord layer is three saws in one patch:
  - Osc 2 at **+3 semitones**, Osc 3 **−12 +7** (a minor chord from one key).
  - **Noise generator on** "for top-end detail".
  - Cutoff low, envelope amount max, resonance 25, tube distortion 40 %. Filter envelope medium decay with short
    sustain; amp envelope high sustain with medium release.
  - Then **low cut up to 250 Hz**, ~5 dB of compression when the filter opens, and widening only on bands **above 2 kHz**
    (Ozone Imager, Stereoize 13.2).
  — [Attack Magazine, Layering Synths](https://www.attackmagazine.com/technique/synth-secrets/layering-synths/)
- The "Landlord" rave stab is an E-minor triad E4-G4-B4 **with E3 and E2 doubling the root**.
  - Osc 2 is tuned **+12** and phase-modulated by Osc 1.
  - Filters are chained LP18 → HP12 → LP24.
  - Bitcrusher at 12 or 8 bit as an alternative to Runciter, then heavy compression and saturation.
  - Resampled and played back through a **12 dB LP at ~411 Hz** with a full-amount filter envelope (attack open,
    sustain max, release ~1.5 s).
  — [Attack Magazine, Landlord stab](https://www.attackmagazine.com/technique/synth-secrets/make-rave-stabs-like-the-landlord-stab/)
- In house chord writing the **bass plays the roots and the keys leave the root out**. Adding 9ths and 11ths (e.g. D and
  F on Cm7) gives "dark, blurry" colour. — [Attack Magazine, Levelling Up Your Chord Stabs](https://www.attackmagazine.com/technique/passing-notes/levelling-up-your-chord-stabs/)
- Keys in the same article layer a piano (Spitfire Firewood) with a **chorused electric piano**, i.e. two keyboard
  timbres on one part. — [Attack Magazine, Levelling Up Your Chord Stabs](https://www.attackmagazine.com/technique/passing-notes/levelling-up-your-chord-stabs/)
- Deep-house chords are defined by jazz 7ths, with 9ths and 11ths as extensions. — [Attack Magazine, Passing Notes: Deep House Chords](https://attackmagazine.com/?p=704)

**Supersaw, leads and pads**
- The JP-8000 supersaw is **7 free-running saws**. The detune fader spreads the 6 side saws while the centre saw stays
  in tune, and a mix fader sets centre vs sides. — [Wikipedia, Supersaw / JP-8000](https://www.Wikipedia.org/wiki/Supersaw); [Perfect Circuit, Super Saw history](https://www.perfectcircuit.com/signal/super-saw-history)
- The measured relative frequencies at **max detune** are .893, .939, .980, 1.0, 1.020, 1.064, 1.110. A "common setting
  is in the 40–90 cent range, meaning 20–45 cents of detune to higher and lower side". The original has a key-tracked HPF
  "somewhere around the fundamental".
  — [KVR forum thread (Oden), citing Szabo's thesis](https://www.kvraudio.com/forum/viewtopic.php?p=4644620)
  (forum measurement, not a manufacturer spec; **unverified**). Converted, max detune = −196 c / +181 c on the outer voices.
- Progressive plucks are "detuned saws passed through a low pass filter" (4-pole) with a short-attack, short-decay
  envelope on cutoff. — [ADSR Sounds, Progressive House Pluck (Massive)](https://www.adsrsounds.com/ni-massive-tutorials/progressive-house-pluck-synth/)

### Inferences
- **Level and band ratios.** I found no source that gives dB ratios between layers. The sources do agree on **band
  ownership**: the sub owns < 80–190 Hz and is mono; the mid layer owns ~100 Hz–3 kHz with its lows cut; the top owns
  > 2–3 kHz and may be wide. A program can enforce this with `lpf` on the sub lane and `hpf` on every other lane,
  rather than by guessing gain ratios.
- **superdough `detune` mapping.** superdough's `detune` is the *total* spread in semitones (per sounds_synthesis.md), so the
  JP "common" 40–90 c total means **`detune(0.4)`–`detune(0.9)`** with `unison(7)`. The superdough default .18 (±9 c) is
  well below a classic supersaw and is one reason it sounds thin. Suggested ranges: pads .3–.5, trance and progressive
  leads .4–.7, reese bass .15–.25 with `spread` ≤ .3. These all need `unison`/`detune`/`spread` added to the whitelist.
- **Detune with today's whitelist.** Use a second lane on fractional MIDI notes (≈ +8 to +12 c), panned opposite,
  with matching `gain`.

**Recipe L1 — three-layer house/techno bass** (not rendered; 4 lanes, all native nodes)
```
stack(
  note("a1 ~ [~ a1] ~ a1 ~ [~ a1] ~").s("sine").lpf(120).decay(0.25).sustain(0.8).release(0.05).orbit(4).gain(0.8),
  note("a2 ~ [~ a2] ~ a2 ~ [~ a2] ~").s("sawtooth").hpf(150).lpf("500:3:2.5").lpdecay(0.12).decay(0.18).sustain(0.3).release(0.04).shape(0.25).orbit(4).gain(0.45),
  note("a3 ~ [~ a3] ~ a3 ~ [~ a3] ~").s("square").n(5).hpf(400).lpf("1500:2:2").decay(0.08).sustain(0).orbit(4).gain(0.15),
  s("~ ~ [~ white] ~ ~ ~ [~ white] ~").hpf(3000).decay(0.03).sustain(0).pan("0.3 0.7").orbit(4).gain(0.12))
```
Notes on L1:
- The sub has no `room`/`delay`, and the whole bass uses its own orbit so no reverb reaches the lows.
- The mid lane copies the sub rhythm exactly, an octave up, with `hpf(150)` (Audiotent's 150 Hz split).
- The click/noise top is the only wide element.
- Leave the first 16th of each beat empty, as in the Attack warehouse bass, so the kick has room.

**Recipe L2 — layered deep-house stab** (not rendered)
```
stack(
  note("<[eb3,g3,bb3,d4] [ab3,c4,eb4,g4]>").struct("~ x ~ [~ x] ~ x ~ ~").s("sawtooth").hpf(250).lpf("600:4:4").decay(0.3).sustain(0).release(0.08).orbit(2).gain(0.3),
  note("<[51.1,55.1,58.1,62.1] [56.1,60.1,63.1,67.1]>").struct("~ x ~ [~ x] ~ x ~ ~").s("sawtooth").hpf(250).lpf("600:4:4").decay(0.3).sustain(0).pan(0.8).orbit(2).gain(0.22),
  note("<[eb4,bb4] [ab4,eb5]>").struct("~ x ~ [~ x] ~ x ~ ~").s("square").n(9).hpf(800).decay(0.12).sustain(0).pan(0.25).orbit(2).gain(0.12),
  s("~ white ~ [~ white] ~ white ~ ~").hpf(5000).decay(0.05).sustain(0).orbit(2).gain(0.06)).room(...)
```
(Write the room and delay on each lane; the trailing `.room(...)` is shorthand.)

The layers in L2:
- the body, with the root omitted because the guest bass/track owns it;
- a +10 c detuned copy panned right;
- a short bright octave "pluck" transient panned left;
- a noise "air" tick on the same hits.

The orbit gets `room(0.3).size(3)` plus `delay(0.25)` (dotted 1/8 by default).

**Recipe L3 — supersaw lead with an octave layer** (needs `unison`/`detune`/`spread` whitelisted)
```
stack(
  note(MEL).s("supersaw").unison(7).detune(0.5).spread(0.8).hpf(200).lpf("3500:2:1").attack(0.005).decay(0.3).sustain(0.6).release(0.3).orbit(5).gain(0.4),
  note(MEL_OCT_UP).s("sawtooth").hpf(1000).lpf(6000).decay(0.2).sustain(0.4).orbit(5).gain(0.12),
  note(MEL_OCT_DOWN).s("triangle").hpf(150).decay(0.2).sustain(0.6).orbit(5).gain(0.2))
```
The octave-up and octave-down copies are quiet; roughly −8 to −12 dB is a common-practice guess (**unverified**).

**Recipe L4 — pad, 3 layers** (not rendered)
- **Body:** `s("supersaw")` or two plain saw lanes on fractional notes ±8 c, `attack(0.6) release(1.5) hpf(200) lpf(1200)`.
- **Air:** `s("pink")` on the same chord rhythm, `hpf(6000) gain(0.04) attack(0.8)`, wide pan pattern.
- **Shimmer:** a sine/triangle octave above, `gain` ~1/4 of the body, `vib("5:0.08")` (whitelisted) for life.

### Gaps
- No primary source found with **numeric level ratios** (dB) between sub, mid and top, or between body and octave layers.
- No source with exact voice counts and detune for Sylenth/Serum-era progressive plucks. The ADSR/Cymatics pages
  were seen only as search snippets.
- JP-8000 detune values are forum measurements and the Szabo thesis numbers were not read directly (fetch failed); **unverified**.
- None of the L1–L4 recipes above has been rendered; they need a render pass (peak, rms, band energy) before use.

---

## 2. Movement: filter envelopes, LFO sync, accents, ghost notes, humanised timing, 8–16-bar automation

### Takeaway
Movement comes from:
1. **per-note filter envelopes**, with the filter opening slightly ahead of the amp;
2. **step-level accent/velocity patterns** (on-beats louder, ghosts ≤ ~55 % level, about ±10 % random-ish variation);
3. **gentle swing** of 54–58 % on 16ths, with the kick kept straight;
4. **slow cutoff automation** across 8–16 bars in builds.

In our dialect all four are expressible with mini-notation step patterns and `<…>` per-bar alternation.

### Cited Findings
- **Pluck envelopes.** A very tight pluck uses a filter or amp **decay of ~20 ms (or 1/32–1/64)**; longer decay gives a more
  sustained pluck. — [Cymatics, Plucks in Serum](https://cymatics.fm/blogs/production/creating-plucks-xfer-serum) (search snippet)
- The filter envelope should attack slightly **faster than the amp envelope** so brightness arrives just before full volume.
  — [Avid, How to make trance plucks](https://www.avid.com/resource-center/how-to-make-trance-plucks) (search snippet)
- **Swing range.** MPC-style grooves commonly sit at ~**54–63 %** swing. Logic's humanize at about **±10 velocity** is
  "enough variation without sounding random". — [Unison, How to humanize MIDI](https://unison.audio/how-to-humanize-midi/)
- MPC-style swing suits house and deep house; apply it to hats, claps and percussion and **keep the kick straight**.
  — [Samplesound, Groove templates](https://www.samplesoundmusic.com/blogs/news/groove-templates-explained-how-to-inject-human-feel-into-edm-and-house)
- Make **on-beat hits stronger than off-beat** ones. — [Loopcloud, 7 drum programming tips](https://www.loopcloud.com/cloud/blog/5254-7-Drum-Programming-Tips-to-Improve-Any-Groove)
- Ghost notes sit below about **velocity 70** (of 127). Consistent micro-timing patterns, e.g. early hats against a
  laid-back snare, beat random humanize.
  — [Sounds Heavy, Programming realistic drums](https://soundsheavy.pages.dev/drums-percussion/programming-realistic-drums); [Sounds Heavy, MIDI drum humanization](https://soundsheavy.pages.dev/drums-percussion/midi-drum-humanization)
- **Sidechain timing feel.** A shorter release puts the pump's swell earlier in the beat, a longer one makes it lazier.
  — [MusicRadar, sidechain compression](https://musicradar.com/how-to/sidechain-compression-mix)
- **Builds.** The chord layer's filter is automated for breakdown tension.
  — [Attack Magazine, Layering Synths](https://www.attackmagazine.com/technique/synth-secrets/layering-synths/)
- **Slow motion on resampled stabs.** A long filter-envelope release (~1.5 s) on a resampled stab gives a slowly closing tail.
  — [Attack Magazine, Landlord stab](https://www.attackmagazine.com/technique/synth-secrets/make-rave-stabs-like-the-landlord-stab/)
- **Kick-locked bass rhythm.** The warehouse bass leaves the first 16th of each beat empty, and its sidechain envelope
  starts below full level on the first notes. — [Attack Magazine, Warehouse Rolling Techno Bass](https://www.attackmagazine.com/technique/tutorials/warehouse-rolling-techno-bass/)

### Inferences
These are dialect translations; the swing and gain-step mechanics were verified with `queryArc`, the sound was not rendered.

- **Swing.** Write 16th pairs as `[x@1.15 x@0.85]`, which gives 57.5 % swing. `@1.1/@0.9` = 55 % and
  `@1.2/@0.8` = 60 %. Example: `note("[a3@1.15 c4@0.85] [e4@1.15 c4@0.85] ...")`. Swing only the guest part's 16ths;
  never shift the downbeat.
- **Accent and ghost velocity map.** Use a 16-step gain pattern such as
  `gain("0.9 0.45 0.7 0.5 0.85 0.45 0.7 0.55 0.9 0.45 0.7 0.5 0.85 0.5 0.75 0.6")`. Downbeats ~.85–.9, ghosts .45–.55
  (≈ velocity 60–70 of 127, matching the "< 70" ghost rule), and small non-repeating deviations stand in for ±10 humanize.
  Because `velocity` does not touch the filter in superdough, pair it with a matching
  `lpenv("4 1.5 3 1.5 4 1.5 3 2 ...")` so accented steps are also brighter.
- **Random ghost drops.** `?0.2`–`?0.3` on ghost-only steps (e.g. `"a2 [~ a2?0.3] a2 [~ a3?0.25]"`) varies repetitions
  without changing the downbeats.
- **8–16-bar filter build.** `lpf("<300 350 420 500 600 720 860 1030 1240 1490 1790 2150 2580 3100 3700 4400>")` is a
  16-bar exponential ramp (×1.2 per bar). The 8-bar version is `<300 400 520 680 880 1150 1500 2000>`.
  - Pair it with a rising `lpenv("<1 1 1.5 1.5 2 2 2.5 3>")` and `room("<0.2 0.2 0.25 0.3 0.35 0.4 0.45 0.5>")`.
    `room` is per-orbit; changing the level is fine, but keep `size` constant.
  - The validator's `cycles: 4` window only scores the first 4 bars of such a build.
- **LFO-like motion without LFO controls.** Superdough 1.2.6 ignores `lprate`/`lpsync`, and signals cannot be expressed
  in the dialect. Use a 16-step cutoff pattern instead, e.g. `lpf("800 950 1100 1250 1400 1250 1100 950 ...")`, which
  is an LFO at 1/2 bar sampled per 16th.
  - Tempo-related rates producers use (common practice, **unverified**): 1/4 or 1/8 for "wobble", 1 bar or 2 bars for
    pad sweeps, 4–16 bars for slow pad filter drift.
- **Filter before amp.** With `lpattack` ≤ amp `attack` (e.g. `lpattack(0.003)`, `attack(0.008)`), brightness leads the volume.
- **Pluck numbers for superdough.** Use `lpdecay(0.02-0.06)` for "tight" and `0.1-0.2` for "pluck", with `decay` about 1.5× `lpdecay`.

### Gaps
- I found no source with numeric LFO rates for house/techno pad filter motion; the rates above are common practice, **unverified**.
- Swing percentages come from drum contexts (MPC). I found nothing that quantifies swing for synth stabs specifically.

---

## 3. Processing chain per role: saturation, EQ, compression, sidechain, delay, reverb, width

### Takeaway
- **High-pass everything that isn't bass:** ~130–150 Hz for the bass mid layer, ~250 Hz for chords, and ~30 Hz plus a low-pass at 80–190 Hz for the sub.
- **Saturate the mid layer, not the sub** (or only lightly, ~35 % wet).
- **Compress a few dB.**
- **Pump everything against the kick** with near-0 attack and a 50–250 ms release.
- **Delay:** 1/8 or dotted-1/8 ping-pong with a high-passed return.
- **Reverb:** 2–3 s for chords with 10–20 ms pre-delay on leads, and none on kick or sub.
- **Width:** above ~2 kHz only.

### Cited Findings
**Saturation and EQ**
- Bass mid layer chain: soft-clip, tape saturation, EQ cut up to ~130 Hz and above 3 kHz, then 2–3 dB of compression.
  Chords: tube distortion **inside** the synth (after the filter), then EQ low cut 250 Hz, then ~5 dB compression on
  filter peaks.
  — [Attack Magazine, Layering Synths](https://www.attackmagazine.com/technique/synth-secrets/layering-synths/)
- On the sub, overdrive at ~35 % wet after an 80 Hz low-pass keeps the low end intact.
  — [Attack Magazine, Warehouse Rolling Techno Bass](https://www.attackmagazine.com/technique/tutorials/warehouse-rolling-techno-bass/)
- In acid, a **high resonance peak driven into distortion** produces the classic driven tone as the cutoff sweeps.
  A Sylenth recipe lowers the cutoff and pushes **resonance to ~3.25 and drive to ~2.0**.
  — [Attack Magazine, Acid with Diva](https://www.attackmagazine.com/technique/synth-secrets/acid-synth-uhe-diva/); [Attack Magazine, TB-303 acid arpeggiator (Sylenth)](https://www.attackmagazine.com/technique/synth-secrets/tb-303-acid-arpeggiator-sylenth/) (search snippets)

**Sidechain**
- MusicRadar's house pad example uses release **5 ms**, attack **20 ms**, ratio **6:1**. The figures look possibly
  swapped; **verify**. — [MusicRadar, sidechain compression](https://musicradar.com/how-to/sidechain-compression-mix)
- Other starting points:
  - attack ~0.1 ms, with a release tuned to the kick of **~67 ms**;
  - ratios **8:1–12:1** with a very fast attack;
  - for subtle headroom rather than pump, attack **1–10 ms** and release **200–400 ms** (≈ kick length);
  - quarter-note release = 60000/BPM.
  — [zZounds blog](https://blog.zzounds.com/2018/05/31/side-chain-compression/); [Sonarworks](https://www.sonarworks.com/blog/learn/sidechain-compression); [Sample Focus](https://blog.samplefocus.com/blog/what-is-sidechain-compression-and-how-to-use-it) (search snippets)
- Sidechaining reverb and delay returns:
  - Reverb bus compressor at **4:1, 0 ms attack, 40–50 ms release**, keyed from the lead.
  - Kick-keyed pumping on a delay return: threshold ~**−33 dB, 0 ms attack, ~50 ms release**.
  — [MusicRadar, How to sidechain reverb and delay](https://www.musicradar.com/tuition/tech/how-to-sidechain-reverb-and-delay-624916)
- Delay return ducked by the dry chord (fast attack and release) so the echoes bloom between hits; LFO-Tool kick ducking after that.
  — [Attack Magazine, Layering Synths](https://www.attackmagazine.com/technique/synth-secrets/layering-synths/)

**Delay**
- 1/8 L/R ping-pong with high crossfeed and a swept-up low cut on the return.
  — [Attack Magazine, Layering Synths](https://www.attackmagazine.com/technique/synth-secrets/layering-synths/)
- For plucks, a tempo-synced **dotted 1/8** is the most common choice; ping-pong 1/8 with an HP filter is the alternative.
  — [ADSR Sounds / Avid pluck tutorials via search](https://www.adsrsounds.com/serum-tutorials/progressive-house-pluck-serum/) (search snippet)

**Reverb**
- Chords: Valhalla VintageVerb at **2.88 s decay**, with reduced HF damping and a high cut for a darker tail.
  — [Attack Magazine, Layering Synths](https://www.attackmagazine.com/technique/synth-secrets/layering-synths/)
- Leave the kick dry, because low-frequency reverb muddies the mix. If bass gets reverb, high-pass the reverb and optionally
  duck it with the dry bass. — [Attack Magazine, How to use reverb in a mix](https://www.attackmagazine.com/technique/tutorials/how-to-use-reverb-in-a-mix/)
- Pre-delay of at least **10–20 ms** on reverb for lead elements; longer pre-delays should be tempo-matched.
  — [Plugin Boutique, 5 Pro Tips for Mixing Reverb](https://www.pluginboutique.com/articles/1789-5-Pro-Tips-for-Mixing-Reverb) (search snippet)

**Bus processing and width**
- Group glue compression: **~4 dB gain reduction, 2:1**, medium attack and release. Width only above 2 kHz.
  — [Attack Magazine, Layering Synths](https://www.attackmagazine.com/technique/synth-secrets/layering-synths/)

**Techno rumble**
- Kick (or bass) → long reverb → **LP below ~250–300 Hz**, HP ~30 Hz, high-shelf cut above 150–200 Hz, then ducked
  on every kick.
  — [Production Music Live, rumbling techno kick](https://www.productionmusiclive.com/blogs/news/6-steps-to-create-that-rumbling-techno-kick-you-love-with-johannes-menzel); [Bonedo, Rumble & Rattle](https://www.bonedo.de/artikel/bass-drum-rumble-rattle-for-techno); [Futureproof Music School](https://futureproofmusicschool.com/blog/making-hard-techno-a-path-to-unique-sound-design) (search snippets)

### Inferences
Per-role chain templates for superdough 1.2.6. Order inside superdough is fixed per voice:
oscillator → filters → amp env → shape/distort/crush → pan → orbit sends.
So **"saturation after the filter" is the only order available**. Pre-filter drive exists only as `ftype("ladder").drive(...)`.

| role | hpf | lpf / env | saturation | space (own orbit) | width |
|---|---|---|---|---|---|
| sub | none (or 30) | `lpf(100-180)` | `shape(0.1-0.25)` max | no room/delay | `pan(0.5)` |
| bass mid | 120–150 | `lpf("400-900:2-4:2-3")` | `shape(0.2-0.35)` or `distort` ≤1.5 | none, or tiny delay | mono |
| chords/stabs | 200–300 | `lpf("500-900:3-6:3-5")` | light `shape(0.1-0.2)` | room .25–.35, size 2.5–3 (≈2.9 s Attack), delay .2–.3 dotted 1/8 | detuned copy panned .2/.8 |
| pads | 150–250 | `lpf(800-2000)` + slow `<>` steps | none | room .4–.6, size 4–6 | 2 lanes panned 0.15/0.85 |
| plucks/arps | 200–400 | `lpf("300-500:5-8:4-6")`, lpdecay .02–.12 | none | delay .3–.45 dotted 1/8, fb .35–.5; room .2–.3 | `pan("0.35 0.65")` alternate |
| lead | 200–300 | `lpf("2500-4000:1-2:1")` | `shape(0.1)` optional | delay .25–.35 with `delaysync` 3/16 or 1/8; room .3–.5 | supersaw spread .6–.8 |
| acid | 80–100 | ladder `lpf(250-500)`, `lpq` 10–18, `lpenv` 2–6 | `distort(1-1.5)` after | small delay .15 | mono |
| vocal chop | 200–300 | `bpf` 800–2500 optional | none | delay .3 + room .4 | small pan steps |

- **Sidechain approximation.** `duckorbit` is a no-op offline (sounds_synthesis.md §3) and `tremolo` is not whitelisted.
  With today's whitelist:
  1. **Avoid the kick rhythmically.** House offbeat stabs `struct("~ x ~ x ~ x ~ x")`, and basses with the first 16th of
     each beat empty (Attack warehouse bass).
  2. **For sustained pads, write the pump as gain steps on a 16th-retriggered chord:**
     `note(CHORD).segment(16).attack(0.01).sustain(1).release(0.06).gain("0.25 0.55 0.8 0.95")`. The four steps per beat
     give an ~0 → full rise in ~120–360 ms. **Not rendered**; it may click, so check it.
  3. **Best fix:** whitelist `tremolosync(4)`, `tremolodepth(0.6-0.8)`, `tremoloshape("ramp")`, which was verified to rise
     like a pump in sounds_synthesis.md (5b). A release of ~50–70 ms (zZounds/MusicRadar) matches the quick dip of `ramp`.
- **Ping-pong approximation.** superdough's delay is not ping-pong. Two options:
  - Add one echo lane: the same notes shifted one 1/8 step by prefixing mini rests (e.g. `"~ [a4 ~]"`-style rotation), `pan(0.85)`, `gain` ×0.5, `hpf(400)`.
  - Use the dry lane `pan(0.3)` with orbit delay feedback .35.
  This costs a lane but sounds wider than a centred mono delay.
- **Pre-delay approximation.** superdough has no pre-delay. Leads and plucks can instead use a separate quiet "send" lane
  that copies the part 1/32 (≈60 ms at 124 BPM) or 1/64 later. That lane gets `hpf(500)`, `gain` ×0.3, and its own
  orbit with `room(0.9).size(4)`; the dry lane gets `room(0)`. **Idea only, not rendered.**
- **High-passed reverb and delay returns** are not possible per orbit, so put the `hpf` on the lane that feeds the orbit. Every lane on a reverb orbit should be high-passed ≥ 200 Hz.
- **Rumble (techno guest part).** Use a separate lane on its own orbit: a sine at the bass root with a long `release(0.6)`,
  `lpf(250)`, `room(0.8).size(6)`, `gain(0.25)`, and the kick-position steps silent (`"~ a1 a1 a1"` per beat). The room
  is not low-passed per orbit, but the input is.

### Gaps
- No primary source with **numeric reverb sizes per role** besides Attack's 2.88 s chord reverb, or pre-delay per role beyond "10–20 ms for leads".
- The MusicRadar 5 ms release / 20 ms attack figure may be a transcription or snippet artifact; I could not fetch the full article.
- I could not confirm superdough's internal per-voice effect order from docs here; the order above is from prior source reading and should be re-checked in `superdough.mjs` if it matters.

---

## 4. Genre specifics: house organ / M1 piano / Korg stabs, deep-house chords, techno rumble bass, acid 303, progressive plucks and arps

### Takeaway
- **House organ:** a sustained organ with its attack truncated, i.e. percussive. Recreate it with a couple of oscillators
  plus noise and some drive.
- **Deep house:** minor 7th/9th/11th voicings without the root, syncopated off-beat placement, chorused keys.
- **Rave/Korg stab:** a minor triad with octave-doubled root, bitcrushed, through a ~400 Hz LP with a long envelope.
- **Acid:**
  - the slide is a constant-time glide of ~60 ms;
  - accent raises level, cutoff and resonance and shortens or changes the filter decay;
  - the patch is high resonance into distortion.
- **Progressive:** detuned-saw plucks with 20–60 ms filter decays and a dotted-1/8 delay.

### Cited Findings
**House organ (M1 / DSS-1)**
- Korg's Jack Hotop (quoted in an Attack comment thread) says the house organ was first made for the DSS-1 library and is
  the same sound as the M1's: "the beginning attack was truncated off of the organ".
  — [Attack Magazine, M1-style organ bass in Massive (Marc Adamo)](https://www.attackmagazine.com/?p=6993) (via search snippet; comment claims, **unverified**)
- To recreate the M1 organ "all you really need are a couple of oscillators and a noise generator", plus distortion or
  overdrive for grit. — [MusicRadar, Korg M1 organ bass](https://www.musicradar.com/tuition/tech/how-to-create-a-korg-m1-style-organ-bass-sound-642650) (search snippet; full page not retrievable)

**Deep-house chords**
- Voicings: Cm7 without the root, Gm7 in third inversion; 11ths and 9ths as colour; rhythm skips the main downbeats and
  stresses off-beat 16ths; mixed short and sustained hits create call-and-response; bar 8 varies the rhythm.
  — [Attack Magazine, Levelling Up Your Chord Stabs](https://www.attackmagazine.com/technique/passing-notes/levelling-up-your-chord-stabs/)
- A sampled chord stab on the **first offbeat of each bar**, pitched to follow the progression.
  — [Attack Magazine, Dusted Deep House](https://www.attackmagazine.com/technique/beat-dissected/dusted-deep-house/) (search snippet)

**Korg/rave stab**
- E-minor triad with E3+E2 doubling; +12 osc with phase modulation; 8–12-bit crush; strong compression; 12 dB LP at ~411 Hz
  with a ~1.5 s filter release. — [Attack Magazine, Landlord stab](https://www.attackmagazine.com/technique/synth-secrets/make-rave-stabs-like-the-landlord-stab/)

**Acid 303**
- **Slide.** The stock 303 slide comes from a 220 nF capacitor with a ~22 ms time constant, so it **completes in about 60 ms
  regardless of interval** (constant time, not constant rate). — [synth-diy mailing list, TB303 Slide](https://synth-diy.org/pipermail/synth-diy/2012-May/140040.html) (search snippet; page blocked on fetch)
- The Devil Fish mod makes the slide up to 5× longer; its soft attack ranges 0.3–30 ms, versus ~3 ms on the stock 303.
  — [MATRIXSYNTH, TB-303 Devil Fish](https://www.matrixsynth.com/2008/08/roland-tb-303-devil-fish.html) (search snippet)
- **Accent.** Sources disagree on the mechanism:
  - It raises volume and opens the filter further.
  - It acts like a small resonance-focused envelope that raises resonance and lengthens the envelope.
  - Per Robin Whittle's account, it **shortens the filter-envelope decay to minimum**.
  - It briefly lifts both cutoff and resonance above the panel settings.
  — [Elektronauts, What exactly does Accent do?](https://www.elektronauts.com/t/what-exactly-does-accent-do/5788); [Learning Modular, Patch ideas from the TB-303](https://www.patreon.com/posts/patch-ideas-i-tb-41917616); [Computer Music via PressReader](https://www.pressreader.com/australia/computer-music/20160615/283167197831659) (all search snippets)
- Env Mod sets the depth of the filter envelope and Decay its length; short decay gives a stab, long decay a bloom.
  High resonance self-oscillates into the "scream".
  — [Roland TB-303 Graphic Tour](https://rolandcloud.com/getmedia/efd3c795-f690-4e88-bd6b-c613af4b31ce/TB-303-Graphic-Tour.pdf); [DP-303 design notes](https://tnn1t1s.github.io/day-303/about.html) (search snippets)
- Acid setup used by Attack: diode filter, cutoff at halfway, a little resonance; "Acid" mode ties resonance to cutoff;
  ABL2 at 129 BPM, then cutoff/resonance modulation, then EQ and saturation.
  — [Attack Magazine, How to make an acid house bassline](https://www.attackmagazine.com/technique/tutorials/how-to-make-an-acid-house-bassline/) (search snippet)

**Progressive plucks and arps**
- Detuned saws into a 4-pole LP with a short attack/decay envelope.
  — [ADSR Sounds](https://www.adsrsounds.com/ni-massive-tutorials/progressive-house-pluck-synth/)
- ~20 ms decay for tight plucks.
  — [Cymatics](https://cymatics.fm/blogs/production/creating-plucks-xfer-serum)
- Dotted-1/8 synced delay "turns a simple pluck pattern into a rolling, rhythmic hook".
  — [ADSR Sounds Serum pluck](https://www.adsrsounds.com/serum-tutorials/progressive-house-pluck-serum/) (search snippets)

**Techno rumble bass**
- See §3. Attack's warehouse bass: sub LP 80 Hz with 35 % overdrive; bassline HP 65 / LP 350 Hz with the first 16th empty;
  a 1/16-delayed kick copy as a wide percussive top. — [Attack Magazine, Warehouse Rolling Techno Bass](https://www.attackmagazine.com/technique/tutorials/warehouse-rolling-techno-bass/)

### Inferences
Dialect recipes, all **unrendered**, each built from the cited facts.

**G1 — M1-style house organ, 3 lanes**
- **Body:** `note(CHORD).struct("~ x ~ x ~ x ~ x").s("square").n(7).hpf(150).lpf(3000).attack(0.001).decay(0.18).sustain(0.15).release(0.05).gain(0.35)`.
  The "truncated attack" means no organ swell, just an instant percussive start.
- **Octave-down saw for weight:** `s("sawtooth")` with notes −12, `lpf(900)`, `gain(0.15)`.
- **Key click:** `s("white")` on the same struct, `hpf(4000).decay(0.015).sustain(0).gain(0.05)`.
- Bus: `shape(0.15)`, `room(0.25).size(2)`, `delay(0.2)`.

**G2 — deep-house chord**
- Voicing: `<[eb3,g3,bb3,d4] [ab3,c4,eb4,g4]>`, i.e. Cm9 without the root, then Fm9 without the root.
- Rhythm `struct("~ x ~ [~ x] ~ ~ x ~")`, which skips beats 1 and 4.
- Layers: L2 body + detuned copy + octave pluck; the electric-piano character comes from `fm(1.5).fmh(1).fmdecay(0.3)` on a sine lane at `gain(0.2)`.
- Every 8th bar uses an alternate struct via `<...>`.

**G3 — rave/Korg stab**
- Notes: `[e2,e3,e4,g4,b4]` on one or two hits per bar.
- Body: `s("sawtooth").lpf("420:2:3").lprelease(1.5).lpsustain(0.6).decay(0.6).sustain(0.3).release(0.4).crush(10).shape(0.3).hpf(80)`.
  `crush` is a worklet, so do not use it on 16ths.
- Second lane: the same notes +12 on `s("square")`, `hpf(600)`, `gain` ×0.3. This stands in for the +12 PM oscillator.

**G4 — acid, 303-like**

```
note("a1 a1 a2 a1 c2 a1 g1 a2 a1 a1 e2 a1 a1 g2 a1 c2")
  .s("sawtooth").ftype("ladder").lpf("<300 360 430 520>")   // per-bar cutoff ramp
  .lpq(16).lpenv("2 2 5 2 2 2 5 2 2 2 5 2 2 5 2 3")         // accent steps: env up
  .lpdecay("0.2 0.2 0.08 0.2 0.2 0.2 0.08 0.2 0.2 0.2 0.08 0.2 0.2 0.08 0.2 0.15")  // accent: shorter decay (Whittle account)
  .gain("0.6 0.6 0.9 0.6 0.6 0.6 0.9 0.6 0.6 0.6 0.9 0.6 0.6 0.9 0.6 0.7")
  .attack(0.003).decay(0.2).sustain(0.5).release(0.03).distort("1.3:0.5:soft").hpf(60).orbit(6)
```
- **Slides:** on slid steps use `clip(1.1)`, which overlaps into the next note. On the target note set
  `penv(<prev-minus-this semitones>)` with `pattack(0.06)` and `panchor(1)`, so the pitch moves from the previous note to
  the target in 60 ms (the 303's constant-time slide).
  - Because `penv` is per-lane and not per-step, slides need a separate lane carrying only the slid notes, or a step
    pattern `penv("0 0 -12 0 ...")` (step patterns on controls work, as with `gain`).
  - **Unverified**: check that `panchor(1)` makes `penv` start at the offset and end at 0 in a render.
- `ftype`/`distort` need whitelisting. Without them, use `lpq(12)`, the default 12db filter, and `shape(0.4)`.

**G5 — progressive pluck arp**
- Two lanes of `s("sawtooth")`: the second on fractional notes +0.1 (10 c), panned 0.3/0.7.
- Filter: `lpf("400:6:5").lpattack(0.002).lpdecay(0.05)`.
- Amp: `attack(0.004).decay(0.12).sustain(0).release(0.05)` (filter faster than amp).
- Space: `hpf(250)`, `delay("0.4:0.1875:0.45")` (dotted 1/8), `room(0.3).size(3)`.
- Over 8 bars: `lpdecay("<0.03 0.03 0.04 0.05 0.06 0.08 0.1 0.12>")` opens the pluck gradually, a standard progressive build.

### Gaps
- I could not retrieve full MusicRadar M1 organ or "Show Me Love" organ recipes (paywall/truncation). No exact oscillator settings were found for the M1 organ.
- **303 control ranges.** I found no reliable source giving the real 303 cutoff range in Hz or the accent-sweep timing in ms.
  Robin Whittle's Devil Fish documentation is the likely primary source but was not fetched.
- The 60 ms slide figure is from a mailing-list circuit analysis seen only as a search snippet.
- No M1 piano source was found in this pass (sounds_samples.md already flags the lack of a free Rhodes/M1 piano multisample).

---

## 5. What this means for the generator (program-level rules)

### Takeaway
"Too simple" is mostly **one lane = one oscillator, unfiltered, no band ownership**. The cheapest big win inside the current
whitelist is to have the generator expand each role into a fixed 2–4-lane template. Each template has:
1. a body lane;
2. a detuned or octave lane panned off-centre;
3. a transient/noise lane;
4. per-lane `hpf`/`lpf` band ownership;
5. a role-specific orbit for space.

The next win is whitelisting `unison/detune/spread`, `tremolosync/tremolodepth/tremoloshape`, `distort`, `ftype`, and fixing `transpose`.

### Cited Findings
- Layer stacks with band splits: [Attack Magazine, Layering Synths](https://www.attackmagazine.com/technique/synth-secrets/layering-synths/); [Attack Magazine, Warehouse Rolling Techno Bass](https://www.attackmagazine.com/technique/tutorials/warehouse-rolling-techno-bass/); [Audiotent](https://www.audiotent.com/blogs/production-tips/mixing-kick-and-bass)
- Supersaw voice count and detune: [KVR forum](https://www.kvraudio.com/forum/viewtopic.php?p=4644620)
- Groove numbers: [Unison](https://unison.audio/how-to-humanize-midi/); [Sounds Heavy](https://soundsheavy.pages.dev/drums-percussion/programming-realistic-drums)
- Dialect and engine facts (`transpose` broken, `octave` ignored, fractional notes work, no pre-delay/ping-pong, `velocity`
  is gain-only, `nudge` sampler-only, swing via `@` weights): local code checks of `js/dialect.mjs`,
  `js/node_modules/superdough/{superdough,helpers,synth,sampler}.mjs` 1.2.6 and `@strudel/core` 1.2.6 (this session).

### Inferences
Concrete changes, in order of value per effort:
1. **Fix `transpose`.** Either import `@strudel/tonal`, or implement it in `buildLane` as `pat.add(note(x))` /
   `withValue(v => ({...v, note: midi(v.note) + x}))`. Then octave and detune layers become `.transpose(12)` and `.transpose(0.1)`,
   instead of rewriting note strings. Drop `octave` from the whitelist, or implement it the same way, since it is silently ignored.
2. **Template expansion in the generator** (`deckc/src/compose.mjs` STYLES/SYNTHS), with band rules enforced as clamps:
   - sub lane `lpf` ≤ 200 and no room/delay;
   - every non-sub lane `hpf` ≥ 120 (bass mid), ≥ 200 (chords/pads/plucks/leads);
   - noise lanes `hpf` ≥ 3000 and gain ≤ 0.08;
   - pan ≠ .5 only on lanes whose `hpf` ≥ 200.
3. **Default space per role** (fixed per orbit, never patterned):
   - bass orbit dry;
   - chords room .3/size 3 + delay .25;
   - pads room .5/size 5;
   - plucks delay .4 fb .45 + room .25;
   - lead delay .3 + room .4.
4. **Groove layer.** Default to 55–57.5 % swing on guest 16ths via `@1.1/@0.9`–`@1.15/@0.85`, a 16-step accent gain mask
   (.85–.9 / .45–.55), and matching `lpenv` accents for filter-based parts.
5. **Build automation.** For 8- and 16-bar sections, emit `<…>` cutoff ramps (×1.2 per bar) on chords, pads and plucks.
   Emit `lpdecay` ramps on plucks.
6. **Whitelist additions** (re-stating sounds_synthesis.md, prioritised for layering): `unison detune spread` (clamp
   unison ≤ 7, detune ≤ 1), `tremolosync tremolodepth tremoloshape` (offline-safe pump), `distort` (≤ 1.5), `ftype` + `drive` (acid).
7. **Render-check every template** with peak, rms and band-energy metrics before adopting it. None of the recipes in this file was rendered.

### Gaps
- No A/B evidence yet that the multi-lane templates sound "finished" next to a real DJ track inside superdough.
  A render-plus-listening pass, or a spectral comparison against the track, is needed.
- Lane cost: each extra lane multiplies voices. Native-node lanes are cheap (sounds_synthesis.md §4), but 4 lanes × 16ths × chords may hit the 256 events/cycle limit or the 128-voice polyphony cap.
