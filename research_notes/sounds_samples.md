# Richer instruments for house / techno / progressive guest parts — free, redistributable sources

Researched 2026-11-06. Checked on primary pages (GitHub API licence fields, LICENSE/README files, Freesound pack pages, vendor FAQ/EULA, Strudel source on codeberg.org/uzu/strudel).
Legend: **[V]** checked on a primary source in this session · **[U]** not verified (secondary source, memory, or inference) · **FLAG** = NC / ND / unclear / not redistributable.

Constraints we're working within: published artifact ≤ 511 files, ≤ 16 MB per file; note-mapped mp3 sets of about 10–30 notes per instrument; licence must allow redistribution in a web app.
Rule of thumb: mono mp3 at 96–128 kbps is about 12–16 KB/s, so a 2 s note is about 30 KB. A 16-note instrument is about 0.5 MB, and 20 instruments × 16 notes = 320 files, about 10 MB.

---

## 1. Top 10 additions, ranked by house/techno richness per MB

| # | Addition | Licence | Cost in the artifact | Why it matters for house/techno |
|---|---|---|---|---|
| 1 | **Modular Samples on Freesound**: real analog polysynth multisamples (Juno‑6, Jupiter‑4, JX‑3P, JX‑8P, SH‑2, Korg Mono/Poly, DSI Tetra, Analog Four, Xpander, Z1…) | CC0 [V] | ~0.4–0.6 MB per patch at 12–16 notes; 8 patches ≈ 4–5 MB, ~120 files | This is the biggest win. Real analog basses, pads, stabs and leads, e.g. "JX‑3P Rave Stabbing", "Juno 6 Open Pad / Rich pluck / Pulse Bass", "JX‑8P Dark Pad Chorus", "Mono‑Poly Big Bass / Res Bass". They replace GM-style synth sounds directly. |
| 2 | **Superdough's own synths, plus AKWF single cycles as `wt_` wavetables** | Strudel code is AGPL (runtime only); AKWF is CC0 [V] | ≈0 MB for the synths; ~1.3 KB per AKWF cycle, so 40 cycles ≈ 60 KB | `supersaw` (unison/detune/spread), `pulse` (PWM), wavetable oscillators with 21 warp modes, FM, `vowel` filter. Trance plucks, supersaw chords and acid leads at no storage cost. Layering a sample with a synth voice is the cheapest way to get a "richer" sound. |
| 3 | **Surge XT rendered to multisamples** (factory presets or your own patches) | Output is yours, explicitly, even from factory presets [V] | Pick the size: 12–16 notes per patch, ~0.5 MB | Supersaw/trance plucks, M1-style house organ, piano stabs, hoover, risers/sweeps. Renders headlessly from Python with `surgepy`. |
| 4 | **uzu-drumkit** (in Strudel's default banks) | Unlicense / public domain [V] | 41 files, 2.6 MB raw wav (less as mp3) | Modern analog-processed electronic kit: bd ×8, sd, cp, hh, oh, rd, cr, rim, toms, misc. Clean licence. Redistribute it as-is. |
| 5 | **FreePats "Synthesizer" category** | CC0 [V] | 1–6 MiB FLAC per bank; resample to 12–16 notes ≈ 0.3–0.6 MB | Lately Bass (TX81Z simulation, a classic house bass), Synth Bass 1, Synth Strings 1/2, Sweep Pad, Choir Pad, Synth Brass 1/2 (DX7 Brass 7), Surge-made leads (fifths, bass+lead), Goblins/Soundtrack FX. Same project you already use, a different category. |
| 6 | **GeneralUser GS** instead of FluidR3. It's already wired into Strudel's `gm_*` sounds (webaudiofontdata) | Permissive custom licence (use, modify, redistribute) [V] | Small: ~15–100 KB per preset as hosted [V for one file]; you can also resample 12–16 notes | Better synth bass 1/2, saw/square leads, warm/poly/sweep pads, choir/voice oohs, EP1/EP2, drawbar/percussive organ (house organ), orchestra hit. Use only the `GeneralUserGS`/`FluidR3` variants (see §2). |
| 7 | **tidal-drum-machines** TR‑909 / 808 / 707 / 606 / 727, LinnDrum, DMX, SP‑12, MPC60, R8, RX5… (71 machines, 683 banks) | **FLAG: no licence file** [V] | Hot-link from Strudel's CDN instead of redistributing; 2,774 wav / 252 MB in the full repo | This is the canonical drum-machine palette for house and techno, already on Strudel's CDN. Use it via runtime fetch rather than copying it into the artifact (see §3). If the files must sit inside the artifact, use uzu-drumkit plus CC0 packs instead. |
| 8 | **Sonic Pi samples** | CC0 (Freesound sources plus Arovane donation) [V] | 207 flac; pick ~20 FX/texture files ≈ 1–2 MB | `ambi_*` pads/drones, `vinyl_*` (scratch, rewind, hiss), `glitch_*`, `elec_*` blips/pings, `bass_*` (drop, hit, trance), `loop_*`. Good for FX, transitions and texture beds. |
| 9 | **Greg Sullivan E‑Pianos** (Yamaha CP80, Hohner Pianet T, Wurlitzer EP200) **+ Salamander piano** (already on Strudel's CDN) | CC BY 3.0 [V] (both) | E-Pianos: 18 MB repo, so 16 notes ≈ 0.5 MB; Salamander: 29 notes already as mp3 on the CDN | CP80 and Salamander give 90s house piano stabs; Pianet T/Wurli give deep-house keys. Your Wurlitzer set is probably the EP200 from this repo [U], so CP80 and Pianet T are the new parts. |
| 10 | **Freesound CC0 electronic packs** (picked): Erokia "Electronic Samples Misc (CC0)", antoinevg "Vowels", SpankMyFilth "Acid Modulated Bass C2 Notes", bdu "Roland TR606 sampleset", ZeSoundResearchInc. "909 Kick Drums" | CC0 [V] (pack page shows CC0 on its sounds) | Small one-shots, ~0.5–2 MB per pack | Vowels for vocal chops, a 303-style acid source, 606 hats, 909 kicks, misc electronic hits/FX. |

Honourable mentions:
- **Karoryfer Caveman Cosmonaut** (CC0 [V]): Unitra transistor organ turned into a VA synth. Good for organ stabs and buzzy bass.
- **Karoryfer basses** (Meatbass, Growlybass, Swagbass, Fashionbass…, all CC0 [V]): electric basses for deep or nu-disco house.
- **VSCO 2 CE** (CC0 [V]): orchestral strings/brass for progressive breakdowns.
- **MuseScore General** (MIT [V]): its piano is the public-domain AKAI "Splendid Grand" [V], but most of its synth patches are still FluidR3, so it adds little for electronic parts.

---

## 2. Strudel's own default banks: what strudel.cc loads and what we could reuse

Source: `website/src/repl/prebake.mjs` and `packages/soundfonts/*` on codeberg.org/uzu/strudel [V]. The CDN base is `https://strudel.b-cdn.net`. Mirror JSONs for these banks are in `github.com/felixroos/dough-samples` (raw.githubusercontent).

| Bank (CDN json) | What's in it | Licence | Notes / unused opportunities |
|---|---|---|---|
| `piano.json` → Salamander Grand Piano V3 | 29 notes (A0…C8, every minor 3rd), mp3, velocity layer v8 | CC BY 3.0, Alexander Holm [V] | Ready-made, already in mp3. Use it directly for house piano stabs (with `.clip`, `.lpf`, short release). |
| `vcsl.json` → VCSL | 128 instruments (percussion, recorder, pipe organ, sax, harp, kalimba, marimba, vibraphone, glock, `clavisynth`, `fmpiano`, `organ_4inch/8inch/full`, `super64` harmonica…) | CC0 [V] | You already use VCSL. Possibly unused: `vibraphone_bowed`, `wineglass_slow` (pad-ish), `clavisynth`, `organ_full`, `handchimes`, `kalimba2–5` (plucks/arps). |
| `tidal-drum-machines.json` | 71 machines / 683 sound keys: RolandTR909, TR808, TR707, TR727, TR606, TR505, TR626, CR78, CR8000, R8, MC303, MC202, JD990, D110, SH09, System100, KorgM1, KorgKR55, KorgMinipops, LinnDrum, LinnLM1/LM2, Linn9000, OberheimDMX, EmuSP12, EmuDrumulator, AkaiMPC60, MPC1000, AkaiLinn, YamahaRX5/RX21/RM50/RY30/TG33, SimmonsSDS5/SDS400, CasioRZ1/SK1/VL1, BossDR55/110/220/550, AlesisHR16/SR16, SergeModular, EmuModular, DoepferMS404, MFB512, etc. [V] | **FLAG: repo has no licence** (GitHub reports none; README has no licence) [V] | Strudel's `.bank("RolandTR909")` aliases come from `tidal-drum-machines-alias.json`. Some banks are synth one-shots, not drums (KorgM1, JD990, MC202, SH09, System100). Check them for stab sources, but the same licence caveat applies. |
| `uzu-drumkit.json` | 16 groups / 41 files: bd(8), sd, cp, hh, oh, rd, cr, rim, lt/mt/ht, sh, tb, cb, brk, misc | **Unlicense** [V] | A clean, modern electronic kit, safe to redistribute. Contributors: Mot4i, Switch Angel (LA‑76-style compression), Ludens (modular misc). |
| `uzu-wavetables.json` | `wt_digital*` (by Glossing) and `wt_vgame` (AKWF) | No licence file [V]; the AKWF part is CC0 [V] | Shows the format: any sample key that starts with `wt_` is played as a wavetable oscillator (default frame 2048, `wt` position, `warp`, `warpmode`) [V in `wavetable.mjs` / `sampler.mjs`]. |
| `mridangam.json` | Mridangam strokes | CC BY‑SA 4.0 (Arthur Carabott) [V] | FLAG share-alike. Not relevant for house. |
| Dirt-Samples (selected folders in prebake; the full set via `github:tidalcycles/dirt-samples`) | 218 folders [V]. House-relevant ones: `house`(8), `techno`(7), `tech`(13), `909`, `808*`, `clubkick`, `hardkick`, `stab`(23), `rave`(8), `rave2`, `ravemono`, `hoover`(6), `juno`(12), `jvbass`(13), `bass1`(30), `bass3`, `moog`(7), `pad`, `padlong`, `pluck`(17), `arpy`(11), `sid`(12), `fm`(17), `future`(17), `bleep`, `noise2`, `speech`, `diphone`, `yeah`(31), `mouth`, `realclaps`, `linnhats` | **FLAG: no licence file** [V]; mixed provenance | Very useful (stabs, hoover, juno, jvbass, vocal "yeah"), but it has the same licence problem as tidal-drum-machines. Hot-link only. |
| `@strudel/soundfonts` → `gm_*` names | 128 GM programs. Each `gm_*` is a list of variants picked with `n`, served from `https://felixroos.github.io/webaudiofontdata/sound/<id>.js` (CORS `*`) [V] | webaudiofontdata repo: MIT [V]. Per variant: **GeneralUserGS** (338 entries, permissive [V]), **FluidR3_GM** (234, MIT/CC BY [V]); **Aspirin / Chaos / JCLive / SBLive / SoundBlasterOld / SBAWE32** (gray provenance, many from Creative Labs ROM banks) **FLAG** [U] | You can reuse this without hosting anything. Prefer the GeneralUserGS variant of `gm_synth_bass_1/2`, `gm_lead_2_sawtooth`, `gm_lead_1_square`, `gm_lead_8_bass_lead`, `gm_pad_warm/poly/sweep/halo/choir`, `gm_synth_strings_1/2`, `gm_synth_brass_1`, `gm_epiano1/2`, `gm_drawbar_organ`, `gm_percussive_organ`, `gm_voice_oohs`, `gm_choir_aahs`, `gm_orchestra_hit`, `gm_fx_*`. The variant index for each sound is set by its position in `gm.mjs`. |
| Built-in synths (no samples) | `sine/square/sawtooth/triangle`, `supersaw` (unison 1–100, detune, spread), `pulse` (pw), `bytebeat`, `white/pink/brown/crackle` noise, ZZFX sounds, wavetables (`wt_*`) with 21 warp modes, FM, `vowel` formant filter [V] | AGPL‑3.0 (code; runs at runtime) | Supersaw chords and plucks, PWM strings, noise risers (`s("white").hpf(sine.range(200,8000).slow(8))`), vowel-filtered saws as vocal-ish chops. |

**Can we reuse them directly?**
- Runtime fetch (hot-linking from `strudel.b-cdn.net`, `raw.githubusercontent.com/felixroos/dough-samples`, `felixroos.github.io/webaudiofontdata`) avoids the 511-file limit and avoids redistributing the files. **[U]** Strudel/Bunny CDN has not published a hot-linking policy, and Bunny bills per GB, so raw.githubusercontent / GitHub Pages mirrors are the politer source. **[U, must test]** The artifact's CSP may block `fetch`/media from these hosts. The Artifact rules list allowed script CDNs, not connect sources. Test one `fetch()` from a published artifact before relying on any of this.
- Copying files into the artifact (redistribution): OK for Salamander (CC BY, add attribution), VCSL (CC0), uzu-drumkit (Unlicense), GeneralUser GS and FluidR3 samples. **Not** OK, strictly, for tidal-drum-machines or Dirt-Samples (no licence).

---

## 3. Electronic-oriented sample sources (detail)

| Source | URL | Licence | Size | Instruments | Quality / notes | House/techno relevance |
|---|---|---|---|---|---|---|
| Modular Samples (Freesound user) | https://freesound.org/people/modularsamples/packs/ | CC0 shown on every sound [V] | 465 packs [V]; individual pack pages show ~17–49 sounds [V for the listing]; "over 50 GB of public domain content" claimed in sound descriptions [V text] | 62 Yamaha CS‑30L, 58 Jupiter‑4, 57 Korg Mono/Poly, 48 Korg Z1, 46 Chroma Polaris, 33 Akai AX80, 32 JX‑3P, 22 SH‑2, 17 JX‑8P, 14 Xpander, 14 DSI Tetra, 10 Analog Four, 10 MicroBrute, 8 HS‑80, 7 Juno‑6, 7 MFB Kraftzwerg, 6 Sequential MAX, 6 Moog Minitaur, plus modular kicks/snares/hats/toms/bass hits and reverb-tail drones [V] | Single notes from hardware, aif, file names give MIDI note and velocity (e.g. "Pulse Bass‑96‑127.aif") [V]. How the notes are spaced in each pack: **[U]**. A free Freesound login is needed to download (the owner does this; or use the Freesound API with an OAuth token). | ★★★★★ Real analog basses, pads, stabs, plucks, sync leads. |
| "Analog Archive" (SHIN NETTONOUMI / ijimi) | https://booth.pm/en/items/8874394 | CC0 stated [V] | ~32 GB, 392 patches, sfz-mapped, 17 synths [V] | A repack of the Modular Samples material with sfz mappings [V: credits modularsamples] | Handy because the sfz mappings are done, but it's huge and delivered via Google Drive. | Same as above. Use the sfz to choose notes. |
| FreePats — Synthesizer | https://freepats.zenvoid.org/Synthesizer/synth-bass.html (and synth-lead, synth-pad, synth-strings, synth-brass, synth-effects) | CC0 per bank [V] | 1–19 MiB per bank (FLAC/WAV/SF2) [V] | Lately Bass (Dexed TX81Z sim), Synth Bass 1 (ZynAddSubFX), Synth Lead 7 fifths & 8 bass+lead (made in Surge), Choir Pad, Sweep Pad, Synth Strings 1/2, Synth Brass 1/2 (DX7 "Brass 7" via Dexed), Goblins/Soundtrack FX [V] | Rendered from software synths, so clean and loop-friendly. "GM Sets not CC0" was noted in a KVR thread [U]. Check each bank page, though every synth bank I read was CC0. | ★★★★ |
| uzu-drumkit | https://github.com/tidalcycles/uzu-drumkit | Unlicense [V] | 41 files, 2.6 MB [V] | Electronic kit [V] | Modern, punchy, compressed | ★★★★ |
| tidal-drum-machines | https://github.com/geikha/tidal-drum-machines | **none** [V] FLAG | 2,774 wav, 252 MB [V] | 71 machines (list in §2) [V] | Standard vintage drum-machine one-shots. The recordings' provenance isn't documented. | ★★★★★ sound, ★ licence |
| Dirt-Samples | https://github.com/tidalcycles/Dirt-Samples | **none** [V] FLAG | ~170 MB repo [V] | 218 folders [V] | Mixed quality, lots of classic rave/house material | ★★★★ sound, ★ licence |
| Sonic Pi samples | https://github.com/sonic-pi-net/sonic-pi/tree/dev/etc/samples | CC0 (README) [V] | 207 files [V] | ambi, bass, elec, drum, bd, hat, perc, glitch, vinyl, loop, tabla, arovane, misc [V] | Clean, short, well trimmed | ★★★ FX/texture |
| Erokia – Electronic Samples Misc | https://freesound.org/people/Erokia/packs/26717/ | CC0 [V] | n/a [U] | Misc electronic hits/FX [U] | Erokia's packs are a staple CC0 source [U] | ★★★ |
| antoinevg – Vowels | https://freesound.org/people/antoinevg/packs/20716/ | CC0 [V] | small [U] | Sung/spoken vowels [U] | Source for vocal chops (pitch them through the sampler) | ★★★ |
| SpankMyFilth – Acid Modulated Bass C2 Notes | https://freesound.org/people/SpankMyFilth/packs/13626/ | CC0 [V] | n/a [U] | 303-style acid bass notes at C2 [U] | Single-pitch source, so pitch-shift it | ★★★ acid techno |
| bdu – Roland TR606 sampleset | https://freesound.org/people/bdu/packs/49/ | CC0 [V] | small [U] | TR‑606 kit [U] | Classic hats and percussion | ★★★ |
| ZeSoundResearchInc. – 909 Kick Drums | https://freesound.org/people/ZeSoundResearchInc./packs/9002/ | CC0 [V] | small [U] | 909 kicks [U] | — | ★★★ |
| Karoryfer Caveman Cosmonaut | https://github.com/sfzinstruments/karoryfer.caveman-cosmonaut | CC0 [V] | 95 MB repo [V] | Unitra B‑11 transistor organ as a VA synth (bass osc, 3 osc, unison) [V] | Raw oscillator samples, so build the patch in superdough (detune, ADSR, filter) | ★★★ organ stabs, bass |
| Karoryfer Cowsynth | https://github.com/sfzinstruments/karoryfer.cowsynth | CC0 [V] (readme also says royalty-free) | 14 MB [V] | Bagpipe samples used as oscillators: organ/pad/pluck variants [V] | Characterful, a bit odd | ★★ |
| Greg Sullivan E‑Pianos | https://github.com/sfzinstruments/GregSullivan.E-Pianos | CC BY 3.0 [V] | 18 MB [V] | Yamaha CP80, Hohner Pianet T, Wurlitzer EP200 [V] | Good EP multisamples (2004) | ★★★ |
| Signature Sounds free downloads | https://signaturesounds.org/blogs-free-download | CC0 per KVR thread [U] | [U] | [U] | Not checked on the site | ? |
| Musical Artifacts (search by licence) | https://musical-artifacts.com | per item | — | LibreArachno parts (Choir Pad, Halo Pad, Sweep, Polysynth, Orchestra Hit: **public domain** [V via API]; Metal Pad GPL‑3) | Community SF2s; check licence and provenance one by one | ★★ |

**Not redistributable / flagged (electronic packs):**
- SampleRadar (MusicRadar), 99Sounds, BPB (Bedroom Producers Blog) packs, Producer Spot, Studio Brootle: royalty-free for use in music only, with no right to redistribute the raw samples [U for each; the usual terms]. Don't use them.
- drolez.com Pro‑1 packs: "royalty free for use in your sound design projects or music productions", with nothing said about redistribution [V]. FLAG.
- Vital factory content: the EULA says "You are not permitted to redistribute presets, samples, wavetables … created from any unaltered VITAL AUDIO content" [V]. Samples from **your own / modified** Vital patches are allowed ("may be used to create samples for commercial products such as sample packs") [V]. FLAG for factory presets.

---

## 4. General MIDI / multi-instrument soundfonts better than FluidR3

| Soundfont | URL | Licence | Size | Verdict for electronic music |
|---|---|---|---|---|
| **GeneralUser GS 2.0.3** (2026‑02‑22) | https://github.com/mrbumpy409/GeneralUser-GS · https://www.schristiancollins.com/generaluser | Custom permissive: "use … without restriction … private or commercial … use it in your software projects, and … modify" [V]. Sample provenance is "not 100% sure" but none came from commercial packs [V]. Don't hot-link the author's download files; host your own copy [V]. | 32.3 MB sf2, 261 presets + 13 kits [V] | **Best GM upgrade.** Synth bass, leads, pads and organs beat FluidR3. Already available via Strudel `gm_*` (older GeneralUser version inside webaudiofontdata [U on version]). |
| MuseScore General 0.2 | https://ftp.osuosl.org/pub/musescore/soundfont/MuseScore_General/ | MIT [V] | 216 MB sf2 / 40 MB sf3 [V] | Piano = AKAI "Splendid Grand" (public domain via AKAI) [V]. Most other presets are still FluidR3Mono [V]. Low gain for synths. |
| FluidR3 GM (current) | gleitz/midi-js-soundfonts | CC BY 3.0 per gleitz [V]; MIT per MuseScore [V] | 148 MB | Baseline |
| Musyng Kite (gleitz mp3) | https://gleitz.github.io/midi-js-soundfonts/MusyngKite/ | "CC BY‑SA 3.0" per gleitz [V], but it's a compilation of samples of unclear origin [U] | 1.75 GB source | FLAG: gray provenance and share-alike |
| FatBoy (gleitz mp3) | https://gleitz.github.io/midi-js-soundfonts/FatBoy/ | "CC BY‑SA 3.0" per gleitz [V]; fatboy.site TLS failed, so not checked [U] | 320 MB source | Maybe usable, under share-alike |
| Arachno | musical-artifacts.com/artifacts/2045 | "various" [V]; built from Roland D‑50, Sound Canvas, Korg M1, Fairlight, E‑MU… [V] | ~150 MB [U] | **Reject**: commercial-source samples |
| Timbres of Heaven | — | not on Musical Artifacts; freeware with unclear sample sources [U] | ~400 MB [U] | **Reject** (unclear) |
| SGM (V2.01 / Pro) | musical-artifacts.com | "gray" [V for SGM‑Pro] | ~240 MB [U] | **Reject** |
| Jeux (pipe organ) | musical-artifacts.com/artifacts/7919 | CC BY‑NC [V] | — | **Reject** (NC) |
| Vintage Dreams Waves v2 | musical-artifacts.com/artifacts/248 | "copyright" [V] | — | **Reject** |
| Sonatina Symphonic Orchestra | https://github.com/peastman/sso | CC Sampling Plus 1.0 [V]: retired licence, allows sampling/transforming, restricts advertising use [U on details] | 1.3 GB [V] | FLAG. Prefer VSCO 2 CE. |
| VSCO 2 CE | https://github.com/sgossner/VSCO-2-CE | CC0 [V] | 2.3 GB [V] | Strings/brass/winds for progressive breakdowns. Safe. |
| Salamander Grand V3 | archive.org/details/SalamanderGrandPianoV3 | CC BY 3.0 [V] | Already on Strudel's CDN | Use it |
| jRhodes3c / 3d (1977 Rhodes Mk I) | https://github.com/sfzinstruments/jlearman.jRhodes3c | Free as an instrument, but **distributing the samples (e.g. in an app) is CC BY‑NC‑SA 4.0** [V] | 16 MB | **FLAG NC, don't ship** |
| Nice‑Keys | — | not found [U] | — | Unverified; skip |
| Discord SFZ GM Bank | https://github.com/sfzinstruments/Discord-SFZ-GM-Bank | No licence on GitHub [V]; a community CC0 effort per KVR [U] | 180 MB | Check before use |

**Gap:** I found no clean, permissive, high-quality **Rhodes** multisample. Options: GeneralUser GS EP1, Greg Sullivan Pianet T / CP80 (CC BY), or a Surge‑rendered FM Rhodes.

---

## 5. Rendering open synths to samples

| Synth | Licence of rendered output | How |
|---|---|---|
| **Surge XT** | Surge FAQ: "If you make songs, samples, sounds, patches … using Surge XT, you own it … regardless if you started a patch from scratch or used one of the factory presets … The output of Surge XT is yours" [V]. Factory patch folders: Basses, Brass, Chords, FX, Keys, Leads, Pads, Percussion, Plucks, Polysynths, Sequences… plus 37 third‑party patch sets [V]. | Build the Python bindings (`cmake -DSURGE_BUILD_PYTHON_BINDINGS=ON`, which gives the `surgepy` module) [V in README]. In a script: load a .fxp, play a note (e.g. 1.5 s hold plus a release tail), render to a numpy buffer, write a wav, then ffmpeg to mp3. Repeat for MIDI notes 36–84 in 3‑semitone steps (17 notes). [U: exact surgepy API names; see github.com/surge-synthesizer/surge-python examples] |
| Vital | Allowed from your own or modified patches; **not** from unaltered factory presets or wavetables [V EULA]. Code GPL‑3 [V]. | Render through a DAW, or with Spotify `pedalboard` / `DawDreamer` hosting the VST3 [U] |
| Dexed (DX7) | Dexed is GPL‑3 [V]. The copyright status of the Yamaha factory ROM cartridge voice data is legally unclear [U]. Rendered audio of a voice is generally treated as yours [U]. FreePats already ships CC0 Dexed renders (Lately Bass, Brass 7) [V], which shows the community treats this as OK. | `pedalboard` or `DawDreamer` with the Dexed VST3 and a MIDI note loop [U]. Prefer your own patches or the FreePats renders. |
| ZynAddSubFX / Yoshimi | GPL software; output yours [U]. FreePats renders are CC0 [V] | Use FreePats' existing renders |

Render recipe (any synth): notes every 3 semitones from C1 to C6 (about 20 notes); mono 44.1 kHz; trim leading silence; 2–4 s per note for pads (or a loopable sustain), 0.5–1 s for plucks/stabs; `ffmpeg -af loudnorm,afade=out` at 96–128 kbps; name files like `C2.mp3`, `Ds2.mp3` to match Strudel's `piano.json` convention.

---

## 6. Single-cycle waveforms and wavetables

| Library | URL | Licence | Size | Use in superdough |
|---|---|---|---|---|
| **AKWF‑FREE** (Adventure Kid Waveforms) | https://github.com/KristofferKarlAxelEkstrand/AKWF-FREE | **CC0 1.0** (LICENSE.md) [V] | ~4,358 single cycles per format set [V], 600 samples each, 16‑bit mono 44.1 kHz [V]; ~1.3 KB per wav [V], so the whole core set is ≈ 5.7 MB [U, derived]. Also re-cut for Surge (13,074 files), Elektron, Synthesis Technology E352 (2,539), etc. [V] | Folders: `bw_saw`, `bw_squ`, `bw_tri`, `bw_blended`, `fmsynth`, `epiano`, `eorgan`, `hvoice` (vocal formants), `overtone`, `stringbox`, `raw`, `oscchip`, `vgame`, `distorted`, `sinharm`… [V]. Register them as `wt_*` keys; superdough treats `wt_` samples as wavetables (default frameLen 2048 [V], so resample AKWF 600‑sample cycles to 2048 or pass the frame length) [U on passing a custom frameLen through `samples()`]. Strudel already ships `wt_vgame` from AKWF [V]. |
| uzu-wavetables `wt_digital*` | https://github.com/tidalcycles/uzu-wavetables | no licence file [V] | tiny | Usable on the CDN at runtime; licence unclear |
| WaveEdit Online (Synthesis Technology) | waveeditonline.com | The domain no longer resolves (ENOTFOUND) [V]. Was CC0 [U]. | — | Use the AKWF `--Synthesis-Technology` set instead [V exists] |
| Surge factory wavetables | surge repo `resources/data/wavetables` | Part of the GPL‑3 repo [V]; separate content licence unknown [U] | — | Render through Surge rather than copying the files |

---

## 7. Practical plan (suggested)

1. **Bass:** Modular Samples Mono/Poly "Big Bass" / JX‑3P "SnapBass" / Juno‑6 "Pulse Bass"; FreePats Lately Bass; superdough `supersaw`/`pulse` with `lpenv` for acid. Plus SpankMyFilth acid (CC0).
2. **Chords/stabs:** JX‑3P "Rave Stabbing", Jupiter‑4 "Baby brass", Salamander and CP80 piano stabs, GeneralUser GS percussive/drawbar organ, Caveman Cosmonaut organ. Render an M1-style organ in Surge.
3. **Pads:** Juno‑6 "Open Pad", JX‑8P "Dark Pad Chorus", Z1 "Bell Pad", FreePats Sweep/Choir Pad, GeneralUser warm/poly pad, VSCO2 strings for progressive.
4. **Leads/plucks/arps:** Juno‑6 "Rich pluck", AX80 "Easy Pluck", Z1 "Plucky", Surge‑rendered trance pluck/supersaw, native `supersaw`, AKWF `wt_` oscillators.
5. **Vocal chops:** antoinevg Vowels (CC0), AKWF `hvoice` wavetables, `vowel()` filter on saws, GeneralUser voice oohs / choir aahs, FreePats Choir Pad.
6. **Percussion:** uzu-drumkit (redistribute), tidal-drum-machines 909/808/707 (runtime fetch only), CC0 Freesound 606/909 packs.
7. **FX:** Sonic Pi `ambi_`/`vinyl_`/`glitch_`, Surge FX patches rendered (risers/sweeps), native noise risers + ZZFX.

Attribution file needed for: Salamander (Alexander Holm, CC BY 3.0), Greg Sullivan E‑Pianos (CC BY 3.0), FluidR3 (Frank Wen), GeneralUser GS (S. Christian Collins; licence text), the existing Wurlitzer (CC BY 3.0). CC0 and Unlicense sources need none, but crediting them is polite.

## 8. Open items / unverified
- The artifact CSP's `connect-src`/`media-src` for runtime sample fetches from strudel.b-cdn.net, raw.githubusercontent.com, felixroos.github.io: **must test**.
- Note spacing and length in Modular Samples packs; whether Freesound API batch download works within the owner's account limits.
- The `surgepy` API surface for offline rendering; `pedalboard`/`DawDreamer` instrument hosting (from memory, not re-checked).
- Licences of Signature Sounds, FatBoy, Discord SFZ GM Bank, Timbres of Heaven, Nice‑Keys.
- Which GeneralUser GS version webaudiofontdata contains (likely 1.4x; 2.0.x sounds better but would need your own extraction).
