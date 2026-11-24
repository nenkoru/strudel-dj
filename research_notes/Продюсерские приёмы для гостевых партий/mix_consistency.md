# Mix consistency: making AI-generated Strudel guest parts sit inside finished, mastered dance tracks

Scope: same perceived loudness, tone and space for added synth/sample parts (bass, chords, pads, arps, leads, drums) across parts and across tracks in a DJ set. Strudel/superdough facts are from the locally installed packages (`js/node_modules/superdough` and `@strudel/core`, both v1.2.6), which are the same files the project renders with. Items marked **[UNVERIFIED]** are reasoning or recalled numbers that no fetched source confirmed in this session.

## 1. Loudness: measuring short synth parts, normalising timbres, target level per role, per-track adaptation

### Takeaway
Measure every guest part and every track section with ITU-R BS.1770 K-weighted loudness. Use EBU **short-term (3 s)** loudness for following the track and **momentary (400 ms)** for short phrases. Set each part's gain so it lands a fixed number of LU below the track's short-term loudness for that section, with the offset set by role. Peak or RMS normalisation will not do this: superdough's own level constants already put samples about 10 dB above oscillators at the same `gain`. The only real data on relative source levels (De Man et al. 2014) puts the lead about 3 LU below the mix and supporting sources about 10 to 17 LU below it.

### Cited Findings
**Measurement standard (BS.1770 / EBU R128)**
- Momentary loudness uses a sliding rectangular window of **0.4 s** and is ungated. Short-term uses a sliding rectangular window of **3 s**, is ungated, and live meters update at **≥10 Hz**. Integrated loudness uses BS.1770 gating, with live meters updating at ≥1 Hz. EBU Mode forbids extra attack/release smoothing after the rectangular windows. — [EBU Tech 3341 (2023)](https://tech.ebu.ch/docs/tech/tech3341.pdf)
- Integrated gating has an absolute "silence" gate at **−70 LUFS** and a relative gate **10 LU** below the absolute-gated level. It is applied to **400 ms blocks with 75 % overlap**, and an incomplete final block is discarded. The relative gate was changed from −8 to −10 LU in the 2011 revision. — [EBU Tech 3341](https://tech.ebu.ch/docs/tech/tech3341.pdf)
- LRA (Loudness Range) is in LU, and 1 LU = 1 dB. — [EBU Tech 3341](https://tech.ebu.ch/docs/tech/tech3341.pdf)
- Loudness formula as implemented in pyloudnorm: per block `l_j = −0.691 + 10·log10(Σ_i G_i · z_ij)`, where `z` is the mean square of the K-weighted channel and `G_i` is the channel weight (1.0 for L and R). Defaults are `block_size=0.400` and `overlap=0.75`, with `Γ_a = −70` and `Γ_r = (gated mean) − 10`. — [pyloudnorm meter.py](https://github.com/csteinmetz1/pyloudnorm/blob/master/pyloudnorm/meter.py)
- K-weighting filter constants as used in pyloudnorm's exact "DeMan" variant:
  - stage 1 is a **high shelf**, G = **+3.99984 dB**, Q = 0.70718, fc = **1681.97 Hz**
  - stage 2 is a **high pass**, Q = 0.50033, fc = **38.135 Hz**

  The simplified default uses a +4 dB shelf at 1500 Hz and a 38 Hz HPF. — [pyloudnorm meter.py](https://github.com/csteinmetz1/pyloudnorm/blob/master/pyloudnorm/meter.py)
- pyloudnorm's loudness-range routine switches to `block_size = 3.0` and `overlap = 0.97`, which reproduces the 3 s / ~10 Hz short-term series offline. — [pyloudnorm meter.py](https://github.com/csteinmetz1/pyloudnorm/blob/master/pyloudnorm/meter.py)

**Relative loudness of sources in real mixes**
- De Man, Leonard, King and Reiss (ISMIR 2014) studied 8 songs, each mixed by 8 engineers, and measured each source's loudness relative to the full mix. They used BS.1770 modified with a **280 ms time constant and +10 dB pre-filter gain**, the best-performing variant for multitrack content. — [De Man et al. 2014](https://archives.ismir.net/ismir2014/paper/000293.pdf)
- The lead vocal was the only source significantly louder than the others, at **−2.7 ± 1.6 LU relative to the mix**. The authors read this as a consensus target of about **−3 LU** for the main element. The other sources (kick, snare, other drums, bass) showed no significant difference in mean relative loudness from each other. — [De Man et al. 2014](https://archives.ismir.net/ismir2014/paper/000293.pdf)
- The table values for the non-lead sources are roughly **−9.5 to −16.8 LU** relative to the mix: kick ≈ −13.2 ± 4.1, snare ≈ −16.8 ± 6.2, other drums ≈ −12.7 ± 5.5, and the remaining source ≈ −9.5 ± 3.5. The average across sources is −10.95 ± 4.1 LU. **Caveat:** the extracted table header puts −2.65 LU under "Bass", but the text and figure attribute ≈ −2.7 LU to the vocal. The column order is ambiguous, and −9.5 LU is most likely the bass. These were acoustic or pop/rock songs, not club music. — [De Man et al. 2014](https://archives.ismir.net/ismir2014/paper/000293.pdf)
- The same paper found that relative loudness depends strongly on the song (p < 5·10⁻¹¹). Bass, snare and "rest" drum levels also depend on the engineer. — [De Man et al. 2014](https://archives.ismir.net/ismir2014/paper/000293.pdf)
- **Crest factor** (peak-to-RMS ratio) by source, 1 s window: kick ≈ 9.8, snare ≈ 16.7, bass-column ≈ 4.3, vocal-column ≈ 5.3, full mix ≈ 5.3. At 100 ms the full mix is ≈ 3.3. Mixing **increased** crest factor relative to the raw tracks for every instrument. — [De Man et al. 2014](https://archives.ismir.net/ismir2014/paper/000293.pdf)
- Wichern, Wishnick, Lukin and Robertson (iZotope, AES 139, 2015) built instrument-dependent **target-loudness templates** from human mixes. In listening tests, subjects preferred automatic mixes from the **simple energy-based loudness model** over the more complex psychoacoustic one. — [AES e-lib 17928 (abstract)](https://www.aes.org/e-lib/browse.cfm?elib=17928)

**Superdough level constants (local source, v1.2.6)**
- `gain` defaults to **0.8**, and `velocity` simply multiplies `gain`. — `superdough/superdough.mjs` `defaultDefaultValues` and line 505 (upstream [strudel repo](https://codeberg.org/uzu/strudel))
- Basic oscillators (`sine`, `sawtooth`, `square`, `triangle`) pass through a hard-coded `gainNode(0.3)` ("turn down"), which is **−10.5 dB**. Supersaw peaks at `0.3 / √voices`. Samples go through an ADSR with peak 1 and no 0.3 trim, so **a sample at the same `gain` is ≈10 dB hotter than an oscillator synth**. — `superdough/synth.mjs` lines 54, 184–191; `superdough/sampler.mjs` line 315
- `applyGainCurve` is the **identity function** by default (`gainCurveFunc = (val) => val`), with a `setGainCurve()` hook. The docstring says `gain` "controls the gain by an exponential amount", but in this version no Strudel package calls `setGainCurve`, so `gain` is linear amplitude here. — `superdough/superdough.mjs` lines 40–48, `@strudel/core/controls.mjs` gain doc

### Inferences
- **Basic waveform RMS at equal peak** (standard maths): sine −3.0 dBFS, saw and triangle −4.8 dBFS, square 0 dBFS. On top of that, K-weighting adds ≈ +4 dB above ~2 kHz, so a saw lead measures and sounds much louder than a sine sub at equal `gain`. This partly explains why "some voices are much louder or brighter".
- **Recommended normaliser:**
  1. Render each guest part solo (offline, Python with soundfile and pyloudnorm, or OfflineAudioContext).
  2. Compute its *active* loudness: the gated integrated loudness over the bars where it plays, or the median of momentary loudness over those bars, so rests do not drag it down.
  3. For the track, compute the short-term series S(t) and take the median S over the section the part will sit in (drop vs breakdown).
  4. `g_dB = (S_track_section + offset_role) − L_part`, `gain_new = gain_old · 10^(g_dB/20)`.

  This is per track and per section, so it adapts automatically to masters of different loudness.
- **Proposed role offsets** relative to the track's section short-term loudness, extrapolated from De Man's −3 LU lead and −10 to −17 LU supporting sources, assuming a guest layer should *add* rather than compete with an already finished mix — **[UNVERIFIED starting points; tune by listening]**:

  | Role | Offset below track short-term loudness |
  |---|---|
  | Hook lead / featured stab | −6 to −9 LU |
  | Arp / pluck | −10 to −13 LU |
  | Chords / stabs | −10 to −14 LU |
  | Pad / atmos | −14 to −20 LU |
  | Added bass | −8 to −12 LU, and only if the track's bass is muted or thin; otherwise high-pass it or skip it |
  | Added percussion / hats | −12 to −18 LU |

- Use momentary loudness (400 ms) for parts shorter than 3 s, such as one-shots and fills. For very sparse parts, use the 95th percentile of momentary loudness rather than the mean, otherwise sparse parts get over-boosted.
- K-weighting is nearly flat from about 100 Hz to 1 kHz and only lightly attenuates sub frequencies (HPF at 38 Hz, Q 0.5). LUFS therefore tends to *under*-report how dominant a sub bass is on a club system and how much headroom it eats. Cap bass parts on **peak or true peak** as well, not only LUFS.
- Crest factor is a useful second check: a guest part with a much higher crest factor than the mastered track (whose 100 ms crest is roughly 3.3 in De Man's mixes) will poke out on transients even at matched LUFS. Fix this with a fast limiter or compressor on that part, or a slower attack envelope.
- Club masters are typically very loud (often quoted around −6 to −9 LUFS integrated for house and techno). **[UNVERIFIED, not sourced this session.]** The adaptive offset method makes the exact number irrelevant.

### Gaps
- No published relative-loudness data was found specifically for electronic/dance mixes or for "layer over a finished master". The De Man figures come from acoustic and pop/rock songs.
- The full Wichern 2015 templates (per-instrument target loudness) were not accessible (paywalled). Only the abstract was read.
- No source found for perceived loudness of very short synth events (<400 ms) beyond BS.1770's 400 ms block.

## 2. Tone matching: spectral/EQ matching, tilt, brightness ceilings, HPF/LPF per role

### Takeaway
Mastered commercial music follows a fairly consistent long-term spectrum. It falls about **5 dB per octave from 100 Hz to 4 kHz**, gets steeper above that, and has a steep low cut around **60 Hz**. Electronic music is among the brightest genres. A guest part should be EQ'd so that, *summed* with the track, the result keeps the track's own long-term spectrum and centroid. Matching-EQ tools (Matchering-style: mid/side FFT ratio, smoothed with LOWESS) do this offline. In the browser, the realistic approach is precomputed filter settings per role and per track.

### Cited Findings
- The long-term spectrum of commercial recordings from 1950 to 2010 is roughly "a linearly decaying distribution of around **5 dB per octave between 100 and 4000 Hz**, becoming gradually steeper with higher frequencies, and a severe **low-cut around 60 Hz**". The presence region (1.5–4 kHz) slope became shallower over the decades, and the low end extended further with a lower resonant peak. — [Pestana, Ma, Reiss et al., AES 135, 2013](https://joshreiss.github.io/documents/2013/Pestana%20Ma%20Reiss%20-%20AES135.pdf)
- Genre table, spectral slope / centroid: Electronic **−0.746 / 845 Hz**, Disco −0.804 / 963 Hz, Hip-hop −0.814 / 662 Hz, Pop −0.943 / 868 Hz, Rock −0.979, Jazz −1.293. Here slope means the log-log regression slope, so less negative is brighter. "Electronic ones allow and benefit from bigger frequency extensions." — [Pestana et al. 2013](https://joshreiss.github.io/documents/2013/Pestana%20Ma%20Reiss%20-%20AES135.pdf)
- Per-source spectral data from real mixes (De Man 2014), centroid / 85 % rolloff:

  | Source | Centroid | 85 % rolloff |
  |---|---|---|
  | Kick | ≈ 2.25 kHz | 4.5 kHz |
  | Snare | ≈ 4.4 kHz | 9.0 kHz |
  | Bass column | ≈ 1.05 kHz | 1.6 kHz |
  | Vocal column | ≈ 2.9 kHz | 5.6 kHz |
  | Full mix | ≈ 2.48 kHz | 5.0 kHz |

  The average mix spectrum agreed with a "target spectrum" of number-one hits within one standard deviation, except in the highest band. — [De Man et al. 2014](https://archives.ismir.net/ismir2014/paper/000293.pdf)
- In the same study, EQ was strongly song-dependent. No band was consistently boosted or cut per instrument, but engineers agreed on large corrections for sources with spectral anomalies. — [De Man et al. 2014](https://archives.ismir.net/ismir2014/paper/000293.pdf)
- Matchering 2.0 makes a target match the reference's "same RMS, FR [frequency response], peak amplitude and stereo width" and ends with its own "Hyrax" brickwall limiter. In a review it ranked 3rd of 12 entries, behind two professional mastering engineers. — [Matchering README](https://github.com/sergree/matchering)
- Matchering defaults: `fft_size = 4096`, `lin_log_oversampling = 4`, `lowess_frac = 0.0375` (LOWESS smoothing of the EQ curve), `rms_correction_steps = 4`, `max_piece_size = 15 s`, internal SR 44.1 kHz. Limiter: attack 1 ms, hold 1 ms, release 3000 ms. Level and frequency matching run separately on **mid** and **side** signals, using the "loudest pieces" of each file. — [matchering/defaults.py](https://github.com/sergree/matchering/blob/master/matchering/defaults.py), [matchering/stages.py](https://github.com/sergree/matchering/blob/master/matchering/stages.py)

### Inferences
- **Match-EQ formula for a layer**, offline:
  1. Compute the long-term average spectrum of the track section, `S_ref(f)`, and of the part, `S_p(f)` (Welch, n_fft 4096).
  2. Smooth both in fractional octaves (1/3 octave) or with LOWESS (frac ≈ 0.04).
  3. Don't make the part equal the track. Instead match its **tilt**: fit the log-log slope of `S_p` over the part's own band, and compare it with the track's slope over the same band (≈ −5 dB/oct for 100 Hz–4 kHz per Pestana).
  4. Apply a tilt EQ (low shelf and high shelf at opposite gains around ~1 kHz) to bring the part's slope within about ±1 dB/oct of the track's.
  5. Separately, cap brightness: the part's centroid should not exceed the track section's centroid by more than about 1.5×. **[UNVERIFIED threshold]**
- **Proposed per-role bandpass** in Strudel `hpf` / `lpf` (`hcutoff` / `cutoff`) Hz — **[UNVERIFIED conventions; consistent with Pestana's 60 Hz mastering low-cut and the De Man centroid values]**:

  | Role | Filter settings |
  |---|---|
  | Added bass | HPF 30–40, LPF 2–5 k. Mono. Ideally remove the track's bass or EQ-dip it, otherwise the two basses double the sub energy. |
  | Chords / stabs | HPF 150–250, LPF 6–10 k |
  | Pads | HPF 200–300, LPF 5–8 k |
  | Arps / plucks | HPF 200–400, LPF 8–12 k |
  | Leads | HPF 150–300, LPF 10–14 k |
  | Hats / perc | HPF 400–800 |

- Filter envelopes (`lpenv`) make spectral centroid time-varying, so measure the centroid of the *rendered* part rather than estimating it from `cutoff`.
- Superdough's `ftype` default is `'12db'`, and `'24db'` cascades two biquads, giving a steeper cut for HPF on pads and chords. — from `superdough.mjs` `defaultDefaultValues` and the filter code at lines 610–625.

### Gaps
- No peer-reviewed numeric "max brightness relative to the bed" rule was found. The centroid-ratio rule is a proposal.
- Pestana's per-octave numbers for the electronic genre curve were only shown graphically. Exact dB per band was not extracted.

## 3. Blend: sidechain to the track's kick, glue compression, shared reverb/delay, width, saturation, masking-aware EQ

### Takeaway
Use three main blend tools:
- **Kick-synced ducking** of the guest bus, so the guest parts "breathe" with the track like its own elements do.
- **Light glue compression and a ceiling limiter** on the guest sum, about 2:1 with 1–2 dB of gain reduction.
- **One shared reverb/delay space per guest bus.**

Masking-aware EQ (Hafezi & Reiss) reduces measured and perceived masking. In practice, static role-band carving plus a dip where the track's lead or bass energy sits is the feasible version.

### Cited Findings
- **Sidechain timing:** release is commonly synced to tempo, with a quarter note = `60000 / BPM` ms (≈ 500 ms at 120 BPM) for an obvious pump, or shorter for subtle ducking. Attack is typically ≤ 2 ms. — [Sonarworks: sidechain compression](https://www.sonarworks.com/blog/learn/sidechain-compression); [EDMProd: sidechain](https://www.edmprod.com/sidechain-compression/)
- Two typical presets:
  - subtle headroom ducking: attack ≈ 1–10 ms, release ≈ 200–400 ms (roughly the kick's length)
  - classic pump: attack ≈ 10–30 ms, release ≈ 300–800 ms

  These are blog-level sources that vary between authors. — [Sonarworks](https://www.sonarworks.com/blog/learn/maximize-your-mixs-clarity-and-groove-with-sidechain-compression)
- Sound On Sound: higher ratio for "serious throbbing"; for a subtle effect, threshold around −20 dB with shorter attack and release. — [SOS, Studio One side-chaining](https://www.soundonsound.com/techniques/studio-one-how-do-side-chaining)
- **Glue/bus compression:** SOS compared bus compressors on a full mix at **2:1, 10 ms attack, auto release, about 2 dB of compression**. — [SOS review: Cytomic The Glue](https://www.soundonsound.com/reviews/cytomic-glue). SOS also reports good "gelling" on the mix bus with **1.5:1 or 2:1** and "just a couple of dB" of gain reduction. — [SOS review: Warm Audio Bus Comp](https://www.soundonsound.com/reviews/warm-audio-bus-comp)
- **Masking-aware EQ:** Hafezi & Reiss (JAES 63(5), 2015) built four autonomous multitrack EQs: offline fully-auto, offline semi-auto, and two real-time versions. All reduced both perceived and objective masking. The semi-autonomous offline version, with one user parameter, beat an amateur mix and came close to a professional one. They also found that **standard objective masking measures track perceived masking poorly**. — [AES e-lib 17637 (abstract)](https://www.aes.org/e-lib/browse.cfm?elib=17637)
- Panning in real mixes: low-frequency sources, lead and snare are panned centrally. In the lowest band, only the bass was significantly more central than the full mix. Side/mid ratio: bass-column ≈ 0.009, vocal-column ≈ 0.022, "rest" drums ≈ 0.24, full mix ≈ 0.10. — [De Man et al. 2014](https://archives.ismir.net/ismir2014/paper/000293.pdf)
- Automatic reverb is one of the newer, harder targets in automatic mixing (Chourdakis 2016/2017, Benito 2017), and the reverb level can be driven into a target range by a perceptual feedback loop. — [De Man, Reiss, Stables 2017, "Ten years of automatic mixing"](https://www.open-access.bcu.ac.uk/4968/1/WIMP2017_DeManEtAl.pdf)

### Inferences
- **Ducking depth for a layer over a finished track:**
  - Pads, chords and bass layers: gain reduction of about 3–6 dB on each kick, recovering by an eighth to a quarter note (≈ 230–470 ms at 128 BPM).
  - Leads and arps: 1–3 dB, or none.

  This mimics the pumping already present in many house/techno masters. **[UNVERIFIED numbers; derived from the presets above]**
- **Width:** keep guest bass, kick-range content and the main lead near mono (side/mid < 0.03, following De Man's bass and vocal values). Pads and chords can be wide, but keep the guest bus's side/mid at or below the track's own (≈ 0.1 typical full mix). This avoids the guest parts sounding detached from the mastered stereo image.
- **Space:** one reverb per guest bus with a fixed IR size and low-pass, matched to the track. Short and dark for techno, longer for progressive. All parts send to it at role-dependent amounts. Separate reverb settings per part produce exactly the "different space per part" jump the owner hears.
- **Saturation:** mild waveshaping (`shape` or `distort` at low drive with `shapevol` or `distortvol` compensation) raises density and lowers crest factor, approaching a mastered sound. Re-measure LUFS afterwards because drive raises loudness. **[UNVERIFIED as a perceptual claim; no source fetched]**
- **Masking-aware EQ, practical version:** compute the track section's spectrum in roughly 1/3-octave bands. Wherever the guest part's band energy is within ~6 dB of the track's in that band, and that band is a key region for the track (kick 50–100 Hz, bass 60–200 Hz, lead 1–4 kHz), cut the part 2–4 dB there or move its filters. **[UNVERIFIED thresholds]** Hafezi & Reiss's finding that objective masking metrics correlate poorly with perception argues for a simple rule plus listening rather than an elaborate masking model.

### Gaps
- No primary academic source was found for sidechain depth or time constants in dance music. The cited numbers are blog and practitioner advice.
- No source was found on how much reverb a guest layer should have relative to a mastered track's ambience, or how to estimate the track's reverb time automatically. Blind RT60 estimation from music exists but was not researched.

## 4. Automatic mixing research (Reiss / De Man): gain, EQ, compression automation, loudness models, real-time feasibility

### Takeaway
Automatic mixing research has covered level, pan, EQ, compression and reverb since Perez Gonzalez & Reiss (2007–2010). The most robust real-time result is **cross-adaptive level setting on a loudness feature**: equal loudness is the baseline, with the lead pushed up. Wichern et al. showed that a simple energy-based loudness model is preferred over a complex psychoacoustic one. Cross-adaptive compression driven by loudness and LRA (Ma, Reiss et al., DAFx 2012) and masking-reduction EQ (Hafezi & Reiss 2015) also have real-time versions.

### Cited Findings
- Timeline from the review: Perez Gonzalez & Reiss automated level, pan, EQ, unmasking and delay correction in 2007–2010, including "Automatic gain and fader control for live mixing" (IEEE WASPAA 2009) and "Automatic maximum gain normalization" (AES 124, 2008). Compression automation followed (Giannoulis 2013, Ma 2013/2015, Maddams 2012), then reverb (Chourdakis 2016/2017, Benito 2017) and machine learning (Mimilakis 2016 and others). — [De Man, Reiss & Stables 2017](https://www.open-access.bcu.ac.uk/4968/1/WIMP2017_DeManEtAl.pdf)
- "A popular assumption is that the loudness of the different tracks … should be equal", with the main element, usually the vocal, set higher. — [De Man et al. 2014](https://archives.ismir.net/ismir2014/paper/000293.pdf)
- Automated **ballistics, time constants and make-up gain** in compressors are already common "assistant"-level automation (Giannoulis et al. 2013). — [De Man, Reiss & Stables 2017](https://www.open-access.bcu.ac.uk/4968/1/WIMP2017_DeManEtAl.pdf)
- The review suggests a feedback loop for perceptual attributes: adjust a parameter until a high-level attribute (for example, "reverb amount") enters a predefined range. — [De Man, Reiss & Stables 2017](https://www.open-access.bcu.ac.uk/4968/1/WIMP2017_DeManEtAl.pdf)
- Intelligent multitrack compression (DAFx 2012) uses loudness and loudness range as features to control each track's compressor cross-adaptively. — [DAFx-12 paper (search summary)](https://www.dafx.de/paper-archive/2012/papers/dafx12_submission_6.pdf)
- Wichern et al. 2015: instrument-dependent target loudness templates from human mixes, and listeners preferred the **energy-based** loudness model. — [AES e-lib 17928](https://www.aes.org/e-lib/browse.cfm?elib=17928)
- Hafezi & Reiss 2015: real-time masking-reduction EQ is possible, but objective masking metrics correlate poorly with perceived masking. — [AES e-lib 17637](https://www.aes.org/e-lib/browse.cfm?elib=17637)
- The review notes that the field is still in its infancy, that reliable training data is scarce, and that mix processes can't be studied in isolation because each source's perception depends on the others. — [De Man, Reiss & Stables 2017](https://www.open-access.bcu.ac.uk/4968/1/WIMP2017_DeManEtAl.pdf)

### Inferences
- **Recommended setup:** do the analysis offline per track and send per-section control values to the browser:
  - a short-term loudness series sampled per bar
  - section boundaries (drop or breakdown)
  - kick onset grid
  - long-term spectrum and centroid per section

  In the browser, apply only cheap per-part `gain` / `postgain`, filters and orbit ducking. This follows the cross-adaptive level approach, simplified by the evidence that energy-based (K-weighted mean-square) loudness is good enough.
- **Real-time gain riding:** update a part's gain at most once per bar (≈ 1.9 s at 128 BPM), smoothing the track's short-term loudness S(t). Limit changes to about ±1 dB per bar to avoid audible pumping. **[UNVERIFIED parameters]**
- Equal loudness is the research baseline but the wrong target for a *guest layer over a finished master*. The finished track is "the mix", so use role offsets below it (section 1) rather than equal loudness.

### Gaps
- Full texts of Perez Gonzalez & Reiss (gain/fader), Ward et al. 2012 (partial-loudness mixing), Ma et al. compression and Wichern 2015 were not read. Their specific parameters (time constants, loudness model variants) are not captured here.
- The ISMIR 2014 modification (280 ms time constant, +10 dB pre-filter gain) cites "[12]", whose identity and results were not checked.

## 5. Practical: how DJs and live performers keep added loops/tools at consistent levels

### Takeaway
Little authoritative published material was found on DJ-specific practice for layering loops over tracks. Studio-practice evidence supports four principles:
- gain-stage by loudness rather than peak
- glue the added bus lightly (2:1, about 2 dB)
- put a brickwall limiter or ceiling on the added bus
- set the level relative to the bed, not as an absolute

### Cited Findings
- Bus glue: 2:1 (or 1.5:1), about 10 ms attack, auto release, about 1–2 dB of gain reduction. — [SOS: Cytomic The Glue](https://www.soundonsound.com/reviews/cytomic-glue); [SOS: Warm Audio Bus Comp](https://www.soundonsound.com/reviews/warm-audio-bus-comp)
- A reference-matching chain ends in a brickwall limiter (Matchering limiter attack 1 ms, hold 1 ms, release 3 s). Clipping and limited-sample counters (8 and 128 samples) are used as quality checks. — [matchering/defaults.py](https://github.com/sergree/matchering/blob/master/matchering/defaults.py)
- EBU short-term loudness (3 s, ≥10 Hz update) is the standard "live meter" scale for following programme loudness. — [EBU Tech 3341](https://tech.ebu.ch/docs/tech/tech3341.pdf)
- Search results indicate that the optimal monitoring level of a track is a linear function of its loudness (Deruty et al. 2014, 55 rock multitracks). This is a search-snippet summary only and was not read in full. — [Deruty et al. 2014](https://www.francoispachet.fr/wp-content/uploads/2021/01/deruty-14c.pdf)

### Inferences
- **Recommended chain for the guest bus** (one orbit, or a few orbits summed):
  1. per-part `gain` from the LUFS normaliser
  2. per-part HPF/LPF by role
  3. shared reverb/delay on the orbit
  4. orbit ducking synced to the track's kick
  5. a final safety limiter or ceiling with ceiling ≈ −1 dBFS and fast attack. This must be added outside superdough (see section 6).
- Gain-stage *before* the limiter so it only catches peaks (≤ 1–2 dB GR). If it works harder, it changes the tone and makes guest parts duller and denser from track to track.
- Between tracks, re-run the per-section offset computation. Constant `gain` values across tracks is exactly what causes "level jumps between tracks", because masters differ in loudness and spectral density.
- DJ mixers apply per-channel trim and EQ to the *track*. If the owner trims the track channel, the guest offsets should follow the post-trim, post-fader track level, which means a live tap of the track output rather than the file analysis. **[UNVERIFIED; depends on the routing of the owner's setup]**

### Gaps
- No primary or authoritative sources were found on DJ practice for live layering (for example Ableton or Traktor remix-deck performers' level conventions). This needs a targeted practitioner search: Ableton DJ templates, Traktor Remix Decks gain conventions, live-PA mastering chains.

## 6. Browser feasibility: WebAudio primitives and what Strudel/superdough exposes

### Takeaway
WebAudio has everything needed for metering (AnalyserNode, AudioWorklet), for K-weighting (BiquadFilterNode, or IIRFilterNode with exact coefficients), and for a limiter or compressor (DynamicsCompressorNode, which has 6 ms lookahead and auto makeup gain but **no sidechain input**).

Superdough exposes:
- per-note `gain`, `velocity` and `postgain`
- per-note filters
- per-note `compressor` (a DynamicsCompressorNode *per event*, not per bus)
- per-orbit shared reverb, delay and DJ filter (`djf`)
- per-orbit **ducking** (`duckorbit`, `duckdepth`, `duckonset`, `duckattack`), which gives kick-synced sidechain from a silent trigger pattern

It has **no bus compressor or limiter** on orbits or on the master output. Bus glue and limiting must be added to the output graph by the host app.

### Cited Findings
**WebAudio spec**
- DynamicsCompressorNode defaults and ranges:

  | Parameter | Default | Range |
  |---|---|---|
  | threshold | −24 dB | −100 … 0 |
  | knee | 30 dB | 0 … 40 |
  | ratio | 12 | 1 … 20 |
  | attack | 0.003 s | 0 … 1 |
  | release | 0.25 s | 0 … 1 |

  All are k-rate. It has fixed look-ahead implemented as a 6 ms pre-delay. **"Side-chaining is not supported."** The `reduction` attribute is a read-only dB value for metering. — [W3C Web Audio API Editor's Draft](https://webaudio.github.io/web-audio-api/)
- Makeup gain is computed automatically: full-range gain is the compression curve evaluated at 1.0, full-range makeup gain is its inverse, and the result is "the 0.6 power of full range makeup gain". The current Editor's Draft also lists a `makeupGain` AudioParam with a `MakeupGainOptions` enum `"automatic"`. Browser support for that new attribute was not checked. — [Web Audio API ED](https://webaudio.github.io/web-audio-api/)
- AnalyserNode `fftSize` must be a power of two from **32 to 32768**, default **2048**. `smoothingTimeConstant` defaults to **0.8**, with `minDecibels` −100 and `maxDecibels` −30. The node keeps the last 32768 sample-frames. — [Web Audio API ED](https://webaudio.github.io/web-audio-api/)
- BiquadFilterNode types: lowpass, highpass, bandpass, lowshelf, highshelf, peaking, notch, allpass. — [W3C Web Audio API](https://www.w3.org/TR/webaudio/)

**Superdough (local v1.2.6 source)**
- **Per-voice signal chain**, in order: source → filters (lpf, hpf, bandpass, vowel) → coarse / crush / `shape` / `distort` → tremolo → **`compressor`** → `pan` → phaser → **`postgain`** GainNode ("last gain"). From the post-gain node, `delay` and `room` are **post-fader sends** to the orbit's shared delay and reverb, and the dry signal goes to the orbit's `summingNode`. — `superdough/superdough.mjs` lines 610–735
- `compressor("threshold:ratio:knee:attack:release")` creates a **new DynamicsCompressorNode per triggered event**. Defaults when unspecified are threshold −3, ratio 10, knee 10, attack 0.005, release 0.05. — `superdough/helpers.mjs` `getCompressor` lines 130–139; `@strudel/core/controls.mjs` compressor doc (example `.compressor("-20:20:10:.002:.02").postgain(1.5)`)
- **Orbit bus:** `summingNode` → optional `djf` worklet (DJ filter, orbit-wide) → `output` GainNode. Reverb and delay are created **once per orbit** and fed by sends. Changing reverb parameters regenerates the IR. There is no dynamics processing on the orbit. — `superdough/superdoughoutput.mjs` `class Orbit` lines 7–116
- **Master output:** ChannelMerger → `destinationGain` GainNode → `audioContext.destination`. There is **no compressor or limiter**, so summed orbits can clip. — `superdough/superdoughoutput.mjs` lines 117–140
- **Ducking:** `duckorbit(n)` is placed on a *trigger* pattern and calls `Orbit.duck()` on target orbit n at each event. The orbit's output gain ramps exponentially to `clamp(1 − √depth, 0.01, current)` over `duckonset` seconds, then ramps exponentially back to 1 over `duckattack` seconds (default 0.1, minimum 0.002). — `superdough/superdoughoutput.mjs` lines 88–111
- The docs show the **silent-trigger idiom**, `s("bd*4").duckorbit(2).duckattack(0.3).duckonset(0.01).postgain(0)`, with `duckonset(0.01)` to avoid clicks. Multi-orbit form: `duckorbit("2:3")`, `duckdepth("1:0.5")`. — `@strudel/core/controls.mjs` lines 957–1038

### Inferences
- **Ducking depth mapping** (from `1 − √depth`):

  | depth | Gain reduction |
  |---|---|
  | 0.05 | −2.2 dB |
  | 0.1 | −3.3 dB |
  | 0.25 | −6.0 dB |
  | 0.5 | −10.7 dB |
  | 1.0 | −40 dB (clamped at 0.01) |

  For guest pads and chords, `duckdepth` 0.1–0.25 with `duckattack` (recovery time) ≈ ⅛–¼ note (0.23–0.47 s at 128 BPM) matches the inference in section 3. The recovery is an exponential ramp, so it sounds faster at first than a linear one.
- **Kick sync with an external track:** run a silent `s("bd*4").duckorbit("2:3").postgain(0)` pattern locked to the track's beatgrid. Strudel's `cps` must equal track BPM / 60 / 4, and the cycle must be phase-aligned to the downbeat. For the realistic case of kick patterns other than four-on-the-floor, generate the trigger from detected kick onsets (librosa onset detection on a low-passed signal).
- **Equalising synths vs samples:** samples are ≈ +10.5 dB hotter than oscillators at the same `gain` (from the hard-coded 0.3). Either let the LUFS normaliser handle it, or apply a static pre-trim of ×0.3 to sample-based parts before role offsets.
- **`compressor` is per note.** It controls note transients but does **not** glue a part or a bus. With strong settings, the browser's automatic makeup gain (0.6-power rule) can raise loudness by several dB, so re-measure after enabling it.
- **True bus glue and a limiter** require host-app code outside superdough, for example by intercepting `destinationGain` or the orbit `output`. Insert `DynamicsCompressorNode` on the guest orbits' sum (threshold set for 1–2 dB GR, ratio 2, attack 0.01, release 0.1–0.3), then a second DynamicsCompressorNode as a peak catcher (ratio 20, knee 0, attack 0.001–0.003, threshold ≈ −1 dBFS). This is not a true brickwall limiter; for that, use an AudioWorklet. **[UNVERIFIED as an implementation detail; superdough has no API hook for it]**
- **Browser LUFS meter:** K-weighting via `IIRFilterNode` with BS.1770 coefficients recomputed for the context sample rate. `BiquadFilterNode` `highshelf` ignores Q, so a biquad approximation of the 1682 Hz shelf is inexact. Follow it with an AudioWorklet computing mean-square over 400 ms (momentary) and 3 s (short-term) windows. AnalyserNode's `getFloatTimeDomainData` can approximate this by polling, but its window is limited to fftSize ≤ 32768 samples (≈ 0.68 s at 48 kHz), so short-term loudness must be accumulated in JS.
- For **per-track tone**, the orbit-level `djf` gives one control for darkening or brightening the whole guest bus. A per-track brightness offset from the track's centroid could drive it. **[UNVERIFIED mapping; the `djf` filter curve was not inspected]**

### Gaps
- It was not verified whether the strudel.cc REPL (as opposed to the npm packages) installs a non-linear `setGainCurve`. If it does, the meaning of `gain` values differs between the REPL and this project's renderer.
- Browser implementation status of the new `makeupGain` AudioParam (Chrome, Firefox, Safari) was not checked. Older implementations apply automatic makeup gain unconditionally.
- The internals of the `djf` worklet (cutoff mapping, slope) and the orbit reverb's IR generation were not examined.
