# Richer synth sounds in Strudel / superdough (house, techno, progressive)

Researched 2026-11-06. Sources: Strudel master (codeberg.org/uzu/strudel @530e963, 2026-11-01),
`website/src/pages/learn/{synths,effects,lfo}.mdx`, `packages/core/controls.mjs` JSDoc,
`packages/superdough/*.mjs`, plus the npm tarballs for superdough 1.2.6, 1.2.7 and 1.3.0. Everything
marked **verified** was rendered through this project's own offline pipeline (a copy of `js/render.mjs`
with a larger whitelist, node-web-audio-api, superdough 1.2.6). Harness:
`<scratch folder>`
(`mk.py` builds the recipe JSONL, `bench.jsonl` holds the cost micro-benchmarks, `env.py` analyses the WAVs).

## 0. Versions matter more than expected

| package | in this project (`js/package.json`) | latest on npm | notes |
|---|---|---|---|
| `superdough` | **1.2.6** (2025-10-27, pinned) | 1.3.0 (2026-01-18) | 1.2.7 and 1.3.0 are almost the same; master = 1.3.0 + kabelsalat `workletSrc` |
| `@strudel/core` | 1.2.6 (2026-01-17) | 1.2.6 | this core is **newer than** superdough 1.2.6 |

So core 1.2.6 accepts controls (`lprate`, `lpsync`, `lpdepth`, `partials`, `phases`, `transient`,
`fmi12`-style FM matrix, `.lfo({...})`, `.env({...})`, `bus`) that **superdough 1.2.6 ignores without
warning**. The table marks each control with the first superdough version that actually *does* something with it.
`chorus` is registered in core but no superdough version implements it (it is only sent to SuperDirt over OSC), so it does nothing here.

## 1. Control reference

"≥1.2.6" = works in this project today. Ranges are practical ones, not hard limits. "Colon form" means
one whitelisted method can set several fields: `lpf("800:12:4")` gives `{cutoff:800, resonance:12, lpenv:4}`.
This was **verified**: the dialect passes the string through `mini()` and core spreads the list over the
control's sub-names.

### Filters
| control (aliases) | what it does | typical range | version |
|---|---|---|---|
| `lpf` (`cutoff`,`lp`) colon `freq:q:env` | low-pass cutoff in Hz | 150–6000 | ≥1.2.6 |
| `lpq` (`resonance`) | Q of the filter. For the 12db biquad, WebAudio reads Q **in dB**, so 20 means a +20 dB peak | 0–15 (biquad), 5–25 (ladder) | ≥1.2.6 |
| `hpf` (`hcutoff`) colon `freq:q:env`, `hpq` | high-pass filter | 80–400 for clearing mud | ≥1.2.6 |
| `bpf` (`bandf`), `bpq` | band-pass filter | 300–3000, q 1–8 | ≥1.2.6 |
| `lpenv` (`lpe`) | filter-envelope depth in **octaves** above the cutoff (negative flips it) | 1–6 (stabs/acid), 0.5–2 (pads) | ≥1.2.6 |
| `lpattack` `lpdecay` `lpsustain` `lprelease` (`lpa lpd lps lpr`) | filter-envelope ADSR in seconds; `lps` is 0–1. Setting any of them turns the env on; if only `lpenv` is set the default is A .005, D .14, S 0, R .1 | a .001–.5, d .05–.4 | ≥1.2.6 |
| `hpenv`, `hpattack`… `bpenv`, `bpattack`… | same envelope for HP and BP | | ≥1.2.6 |
| `fanchor` | where the envelope sits: 0 = sweeps only upward from the cutoff (default), .5 = both ways, 1 = downward | 0–1 | ≥1.2.6 |
| `ftype` | `12db` (biquad, default) / `ladder` (Moog-style JS worklet, saturating) / `24db` (two biquads in series) | | ≥1.2.6 |
| `drive` | input drive of the ladder filter only (default 0.69) | 0.5–3 | ≥1.2.6 |
| `vowel` | 5-band formant filter: `a e i o u ae aa oe ue y uh un en an on` | | ≥1.2.6 |
| `djf` | per-orbit DJ filter: below 0.5 is LP, above is HP | 0.2–0.8 | ≥1.2.6 |
| `lprate`/`lpsync`/`lpdepth`/`lpshape`/`lpdc`/`lpskew` (and `hp*`, `bp*`) | built-in filter LFO, in Hz or synced per cycle | rate .1–8, depth 0–2 | **≥1.2.7** (ignored on 1.2.6) |

### Oscillators and synthesis
| control | what it does | typical range | version |
|---|---|---|---|
| `s("sawtooth"/"square"/"triangle"/"sine")` (`saw sqr tri sin`) | native OscillatorNode. Internal gain is 0.3 | | ≥1.2.6 |
| `s("supersaw")` + `unison`, `detune` (`det`), `spread` | JS worklet with band-limited saws. `detune` is the **total** spread in semitones (default .18, so ±9 cents); `unison` is the voice count (default 5, clamped 1–100); `spread` is stereo width 0–1 (default .6). Output is scaled by 1/√voices. Voice phases are random, so **renders are not bit-reproducible** | unison 3–7, detune .1–.5, spread .5–1 | ≥1.2.6 |
| `s("pulse")` + `pw` colon `pw:pwrate:pwsweep` | pulse width, plus a PWM LFO in Hz and its depth | pw .1–.9, pwrate .1–4, pwsweep .1–.4 | ≥1.2.6 |
| `s("white"/"pink"/"brown"/"crackle")`, `density` | noise sources (hats, risers, air) | | ≥1.2.6 |
| `noise` | mixes pink noise into any oscillator | .05–.4 | ≥1.2.6 |
| `n` on basic waves | **on superdough 1.2.6, `n` = number of additive partials** (`saw`/`square`/`triangle`). On `supersaw`, `n` is used as `detune` if `detune` is unset. Watch out if `.n()` is meant as a scale degree | 4–16 partials gives a darker, organ-like tone | ≥1.2.6 |
| `partials`, `phases`, `s("user")` | list of harmonic amplitudes and phases | needs a JS array, so the dialect cannot express it | ≥1.2.7 |
| `fm` (`fmi`) colon `index:harmonicity`, `fmh` | single-operator FM: modulator = carrier × `fmh`, depth = index × modulator freq | index 1–10; fmh 1/2/3 harmonic, 1.41/3.5/7.1 bell-like | ≥1.2.6 |
| `fmattack` `fmdecay` `fmsustain` `fmrelease`, `fmenv` (`exp`/`lin`), `fmwave` (`sine square sawtooth triangle` or a noise type) | envelope on the FM index; this is what makes plucks and bells | fmdecay .05–.8, fmsustain 0–.3 | ≥1.2.6 |
| `fm2…fm8`, `fmh2…`, `fmi12` (operator matrix) | 8-operator FM | | ≥1.2.7 |
| `penv` `pattack` `pdecay` `prelease` `panchor` `pcurve` | pitch envelope in semitones (`penv` alone means attack .2). Useful for kick-like subs, zaps and pseudo-slides | penv ±1–24, pdecay .01–.1 | ≥1.2.6 |
| `vib` colon `rate:depth`, `vibmod` | vibrato rate in Hz and depth in semitones | vib 4–6, vibmod .05–.3 | ≥1.2.6 |
| `wt_*` samples + `wt`, `wtenv`, `wtattack…`, `wtrate`/`wtsync`/`wtdepth`, `warp`, `warpmode`, `unison`/`detune`/`spread` | wavetable oscillator (any sample registered with the `wt_` prefix, e.g. AKWF via `samples('bubo:waveforms')`). Also supports unison | | ≥1.2.6 (needs wt sample files) |
| `s("sbd")` + `decay`, `pdecay`, `penv` | synth kick | | ≥1.2.6 |
| `z_sawtooth`, `z_*` | ZZFX synth (its own params) | | ≥1.2.6 |

### Amplitude and dynamics
| control | what it does | typical range | version |
|---|---|---|---|
| `attack decay sustain release` | amplitude ADSR. If only some are given, superdough infers the rest (e.g. `decay` alone means sustain 0) | | ≥1.2.6 |
| `gain`, `velocity` | multiply pre-filter. Default gain .8, and the gain curve is linear | | ≥1.2.6 |
| `postgain` | gain after all per-voice FX | .5–1.5 | ≥1.2.6 |
| `compressor` colon `thr:ratio:knee:att:rel` | per-voice DynamicsCompressor | `"-20:4:10:.005:.1"` | ≥1.2.6 |
| `tremolo` colon `rate:depth:skew:phase`, `tremolosync` (cycles), `tremolodepth`, `tremoloshape` (`tri sine ramp saw square`), `tremoloskew`, `tremolophase` | amplitude LFO (worklet) | sync 4 or 8, depth .5–.9 | ≥1.2.6 |
| `duckorbit` (`duck`), `duckattack`, `duckdepth`, `duckonset` | sidechain: a trigger on this lane ducks the whole output of the target orbit(s); `"2:3"` targets several | attack .1–.3, depth .5–.9 | ≥1.2.6, **but no-op offline (see §3)** |
| `transient` colon `attack:sustain` | transient shaper, −1 to 1 | | ≥1.2.7 |

### Distortion and colour
| control | what it does | typical range | version |
|---|---|---|---|
| `shape` | soft waveshaper (marked deprecated in favour of `distort`); peaks at about 1.8× at .4 | .1–.5 | ≥1.2.6 |
| `distort` (`dist`) colon `amt:postgain:type`, `distorttype` (`scurve soft hard cubic diode asym fold sinefold chebyshev`) | waveshaping distortion; **loud** (distort 2 tripled the peak) | .5–3, postgain .4–.7 | ≥1.2.6 |
| `crush` | bit depth 1–16 | 6–12 | ≥1.2.6 |
| `coarse` | sample-rate reduction; per the docs it only works in Chromium | 2–8 | ≥1.2.6 |
| `phaser` (`phaserrate`, `ph`) colon `rate:depth:center:sweep`, `phaserdepth`, `phasercenter`, `phasersweep` | 2-stage notch phaser with an LFO | rate .1–2, depth .3–.7 | ≥1.2.6 |
| `pan` | stereo position 0–1 | | ≥1.2.6 |
| `chorus` | registered, **not implemented** in superdough | – | none |

### Global (per-orbit) effects
These are shared by **every** lane on the same `orbit`; the last event's parameters win.

| control | what it does | typical range | version |
|---|---|---|---|
| `orbit` (`o`) | picks the FX bus (default 1). Give each part its own orbit when the parts need different reverb or delay | 1–8 | ≥1.2.6 |
| `room`, `size` (`roomsize`,`sz`,`rsize`) | reverb send level, and decay length in seconds (0–10) | room .2–.6, size 2–8 | ≥1.2.6 |
| `roomlp` (`rlp`), `roomdim` (`rdim`), `roomfade` (`rfade`) | brightness at the start of the reverb tail, brightness at −60 dB, fade-in. **Each change regenerates the IR**, so keep them constant | rlp 4000–10000, rdim 400–2000 | ≥1.2.6 |
| `ir` (`iresponse`), `irspeed`, `irbegin` | convolution reverb using a loaded sample as the IR | | ≥1.2.6 |
| `delay` colon `wet:time:feedback`, `delaytime` (seconds), `delayfeedback` (clamped at .98), **`delaysync`** (cycles; default 3/16) | feedback delay. `delaytime` is in **seconds**, so it does not follow the tempo. With no `delaytime`, delay is tempo-synced to 3/16 of a cycle (a dotted 1/8) | wet .2–.5, fb .3–.65 | ≥1.2.6 |
| `dry` | dry level next to room/delay | | ≥1.2.6 |
| signals `sine.range(a,b).slow(n)`, `.lfo({...})`, `.env({...})`, `bmod`, `bus` | pattern-rate signals / audio-rate modulators | need JS objects or expressions, **so the dialect cannot express them** | signals: core; lfo/env/bus ≥1.2.7 |

The dialect does allow mini-notation stepping instead of signals, e.g. `lpf("<400 700 1100 1600>")`
(one value per bar) or `lpf("400 600 900 1300")` (four steps per bar).

## 2. Recipes (all rendered at 124 BPM through superdough 1.2.6; numbers are rms / peak)

The baseline that sounds "too simple", `note("<[a3,c4,e4]@4>").s("sawtooth").clip(1).room(0.3).gain(0.5)`,
rendered at rms .107 and peak .47. The `gain` values below are starting points; normalize per lane afterwards.

1. **Supersaw trance / progressive lead**
   `note("<[a4 ~ c5 e5] [a5 ~ g5 e5] [f5 ~ e5 c5] [d5 ~ e5 ~]>*2").s("supersaw").unison(7).detune(0.25).spread(0.7).lpf("4000:2").attack(0.005).decay(0.2).sustain(0.6).release(0.25).delay("0.3:0.1875:0.4").room(0.4).size(4).gain(0.6)` (.055/.37)
2. **Acid 303 (ladder filter, accent through `lpenv` per bar)**
   `note("a1 a1 a2 a1 c2 a1 [g1 a2] a1").s("sawtooth").ftype("ladder").lpf(300).lpq(14).lpenv("<3 5 4 6>").lpdecay(0.14).lpsustain(0).drive(1).decay(0.18).sustain(0.5).release(0.03).distort("1.2:0.5:soft").gain(0.6)` (.075/.39).
   superdough has **no glide/portamento** (only ZZFX has `slide`). To fake a slide, use `clip(1.05)` overlaps or `penv(-2).pattack(0.04).panchor(1)` on the slid notes.
3. **Deep-house chord stab (minor 7th, filter envelope)**
   `note("<[c3,eb3,g3,bb3] [f3,ab3,c4,eb4]>").struct("~ x ~ [~ x] ~ x ~ ~").s("sawtooth").lpf(500).lpenv(4).lpdecay(0.15).lpsustain(0).lpq(4).decay(0.25).sustain(0).release(0.05).delay("0.3:0.1875:0.4").room(0.3).size(3).gain(0.55)` (.067/.65).
   **Works with today's whitelist** as `.lpf("500:4:4")` with the default filter env (rms .066, practically identical).
4. **House organ stab (additive square, 7 partials)**
   `note("<[a3,c4,e4,g4] [d3,f3,a3,c4]>").struct("~ x ~ x ~ x ~ x").s("square").n(7).lpf(3000).lpq(1).decay(0.2).sustain(0.15).release(0.05).room(0.25).gain(0.45)` (.085/.62)
5. **Sidechain-pumping pad (browser / strudel.cc)**
   `stack(s("bd*4").bank("RolandTR909").duckorbit(2).duckattack(0.22).duckdepth(0.8), note("<[a3,c4,e4,g4] [f3,a3,c4,e4] [d3,f3,a3,c4] [e3,g3,b3,d4]>").s("supersaw").unison(5).detune(0.35).spread(1).attack(0.6).sustain(1).release(1.5).lpf(1400).lpq(1).room(0.6).size(6).orbit(2).gain(0.4))`
5b. **Pumping pad that also works offline (tremolo instead of duck)**
   `... .s("supersaw").unison(5).detune(0.35).spread(1).attack(0.6).sustain(1).release(1.5).lpf(1400).tremolosync(4).tremolodepth(0.8).room(0.6).size(6).gain(0.45)`.
   **Verified** envelope across one beat: .28→.30→.39→.48→.59→.72→.85→1.0, a rising pump. The default shape (tri, skew 1) and `"ramp"` both rise; `"saw"` falls, which is wrong for a pump.
6. **Reese bass (techno / progressive)**
   `note("<a1 f1 c2 g1>").s("supersaw").unison(3).detune(0.22).spread(0.25).lpf(700).lpq(3).lpenv(1.5).lpattack(0.4).lpsustain(0.5).phaser(0.25).phaserdepth(0.5).distort("1.5:0.5:soft").gain(0.6)` (.089/.33). Keep `spread` low so the low end stays mono.
7. **FM bell (inharmonic ratio 3.5, decaying index)**
   `note("<[e5 ~ b4 ~ g5 ~ e5 ~] [d5 ~ a4 ~ f#5 ~ d5 ~]>").s("sine").fm(6).fmh(3.5).fmdecay(0.5).fmsustain(0).decay(1).sustain(0).release(0.6).delay("0.35:0.375:0.45").room(0.5).size(5).gain(0.5)` (.094/.38)
8. **FM pluck / marimba-ish arp**
   `note("a3 c4 e4 a4 e4 c4 g3 e4").s("triangle").fm(3).fmh(2).fmdecay(0.08).fmsustain(0).decay(0.18).sustain(0).release(0.05).delay("0.25:0.1875:0.35").room(0.2).gain(0.8)` (.048/.23 at gain .6, so raise the gain)
9. **Plucky saw arp (resonant filter "pew")**
   `note("<[a3,c4,e4,g4] [f3,a3,c4,e4]>").arp("0 1 2 3 2 1 3 2").s("sawtooth").lpf(350).lpenv(5).lpdecay(0.12).lpsustain(0).lpq(6).decay(0.14).sustain(0).release(0.04).pan("0.35 0.65").delay("0.4:0.1875:0.5").room(0.3).size(3).gain(0.75)` (.033/.31 at gain .55)
10. **Dub-techno chord (hpf + long delay + big room)**
    `note("[d3,f3,a3,c4]").struct("~ x ~ ~ ~ ~ x ~").s("sawtooth").hpf(180).lpf(700).lpenv(2.5).lpdecay(0.2).lpsustain(0).lpq(3).decay(0.3).sustain(0).delay("0.55:0.375:0.65").room(0.6).size(6).orbit(3).gain(0.5)` (.075/.90). Put it on its own orbit, because the delay and room are global.
11. **House sub with click (pitch-env "zap" plus soft saturation)**
    `note("a1 ~ [~ a1] ~ a1 ~ [~ c2] [~ g1]").s("sine").penv(-12).pdecay(0.02).panchor(0).decay(0.3).sustain(0.7).release(0.06).shape(0.35).lpf(220).gain(0.8)` (.176/.60)
12. **PWM techno bass**
    `note("a1 [~ a2] a1 [~ e2] a1 [~ g2] a1 [~ c2]").s("pulse").pw("0.3:0.5:0.2").lpf(900).lpenv(2).lpdecay(0.12).lpsustain(0.2).lpq(3).decay(0.15).sustain(0.5).release(0.03).gain(0.9)` (.045/.20 at gain .6)
13. **Talking / vowel bass (house)**
    `note("a1*8").s("sawtooth").vowel("<a o e i>").lpf(1500).lpq(2).decay(0.15).sustain(0.4).release(0.03).gain(1)`. The vowel filter loses about 6 dB (.041/.17 at gain .7).
14. **Progressive lead with vibrato and a falling scoop**
    `note("<[e5@3 d5] [c5@3 b4] [a4@2 b4 c5] [b4@4]>").s("supersaw").unison(5).detune(0.18).spread(0.6).vib("5:0.12").penv(-2).pattack(0.06).panchor(1).attack(0.02).sustain(0.8).release(0.4).lpf(3000).delay("0.35:0.375:0.4").room(0.5).size(5).gain(0.5)` (.053/.26)
15. **Air / noise-layered pad with a per-bar filter build**
    `note("<[a3,e4]@4>").s("sawtooth").noise(0.3).lpf("<400 800 1600 3200>").lpq(4).hpf(150).sustain(1).release(0.3).room(0.4).gain(0.4)` (.18/.53)

Not rendered, needs `wt_` samples: **wavetable pad**, e.g.
`note("<[a3,c4,e4]@4>").s("wt_<name>").unison(4).detune(0.2).spread(0.8).wt(0.2).wtenv(0.6).wtattack(1.5).attack(0.5).release(1).lpf(2500)`.
The `wt_` files would have to be fetched once into `data/cache`.

General rules that make parts sound "produced":
- Use a filter **envelope** (`lpenv` plus `lpdecay`) on stabs, plucks and basses, rather than a static `lpf`.
- Layer detune (`supersaw` or `unison`) on pads and leads.
- Use tempo-synced delay: `delay(0.3)` alone already gives 3/16, a dotted eighth.
- Give each role its own `orbit` so reverb and delay do not bleed.
- Cut the low end from chords with `hpf(150-250)`.
- Vary over time with mini patterns such as `lpenv("<3 5 4 6>")` or `lpf("<400 800 1600>")`.

## 3. Pitfalls found (verified)

- **`duckorbit` does nothing in our offline renderer.** A pad with and without a ducking kick had
  rms .1283 vs .1288 and a flat envelope. superdough 1.2.6 runs the duck from a `ConstantSourceNode.onended`
  callback at t−0.01. In an OfflineAudioContext the main thread handles that callback after the render has
  already passed that point, so the gain ramps land in the past. Duck also logs an error if the target orbit
  does not exist yet. On strudel.cc (realtime) it works. Offline, use `tremolosync(4)` (recipe 5b). An
  untested alternative is to `ctx.suspend()` at each kick time.
- **`render.mjs` does not pass the hap's cycle position to `superdough()`.** `@strudel/webaudio` calls
  `superdough(value, t, dur, cps, hap.whole.begin)`. Without that argument every tremolo/LFO starts at the same
  phase on each note, so short notes with `tremolosync(4)` came out near-silent (rms .0036). Passing
  `h.whole.begin.valueOf()` as the 5th argument gave rms .036. This is a one-line fix in `js/render.mjs`.
- **Resonance clips hard.** `lpq(30)` with `ftype("24db")` and `lpenv(4)` peaked at **10.3** (≈+32 dB over the
  dry saw), because biquad Q is in dB and 24db cascades two biquads. Clamp `lpq` to ≤15 for 12db, ≤10 for 24db
  and ≤25 for ladder. `distort(2)` alone took the peak from .25 to .82, and `shape(.4)` to .46.
- Chord voices add up: a 4-note saw chord at `gain(0.5)` already peaks at about .5. Keep chords/pads at 0.3–0.45
  and basses at 0.6–0.8, and do not rely on `render.mjs` peak-normalising each clip (it hides clipping inside the mix).
- Chaining the same control twice keeps only the **last** call (`.gain("…").gain(0.4)` keeps 0.4).
- `delaytime` is in seconds and does not follow the tempo. Prefer omitting it (default 3/16 cycle) or `delaysync`.
- Reverb and delay are shared **per orbit**. Changing `size`, `roomlp`, `roomdim` or `roomfade` regenerates the
  impulse response (CPU spike), so do not pattern them, and give each lane a fixed size or its own orbit.
- `n` on basic oscillators changes the waveform (number of partials) in 1.2.6, and on `supersaw` it is used as
  `detune` when `detune` is unset.
- `supersaw` and wavetable unison use random start phases, so the same code renders slightly differently each
  run. Keep that in mind for reward or eval caching.
- superdough evicts the oldest voices beyond `maxPolyphony` = 128 (with a 0.25 s fade). Long-release pads with
  fast retriggers hit this limit.

## 4. Performance (offline, node-web-audio-api; 64 notes = `a2*16` over 4 bars at 120 BPM)

| addition to a plain saw | render ms | node type |
|---|---|---|
| plain saw / +lpenv / +24db / +delay / +fm / +vib | 200–500 | native (cheap) |
| +room(.5).size(4) | 660 | native ConvolverNode, one per orbit |
| +vowel | 1370 | 5 native biquads |
| +crush | 4800 | AudioWorklet |
| `pulse` osc / +phaser / +shape / +distort | 6000–7000 | AudioWorklet |
| +tremolo / `supersaw` (unison 1, 5 or 9) / ladder | 6600–9000 | AudioWorklet |
| 5-note supersaw chord ×16/bar ×4 bars, unison 9 | **39 000 for 9.2 s of audio** (≈4× slower than realtime) | 320 worklet voices |

In this renderer the cost is roughly **per AudioWorklet node per note**, and grows little with
the voice count inside it: supersaw with unison 1, 5 and 9 cost about the same. In the browser, worklets are
cheaper, but the same ranking holds and a dense supersaw chord pattern is the classic cause of glitches on strudel.cc.
Budget per loop:
- At most ~1 worklet-based lane playing 16ths.
- Use supersaw for sustained pads and leads (few onsets), and plain `sawtooth` + `lpenv` for fast stabs and arps.
- Avoid stacking `ladder` + `distort` + `phaser` on 16th-note parts.

## 5. Whitelist recommendation (`js/dialect.mjs` METHODS)

**Add now: works on superdough 1.2.6, native nodes, low risk.**
`lpenv lpattack lpdecay lpsustain lprelease fanchor hpq bpf bpq unison detune spread fm fmh fmattack fmdecay fmsustain fmwave vib vibmod noise penv pattack pdecay panchor vowel orbit delaysync postgain compressor`
Optional: `roomlp roomdim` (constants only).

**Add with clamps or limits: worklet-based or loud.**
- `ftype` (12db/ladder/24db) and `drive` (≤3)
- `distort` (≤3, and default its postgain to ≤.7) and `distorttype`
- `tremolosync tremolodepth tremoloshape`
- `phaser phaserdepth`
- `pw pwrate pwsweep`, used with `s("pulse")`
- `djf`

Validator limits to add:
- `lpq` ≤ 15 (≤ 25 with ladder)
- `unison` ≤ 7, `detune` ≤ 1
- `fm` ≤ 12
- `|penv|` ≤ 24
- `orbit` 1–8
- `size` ≤ 8 and constant
- `delayfeedback` ≤ .8
- `postgain` ≤ 1.5
- "≤ 1 worklet lane with > 8 onsets per bar"

**Do not add yet.**
- `duckorbit duckattack duckdepth`: a no-op offline. Add them only together with an offline workaround, or for browser-only output.
- `lprate lpsync lpdepth partials transient fm2…`: silently ignored until superdough is bumped to 1.3.0. That bump is worth considering, since core 1.2.6 already targets it.
- `chorus`: not implemented.
- `ir`: loads arbitrary sample buffers.
- `coarse`: Chromium-only.
- `roomfade`: rarely useful.
- Signals and `.lfo/.env`: the dialect cannot express them. Use mini-notation steps instead.

**No whitelist change needed to get richer sounds today.**
- `lpf("cutoff:q:env")` gives a filter envelope with the default A .005, D .14, S 0, R .1.
- `hpf("f:q:env")` works the same way.
- `delay("wet:time:fb")` sets all delay fields in one call.
- `s("supersaw")`, `s("pulse")` and `s("white")` are just sound names.
- `.n(4-16)` gives darker additive waves.

All of these were verified in the renders above.
