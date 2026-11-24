# Pockets and gaps: finding places in a finished dance track where a guest part fits, and filling them like a producer

Scope: AI-generated Strudel guest parts (bass, chords/stabs, pads, arps, leads, vocal chops, percussion fills) layered live over a finished house/techno/progressive track. Inputs already available per bar: band activity (kick/low/mid/top), energy curve, rekordbox phrase labels, key, beat grid.

Source-quality note: the strongest material found is from MIR papers (AutoMashUpper ISMIR 2013, Mosaikbox ISMIR 2024, Huang et al. AAAI 2021 stem-compatibility). Producer-practice material is mostly from tutorial/education sites (Beat Kitchen, MusicRadar, Mixed In Key, Attack Magazine track breakdowns); no Sound On Sound article was retrieved. The Reiss-group masking papers were only reachable at abstract level (paywalled / withdrawn), so their formulas are NOT in these notes. Items labelled "[unverified]" or placed under Inferences are my own engineering proposals, not sourced facts.

## 1. Producer and live-performer practice: frequency slotting, call-and-response, rhythmic gaps, counter-melodies, when not to add, live layering

### Takeaway
Dance arrangement is built on 8-bar phrases where elements enter, leave or change at boundaries; fills live in the last 1–2 bars (or last 2 beats) of a phrase; supporting parts should answer a hook rather than sit on top of it, and breakdowns should be left sparse. Frequency slotting is conventional rather than exact: kick/sub below ~100 Hz, mud zone 250–500 Hz, presence 2–6 kHz, and everything that is not bass gets high-passed. Live layering (Traktor Remix Decks, loop packs) uses short, chopped loops and acapella fragments launched in a grid over a playing track, not whole parts.

### Cited Findings
**Phrase structure and where changes happen**
- The 8-bar phrase is the core structural unit; "listeners subconsciously expect changes at these boundaries"; elements are introduced, removed or transformed at 8-bar intervals (example: kick bar 1, hats bar 9, bass bar 17); give a new element 8 bars before adding the next; 4-bar transitions and 16-bar breakdowns are legitimate deliberate deviations — [Beat Kitchen: Arrangement and Energy](https://beatkitchen.io/guides/electronic-music/06-arrangement-and-energy/)
- Dance music is "almost always" in 8-bar phrases; fills belong at the ends of 8- or 16-bar blocks, not every two bars; fills are typically 1/2-bar or 1-bar drum variations pushing into the next downbeat — [Mixed In Key: how to arrange a dance music track](https://mixedinkey.com/captain-plugins/wiki/how-to-arrange-a-dance-music-track/) (as summarised by search; page not fetched in full)
- Transition tools: subtractive ("pull the hi-hat out for one bar before the breakdown", "drop the bass for the last two beats before a new section") and additive (reverse cymbal, filter sweep, drum fill or snare roll in the last 1–2 bars, risers/downers, a brief volume dip) — [Beat Kitchen](https://beatkitchen.io/guides/electronic-music/06-arrangement-and-energy/)
- Builds increase rhythmic density (snare rolls quarters → eighths → sixteenths), raise pitch, open filters; high-pass the low end as the build approaches the drop; short 4-bar builds before lesser sections, 16-bar builds before the main drop — [Beat Kitchen](https://beatkitchen.io/guides/electronic-music/06-arrangement-and-energy/)

**When NOT to add**
- Breakdowns: strip to "one or two elements" for ~16 bars and "resist the urge to fill it"; remove kick, bass and most rhythmic elements — [Beat Kitchen](https://beatkitchen.io/guides/electronic-music/06-arrangement-and-energy/)
- "Tracks that are all drops have no dynamics"; a drop after 8 bars of full arrangement "barely registers" — [Beat Kitchen](https://beatkitchen.io/guides/electronic-music/06-arrangement-and-energy/)
- DJ-friendly intros/outros carry 16–32 bars of kick and minimal elements (so they are mixing zones, i.e. the outgoing/incoming track will overlap there) — [Beat Kitchen](https://beatkitchen.io/guides/electronic-music/06-arrangement-and-energy/)
- Some classic techno uses no fills or dropouts at all and gets energy from section changes and percussion density (Model 500 "No UFO's"); Âme "Rej" also avoids fills, using synths for tension/release — [Attack: Model 500 No UFOs](https://www.attackmagazine.com/technique/deconstructed/model-500-no-ufos/); [Attack: Âme Rej](https://www.attackmagazine.com/technique/deconstructed/ame-rej/)

**Call-and-response / question-answer**
- Call-and-response is a structure where non-overlapping phrases alternate; in dance music the definition is looser and the alternation can be between synth sounds or processing effects — [Attack: Julio Bashmore Au Seve breakdown](https://www.attackmagazine.com/technique/the-breakdown/julio-bashmore-au-seve/)
- Future Music describes it as a figure followed by a complementary answering figure, with both playing together only near the end of the phrase — [Future Music via PressReader](https://www.pressreader.com/australia/future-music-9629/20161215/282144995976445) (search-snippet level)
- Write the support part to play after the hook, not on top of it; keep the call identical and vary only the response; when vocals are present, supporting parts should be more rhythmic than melodic, in a different register, or placed between vocal phrases; give each part an on/off pattern so silence is part of the groove — [Cursa: writing parts that leave space](https://cursa.app/en/page/music-production-fundamentals-writing-musical-parts-that-leave-space) (course-platform summary; low authority)
- Call-and-response can also be used within one layer, e.g. hats in a Paula Temple-style techno groove — [Attack: dark cinematic hypnotic techno](https://www.attackmagazine.com/technique/beat-dissected/dark-cinematic-hypnotic-techno/)

**Frequency slotting / giving a part room**
- In Âme "Rej" a synth drone is filtered down so the arpeggio has space — i.e. producers carve by filtering the existing layer rather than only placing the new one — [Attack: Âme Rej](https://www.attackmagazine.com/technique/deconstructed/ame-rej/)
- In the ROBPM remix of "Room 2 Move" a fill section at bar 56 drops the bass and leaves space for an acid line — [Attack: Linus Quick Room 2 Move](https://www.attackmagazine.com/technique/deconstructed/linus-quick-room-2-move-robpm-rmx/)
- Generic EQ charts (agree only roughly): sub 0–60 Hz "more felt than heard"; kick thump 50–80 Hz and click 2–4 kHz; bass body 60–120 Hz with growl ~700 Hz–1 kHz; mud ~250 Hz (some say 250–500 Hz), honk ~500 Hz; presence 2–6 kHz (upper mids 2–4 kHz, presence 4–6 kHz); vocals high-passed at 80–100 Hz, box 200–300 Hz, presence 3–5 kHz; high-pass non-bass elements to clear low-end mud; sidechain bass to kick — [Ledgernote EQ cheat sheet](https://ledgernote.com/columns/mixing-mastering/eq-cheat-sheet/); [Sonicbids EQ cheat sheet](https://blog.sonicbids.com/the-ultimate-eq-cheat-sheet-for-every-common-instrument); [Loopmasters EQ ranges](https://loopmasters.com/articles/2041-EQ-Ranges-For-A-Better-Mix-Part-1); [Teach Me Audio](https://www.teachmeaudio.com/mixing/techniques/frequencies/). Sources disagree on exact edges.
- Making room for vocals: leave space around the vocal; keep chord stabs short enough to leave rhythmic space for bass and percussion — [Melodigging: vocal house](https://www.melodigging.com/genre/vocal-house); [Jack Righteous House Prompt Vault](https://jackrighteous.com/blogs/vip-prompt-support/house-prompt-vault-groove-bass-vocals-arrangement) (marketing page; low authority)

**Live layering by DJ-producers**
- Traktor Remix Decks are a clip grid launched like Ableton Session View; acapella sections can be looped and stored in cells; tip: split vocals into separate pieces rather than loading the whole acapella, since a whole acapella is hard to play flexibly — [Bonedo: Traktor Remix Decks](https://www.bonedo.de/artikel/dj-basics-traktor-remix-decks); [ADSR: Traktor remix decks loops](https://www.adsrsounds.com/traktor-tutorials/traktor-remix-decks-loops/)
- Punch mode lets you switch loops without retriggering/restarting them; per-column effects give per-loop control for transitions — [ADSR](https://www.adsrsounds.com/traktor-tutorials/traktor-remix-decks-loops/)
- Commercial "Traktor decks" techno loop packs are sold explicitly to "ride loops over your favorite tracks" — [Loopmasters: 1937 Audio Injection Traktor Decks Techno](https://www.loopmasters.com/products/1937-Audio-Injection-Traktor-Decks-Techno)
- Where to source loops/acapellas/instrumentals for live remixing — [DJ TechTools](https://djtechtools.com/2015/04/29/where-to-find-loops-acapellas-and-instrumentals-for-remixing/); loops-in-DJ-set workshop — [Bonedo: Loops im DJ-Set](https://www.bonedo.de/artikel/kickstart-digital-djing-4-loops)

### Inferences
- For our system, the producer rules translate into: (a) change the guest part only at 8-bar (or rekordbox phrase) boundaries; (b) the "fill slot" is the last 1–2 bars or last 2 beats of each 8/16-bar phrase, especially before a phrase-label change; (c) a breakdown/intro/outro is a "don't fill or fill with one sparse element" zone, not an invitation to add a full part; (d) a guest lead/chop should answer the track's hook (play in the bars/beats where the hook rests), not double it.
- The two Attack examples (bass dropped for an acid line; drone filtered for an arp) suggest the strongest pockets are where the original track itself removes an element — a "band goes silent" event in our per-bar band words is a direct pocket signal for a part in that band.
- Live layering practice favours short loops (1–4 bars) and chopped fragments over long through-composed parts; our Strudel parts should likewise be short repeating cells that can be dropped in/out at phrase boundaries.

### Gaps
- No Sound On Sound or Attack article giving a general "frequency slotting by role" rule for techno/house was found; the band edges come from generic EQ charts.
- No source found on the specific "space between kick and clap" or offbeat-gap practice with numbers; Ableton live-set (Session View) layering over finished tracks not covered by retrieved sources.
- No source gave a maximum number of simultaneous elements (Beat Kitchen explicitly does not).

## 2. Analysis methods to find gaps automatically (band occupancy, onset density per 16th, masking, key/chords per bar, vocal activity, mashup/automix MIR)

### Takeaway
The MIR mashup/automix literature scores compatibility as a weighted sum of per-beat correlations: harmonic (chroma cosine, with key rotation), rhythmic (onset or drum-hit vectors on a sub-beat grid), spectral balance (low/mid/high band energies), plus timbre and key distance. Mosaikbox (ISMIR 2024) gives concrete weights, thresholds and vocal-clash rules. Psychoacoustic masking metrics from Reiss's group exist but their formulas were not retrievable; a learned stem-compatibility model (Huang et al. 2021) beat AutoMashUpper in listening tests.

### Cited Findings
**AutoMashUpper (Davies, Hamel, Yoshii, Goto; ISMIR 2013 / IEEE TASLP 2014)**
- Pipeline: NNLS Chroma (Sonic Annotator) → beat-synchronous tuned semitone spectrogram and 12-d chroma; phrase-level segmentation by stacking beats into downbeat-synchronous frames, Itakura-Saito self-similarity, Gaussian checkerboard novelty, peaks = phrase boundaries; phrase sections are whole numbers of bars — [AutoMashUpper ISMIR 2013](https://archives.ismir.net/ismir2013/paper/000077.pdf)
- Harmonic similarity: for phrase p of K beats of input i, chroma matrix C(i,p) (12×K) is rotated by r semitones (r user-set in 0..±6) and compared at every beat increment k against every song n by cosine similarity H_n(r,k) = C(i,p,r)·C(n,p,k) / (‖C(i,p,r)‖‖C(n,p,k)‖); matching whole K-beat matrices (not single frames) implicitly captures aligned chord changes — [AutoMashUpper ISMIR 2013](https://archives.ismir.net/ismir2013/paper/000077.pdf)
- Mashability (2013 version): M_n(r,k) = H_n(r,k) + γ if |1 − T_i/T_n| ≤ η (tempo ratio within user tolerance η), else H_n(r,k); γ = 0.2 "was found to give favourable results"; selected song is pitch-shifted by −r semitones and beat-matched with Rubberband — [AutoMashUpper ISMIR 2013](https://archives.ismir.net/ismir2013/paper/000077.pdf)
- The 2014 journal version defines mashability from harmonic and rhythmic similarity and spectral balance, computed locally between phrase sections over a range of key shifts — [AutoMashUpper TASLP 2014 (INESC TEC record)](https://repositorio.inesctec.pt/items/ee22c2f1-26ac-47eb-be17-e963535d115b); described as "a weighted sum of harmonic compatibility, rhythmic compatibility and spectral balance, each computed as a correlation between two beat-synchronous representations" — [Huang et al. 2021, arXiv 2103.14208](https://arxiv.org/pdf/2103.14208)
- Third-party implementation reporting harmonic matching and spectral balance separately: [migperfer/AutoMashupper (GitHub)](https://github.com/migperfer/AutoMashupper); harmonic-compatibility code following Bernardes/Davies/Guedes: [migperfer/harmonic_compatibility](https://github.com/migperfer/harmonic_compatibility)

**Mosaikbox (Sowula & Knees, ISMIR 2024) — automatic DJ mixing with rule-based stem modification**
- Rhythm: drum transcription (Southall et al.) instead of onset functions ("poor performance in polyphonic audio"); beat divided into 12 sub-beats (to capture straight, swing, shuffle, offbeat patterns, following AMU); kick/snare/hat positions quantized → 3-d binary vector of length K·12; rhythmic similarity = mean over the 3 drum dimensions of the fraction of sub-beat positions where seed and candidate match (Iverson bracket), stricter than AMU's cosine — [Mosaikbox](https://repositum.tuwien.at/bitstream/20.500.12708/212628/1/Sowula-2024-Mosaikbox%20Improving%20Fully%20Automatic%20DJ%20Mixing%20Through%20Rule-ba...-vor.pdf)
- Timbre: 28-d vector of stacked MFCCs + spectral flatness + "dirtiness", cosine similarity, computed once per phrase — [Mosaikbox](https://repositum.tuwien.at/bitstream/20.500.12708/212628/1/Sowula-2024-Mosaikbox%20Improving%20Fully%20Automatic%20DJ%20Mixing%20Through%20Rule-ba...-vor.pdf)
- Key: KeyFinder; key distance D = minimum semitone distance between tonics; M_K = 1 if D = 0 else D^−1 — same source
- Harmonic similarity and spectral balance across low/mid/high bands "based on the approach by Davies et al." — same source
- Mixability M_c(k) = ω_R·M_R + ω_T·M_T + ω_K·M_K + ω_H·M_H + ω_L·M_L with ω_R = 0.3, ω_T = 0.75, ω_K = 0.2, ω_H = 0.2, ω_L (spectral balance) = 0.1 (found by informal testing); lyrics similarity weight 0.25 added no improvement; evaluated over the 64 beats after the seed phrase — same source
- Choosing the cue point by raw argmax produced transitions at non-downbeats or at 7/9/15/17-downbeat offsets; fix: only consider shifts at candidate segment boundaries — same source
- Mixing rules: loudness to −14 LUFS; max tempo change ±8%; transition = 16 downbeats (8 before, 8 after); bass-swap EQ extended to highs; if timbral similarity at cue < 0.95 treat mids as clashing and cut mids of the playing song; if rhythmic similarity ≥ 0.95 attenuate bass less; if rhythmic similarity < 0.95 apply drum-stem modification; HT-Demucs 4-stem separation — same source
- Vocal activity / clash rule: split the separated vocal stem at "silent" sections lasting ≥ 1 s with loudness below −40 dBFS; discard vocal segments shorter than 400 ms; two excerpts clash if their vocals overlap for more than 2 s → attenuate the playing song's vocals. Listening test: rule-based stem removal "significantly enhances the perceived quality" — same source

**Learned stem compatibility (Huang, Wang, Smith, Song, Wang; ByteDance/QMUL, AAAI 2021)**
- Random mashups from separated stems with key and tempo auto-matched = positives (plus original songs); random combinations with key and/or tempo unadjusted = negatives; harmonic candidates within ±3 semitones; beat offset randomly by ±1 s for some negatives; semi-supervised with unlabeled data; PreMixNet (per-stem input) + unlabeled data performed best and beat AutoMashUpper in a listening test — [Huang et al. 2021](https://arxiv.org/pdf/2103.14208)
- Failure mode noted: global time-stretching causes beat-phase drift in later bars when tempo varies within a clip — same source

**Masking-aware mixing (Reiss group) — abstract level only**
- Ronan et al. propose a multitrack masking metric "inspired by the MPEG psychoacoustic model"; used in an automatic mixing framework it reduced inter-channel masking and improved perceived quality and clarity; subgrouping helped. Note: the arXiv version was withdrawn in 2021 over an IP question — [arXiv 1803.09960](https://arxiv.org/abs/1803.09960v3)
- Hafezi & Reiss (JAES 63(5), 2015) built a simplified masking measure from best practice, with offline (constant EQ from time-averaged masking) and real-time systems; they found existing objective masking measures ill-suited to perceived masking in multitrack music — [AES E-Library 17637](https://www.aes.org/e-lib/browse.cfm?elib=17637); [Bohrium summary](https://www.bohrium.com/paper-details/autonomous-multitrack-equalization-based-on-masking-reduction/814627736487198720-4600)
- Pestana & Reiss: cross-adaptive spatial unmasking that maps time-frequency bins to azimuth — [DAFx 2014](https://dafx14.uni-erlangen.de/papers/dafx14_pedro_d._pestana_a_cross_adaptive_dynamic_.pdf)
- A later speech-enhancement mixer by Liu/Ai/Reiss evaluates masking with the ITU-R BS.1387 (PEAQ) perceptual model — [Liu et al. JAES 2025](https://joshreiss.github.io/documents/2025/Liu2025JAESAutomaticMixingSpeech.pdf)

### Inferences
- [unverified design proposal] A practical, cheap "masking estimate" without the paywalled metrics: compute per-bar band energies of the track in ~8 bands (e.g. 20–60, 60–120, 120–250, 250–500, 500 Hz–1 k, 1–2 k, 2–6 k, 6–16 kHz, edges taken from the EQ charts above) and, for a candidate part, its expected band profile (rendered offline or from a per-role template); masking cost per band ≈ min(track_dB, part_dB) weighted by how close they are (e.g. penalty when |track_dB − part_dB| < 6 dB and both above a floor). This mimics the "clash if both loud in same band" logic of bass-swap EQ in Mosaikbox.
- Mosaikbox's 12-sub-beat drum vectors are the closest published analogue to our "onset density per 16th position"; for 4/4 house/techno a 16-step grid per bar is sufficient (12 only matters for swing/triplets).
- Vocal activity in the original track can be detected the Mosaikbox way (Demucs vocal stem + −40 dBFS / 1 s silence gaps / 400 ms minimum), and its 2 s overlap rule gives a direct threshold for "our vocal chop must not overlap the track's vocal for > 2 s".
- The learned approach (Huang et al.) shows key/tempo mismatch is the dominant negative signal; since our guest parts are generated in-key and on-grid, harmonic and rhythmic compatibility are mostly guaranteed by construction, so the remaining risk is spectral/rhythmic crowding — i.e. pockets matter more than "mashability".

### Gaps
- Exact AutoMashUpper 2014 formulas for rhythmic compatibility and spectral balance (band edges, weights) were not retrieved (TASLP PDF host refused connection).
- Ronan/Reiss masking metric equations and Hafezi/Reiss band ranking and dB thresholds are paywalled or withdrawn; not available here.
- No retrieved paper scores "where an added part fits" in a finished stereo mix directly; all found work scores song-to-song or stem-to-stem compatibility.

## 3. Turning analysis into decisions: role, register, rhythm (which 16ths), density

### Takeaway
Published systems give templates for the decision layer: weighted-sum scores with hard gates (tempo tolerance, key distance, vocal-overlap > 2 s, similarity thresholds of 0.95) and decisions restricted to phrase boundaries. Producer practice supplies the priors: change at 8-bar boundaries, fill the last 1–2 bars, answer rather than double the hook, keep breakdowns to 1–2 elements, high-pass non-bass parts.

### Cited Findings
- Decisions should be snapped to structural boundaries: Mosaikbox restricts transition candidates to segment boundaries because free argmax produced unnatural 7/9/15/17-downbeat placements — [Mosaikbox](https://repositum.tuwien.at/bitstream/20.500.12708/212628/1/Sowula-2024-Mosaikbox%20Improving%20Fully%20Automatic%20DJ%20Mixing%20Through%20Rule-ba...-vor.pdf)
- Threshold-gated stem decisions: rhythm sim < 0.95 → modify drums; timbre sim < 0.95 → cut mids of the playing track; vocal overlap > 2 s → attenuate a vocal — same source
- Weighted sum + bonus gate form: M = H + γ (γ = 0.2) if tempo within tolerance — [AutoMashUpper](https://archives.ismir.net/ismir2013/paper/000077.pdf)
- Element-entry spacing of 8 bars, fills in last 1–2 bars, "drop the bass for the last two beats before a new section", breakdown with 1–2 elements — [Beat Kitchen](https://beatkitchen.io/guides/electronic-music/06-arrangement-and-energy/)
- With vocals present, a supporting part should be rhythmic rather than melodic, in a different register, or between vocal phrases — [Cursa](https://cursa.app/en/page/music-production-fundamentals-writing-musical-parts-that-leave-space)
- Chord stabs short to leave rhythmic space for bass/percussion — [Jack Righteous](https://jackrighteous.com/blogs/vip-prompt-support/house-prompt-vault-groove-bass-vocals-arrangement) (low authority)

### Inferences
All items below are [unverified design proposals] derived from the findings above; thresholds are starting points to tune by ear.

**Role from band occupancy (per 8-bar phrase, using our existing band words)**
- low band off while kick on (bass removed, as in the Room 2 Move fill) → bass/acid line is the best candidate role; register octave 1–2 (≈ 40–130 Hz fundamentals); avoid kick hits (play offbeat 8ths or 16ths 3/4 of each beat).
- mid band off/weak while low and top on → chords/stabs or pad; register octave 3–4 (≈ 130–520 Hz) — but high-pass/keep thin to stay out of 250–500 Hz mud if the track's low is heavy.
- top band off/weak → hats/shakers/percussion or arp in octave 5–6 (≈ 520 Hz–2 kHz fundamentals with harmonics into 2–6 kHz presence).
- all bands on and energy in top quartile ("drop", busy) → do nothing or only a 1-bar percussion fill / single answering stab at phrase end.
- breakdown / no kick → at most one sparse element (pad swell or one-shot vocal chop), consistent with "resist the urge to fill it".
- intro/outro (DJ mixing zones) → avoid, because another track will usually be overlapping there.

**Rhythm (which 16ths) from onset-per-step occupancy**
- Compute for the track an occupancy histogram over 16 steps per bar per band (fraction of the phrase's bars with an onset at step s in band b). Candidate steps for the guest part = steps where occupancy in the part's target band < ~0.25 [unverified]. In 4-on-the-floor, steps 0/4/8/12 are kick; clap/snare at 4 and 12; the classic house "gap" steps are offbeats 2/6/10/14 (open hat) and the 16ths 3/7/11/15 and 1/5/9/13.
- Call-and-response in time: if the track's lead/vocal is active in bars 1–2 of a 4-bar group, place the answer in bars 3–4 (or in the last 2 beats of the 4-bar group); both together only near the end of the phrase (per Future Music).
- Fills: schedule in the last 1 bar (or last 2 beats) of an 8/16-bar phrase, with higher priority when the next rekordbox phrase label differs.

**Density**
- Target density inverse to the track's: e.g. guest notes per bar ≈ clamp(k·(1 − track_onset_density_in_band), 1, 8), and the guest part should never raise per-bar energy above the phrase's existing peak except in a build.
- Change density only at phrase boundaries; in builds, increase subdivision (quarters → 8ths → 16ths) following the build convention.

**Score shape for picking (role, register, rhythm) per phrase**
- score = w_band·(1 − occupancy of target band) + w_step·(fraction of chosen steps that are free) + w_harm·(key match: 1 if same key/relative, else 1/semitone-distance as in Mosaikbox) − w_vox·[overlap with track vocal > 2 s] − w_busy·(energy percentile) ; initial weights could mirror the published practice of weighting the dominant failure mode highest. Gate: never place on a non-phrase boundary.

### Gaps
- No published source found that maps band occupancy to instrument role or octave for an added part; the mapping above is a design proposal.
- No numeric "maximum simultaneous layers" or density limits found in producer sources.

## 4. Cheap-to-compute per-bar signals (browser or offline Python/librosa)

### Takeaway
Everything the published systems use reduces to per-beat/per-bar features that are cheap offline: beat-synchronous chroma, band energies, onset or drum-hit vectors on a sub-beat grid, MFCC/flatness timbre vectors, and (more expensively) source separation for vocal activity. Source separation (Demucs) is the only costly step and should be done offline.

### Cited Findings
- Beat-synchronous chroma and semitone spectrogram (NNLS Chroma) are the base representation for harmonic matching and phrase segmentation — [AutoMashUpper](https://archives.ismir.net/ismir2013/paper/000077.pdf)
- Onset detection functions perform poorly in polyphonic audio for rhythm comparison; a drum transcription model gives kick/snare/hat hits on a 12-per-beat grid — [Mosaikbox](https://repositum.tuwien.at/bitstream/20.500.12708/212628/1/Sowula-2024-Mosaikbox%20Improving%20Fully%20Automatic%20DJ%20Mixing%20Through%20Rule-ba...-vor.pdf)
- Timbre: MFCC + spectral flatness + dirtiness (28-d), computed once per phrase "due to high computational demands" — same source
- Vocal activity: HT-Demucs vocal stem, −40 dBFS silence threshold, ≥ 1 s gaps, ≥ 400 ms segments — same source
- Loudness normalisation to −14 LUFS before comparing/mixing — same source

### Inferences
- [unverified, from general librosa knowledge, not checked against docs in this session] Offline Python per bar: `librosa.beat.beat_track` (or the existing rekordbox grid) → `librosa.util.sync` to aggregate `librosa.feature.chroma_cqt` per beat/bar; `librosa.stft` magnitude summed into fixed Hz bands per 16th step for band occupancy; `librosa.onset.onset_strength(..., aggregate)` per band (multi-band onset envelopes) sampled at 16th positions for per-step occupancy; `librosa.feature.mfcc` and `spectral_flatness` per phrase; Demucs for vocal stem then RMS in dBFS against −40 dB.
- [unverified] In the browser: Web Audio `AnalyserNode` or an offline FFT (e.g. Meyda) over the decoded buffer gives band energies per 16th cheaply; precomputing offline and shipping a per-bar JSON (bands × 16 steps, chroma 12-d, vocal flag, energy) is likely simpler and matches the current "per-bar words" design.
- Since we already have kick/low/mid/top band words per bar, the highest-value additions are (1) per-16th-step occupancy per band (not just per bar), (2) a vocal-activity flag per bar (Demucs offline), and (3) per-bar chroma to avoid clashing with chord changes the global key does not capture.

### Gaps
- No benchmark found of computation cost for these features in a browser; Meyda/Web Audio suitability is unverified.
- No source verified for multi-band onset strength parameters (band edges, thresholds) tuned for house/techno.
