# Tracker archives, synth/drum pattern collections and MIDI packs as training data (as of 2026-11-05)

Method note: about 20 search/fetch calls. modarchive.org returned HTTP 503 on every fetch (home, FAQ/licensing, FAQ), so Mod Archive facts come from secondary sources and are marked as such. Search-tool results are model summaries. Where only a snippet was seen, the item says so.

## 1. Tracker module archives (Mod Archive, ModLand, AMP, scene.org, Nectarine, Keygenmusic) and conversion to MIDI

### Takeaway
The Mod Archive and ModLand are the two big tracker corpora. Mod Archive is in the low hundreds of thousands of modules and ModLand has more than 400k files. Both are "private use only unless the author permits." Only the subset of modules whose uploader picked Public Domain or a Creative Commons licence is legally clean, and the CC subset is probably small. No public, licence-filtered tracker-to-MIDI dataset was found on HuggingFace or Zenodo. The only ML use found is an evaluation set in the Decomposer (Strudel) paper, built with private conversion code.

### Cited Findings
- **The Mod Archive:** founded February 1996 as an upload site for tracker artists. Wikipedia lists its content licence as "Public domain or Creative Commons licenses, if mentioned by the uploader". Reusing a file otherwise needs the author's permission. It has offered bulk downloads of archive files via BitTorrent since 2006. — [Wikipedia: Mod Archive](https://en.wikipedia.org/wiki/Mod_Archive)
- Mod Archive general rule (snippet-level): modules are "freely downloadable for private use only unless permission for other uses has been granted by the relevant copyright holders". The archive is described as holding "hundreds of thousands" of MOD/S3M/XM/IT files. — [search summary of Wikipedia / wikiwand](https://www.wikiwand.com/en/articles/Mod_Archive) (primary FAQ unreachable, 503)
- **Mod Archive API:** there is an API, wrapped by the R package `openmpt`. Downloading a module by database ID needs no key. Other functions need a key, obtained by registering on the ModArchive Forums. Keys have monthly request caps. For large quantities of files "it is advised to use torrent files". — [openmpt R package vignette: modarchive](https://pepijn-devries.r-universe.dev/openmpt/doc/modarchive.html)
- **ModLand:** the same vignette describes it as having over 400,000 files. Other sources call it "probably the largest module archive in the world", reachable by FTP (ftp.modland.com). — [openmpt vignette](https://pepijn-devries.r-universe.dev/openmpt/doc/modarchive.html); [maidavale.org: amiga mod file sources](https://maidavale.org/blog/amiga-mod-file-sources/)
- **ProTrackR (CRAN):** has a `modArchive` helper for fetching MOD files programmatically. This is evidence of existing tooling for automated access. — [ProTrackR modArchive docs](https://search.r-project.org/CRAN/refmans/ProTrackR/html/modArchive.html)
- **Decomposer (arXiv 2607.01849, 2026) uses ModArchive for genre-wise evaluation.** The paper "learn[s] to decompile symbolic music to programs" and is directly about Strudel: its training corpus "Strudel-Synth" pairs Strudel programs with rendered MIDI, and RL runs on unpaired MIDI. Its acknowledgment thanks Michael Freeman "for sharing his ModArchive-to-MIDI conversion code and resources". — [arXiv abs](https://arxiv.org/abs/2607.01849); [arXiv HTML](https://arxiv.org/html/2607.01849)
  - Search-snippet detail, not seen on the page itself: they crawled ModArchive across 51 genre tags, aiming for the top 100 by rating per genre. They kept .mod/.xm/.it/.s3m, mapped each tracker instrument to a General MIDI program and discarded non-pitched samples (speech, SFX). — [search summary of arXiv 2607.01849](https://arxiv.org/pdf/2607.01849). **UNVERIFIED:** the fetched HTML only showed the acknowledgment in the first 100k characters, so the details are probably in the appendix past that point.
- **KTH master's thesis (DiVA):** uses tracker (MOD) music for ML and describes converting MOD files to sequential training data. The extracted text was fragmentary. — [DiVA diva2:1597938](https://www.diva-portal.org/smash/get/diva2:1597938/FULLTEXT01.pdf)
- XM uses instrument-based envelopes and panning, while IT uses channel-based panning that commands can override. Parsers must handle these per-format semantics. — [Wikipedia: Module file](https://en.wikipedia.org/wiki/Module_file)

### Inferences
- **Legal usability:** only modules carrying an explicit CC0, CC BY or CC BY-SA licence, or Public Domain, should go into a redistributable or commercial model's training set. CC BY-NC might be acceptable for a strictly non-commercial research model. Modules with no licence ("private use only") should be excluded. ModLand has no per-file licence metadata, so it is not usable for clean training data. It is still useful for dedup or reference.
- **Electronic share:** the Mod Archive genre taxonomy includes Techno, Trance, House, Electronic and similar tags. Decomposer reportedly used 51 genre tags. A large electronic share is plausible because 1990s–2000s tracker scenes were heavily techno, trance and chiptune. No measured percentage was found.
- **Overlap with Lakh/Groove/GigaMIDI:** tracker modules are native pattern/step data, not MIDI, so overlap with Lakh or GigaMIDI should be small. Some GigaMIDI or Lakh files may themselves be conversions of modules (unverified).
- **Conversion difficulty: medium.**
  - Notes, rows and patterns are explicit, so a 4-bar slice is trivial: rows per beat comes from speed/tempo, and the typical 64-row pattern at 4 rows per beat equals 4 bars.
  - The hard parts are effect commands (portamento, arpeggio, retrigger, note-cut, volume slides, pattern-delay or speed changes mid-song) and channel-to-role assignment.
  - Instruments are samples. Drum vs bass vs lead role detection has to come from sample names (often "kick", "bd", "snare", "hh", "bass"), sample length and loop flags, pitch range and note-repetition statistics, or from audio classification of the sample itself. A heuristic plus a small classifier on the sample audio is feasible.
  - Tools commonly used: OpenMPT (GUI has "Export as MIDI"), libopenmpt (playback and pattern access), xmp/libxmp, and mod2midi-style scripts. **UNVERIFIED this session:** primary docs were not fetched.
- **Strudel relevance:** Decomposer is the closest prior work to "strudel-lm" and shows that ModArchive-to-MIDI conversion works for evaluation. Contacting its authors or Michael Freeman for the conversion code could save effort. Re-check the licence of any released material.

### Gaps
- Mod Archive primary pages (FAQ, licence, stats, torrent page) all returned 503. The exact module count, the share of modules with CC/PD licences, the current torrent availability and the size of each genre were not verified.
- No data was gathered on AMP (Amiga Music Preservation), scene.org /music, Nectarine or Keygenmusic. These are not covered here. Keygenmusic content is mostly unlicensed or anonymous rips and is likely unusable.
- No HuggingFace or Zenodo tracker-module dataset was found (one HF search returned nothing relevant). Absence was not exhaustively proven.
- Conversion-tool capabilities (OpenMPT MIDI export, libopenmpt pattern API, xmp) were not verified against primary docs.

## 2. Synth/sequencer pattern collections (TB-303, TR-808/909, Elektron/Novation/Arturia, arpeggiators)

### Takeaway
No open, licence-clear TB-303 or TR-808/909 pattern dataset was found in research repositories. What exists is commercial MIDI packs, old free pattern pages (some now hijacked by malware), and printed pattern books with unclear licences. The best permissive EDM pattern sources are the Patchbanks WaivOps datasets (CC BY 4.0), but most of them are audio. A few ship symbolic sidecars: JSON note numbers, plus an 8-bar MIDI chord set "NRG-CP" that is listed but not verified.

### Cited Findings
- **TB-303 commercial packs:** one seller offers 300+ MIDI pattern files for D16 Phoscyon, Behringer TD-3, ABL3 and other clones at €49. The NatLife "ACID 2" pack has 139 acid melodies for €30. — [Gumroad: TB-303 patterns MIDI](https://mysoundbanks.gumroad.com/l/nkfgp) (via search summary)
- A 2008 Synthtopia post linking free TB-303/TR-909/TR-808 patterns as standard MIDI files now carries a warning that the target site appears to have been taken over by a malware host. Do not use it. — [Synthtopia 2008](https://www.synthtopia.com/content/2008/12/23/free-patterns-and-midi-files-for-tb-303-tr-909-and-tr-808/)
- **Roland Cloud TB-303** lets users drag and drop audio/MIDI pattern data into a DAW. You could generate a corpus from your own programmed patterns, but there is no bundled open dataset. — [Roland RC TB-303](https://www.roland.com/DE/products/rc_tb-303/)
- **WaivOps (Patchbanks): 16 datasets, all CC BY 4.0.** Relevant EDM sets:
  - EDM-TR9: 3,780 WAV loops, TR-909, dance/house/techno, 4.8 GB.
  - EDM-TR8: 3,790 loops, TR-808, 4.4 GB.
  - EDM-HSE: 8,000 house drum loops, 7.6 GB.
  - EDM-TECH: 11,270 techno WAVs, 12.1 GB.
  - RTRO-DRM: 2,138 1980s electronic clips.
  - **NRG-CP: "30,943 MIDI files, 8 bars each", dance/trance/house/EDM chord progressions, 9.8 MB.**
  - Most sets were rendered from MIDI-programmed patterns, but only NRG-CP is described as a MIDI dataset. — [Patchbanks WaivOps page](https://www.patchbanks.com/waivops/)
- **EDM-TR9 on Zenodo:** 3,780 audio loops, TR-909 within dance/house/techno, "MIDI-programmed rhythms at various tempo rates". DOI 10.5281/zenodo.10278066. — [Zenodo 10278066](https://zenodo.org/records/10278066); [GitHub WaivOps-EDM-TR9](https://github.com/patchbanks/WaivOps-EDM-TR9)
- **EDM-HSE symbolic sidecar:** paired JSON files contain "MIDI note numbers (pitch) and tempo data". `key_map_drum_note_labels.json` maps note numbers to drum labels. Patterns came from an "algorithmic framework" of "probable drum notations commonly played by EDM music producers". Licence is CC BY 4.0. The page does not document whether the JSON has onsets or velocities. — [GitHub WaivOps-EDM-HSE](https://github.com/patchbanks/WaivOps-EDM-HSE); [Zenodo 13769544](https://zenodo.org/records/13769544)
- A WaivOps Lo-Fi Chords set (8,000 8-bar audio loops, CC BY 4.0, Zenodo, 2 Nov 2025) exists. No Zenodo record for "NRG-CP" was found by search. — [Zenodo 17819350](https://zenodo.org/records/17819350) (search summary)

### Inferences
- **NRG-CP is potentially the single best-fit permissive source for chords:** CC BY 4.0, about 31k 8-bar trance/house progressions, trivially sliceable into 4-bar lines. Its existence and download location need confirming (the patchbanks GitHub org URL returned 404). It is algorithmically generated, so expect low diversity and template-like voicings. Use it for fine-tuning and weight it down.
- **WaivOps drum sets:** if the EDM-HSE, TR8 and TR9 JSON sidecars contain onset positions, they become CC BY drum-step data in house/techno style. If they hold only note lists, then audio-to-MIDI drum transcription of perfectly quantised, machine-rendered loops is near-lossless and an option.
- **No open 303 corpus:** for acid basslines the realistic routes are:
  - the user's existing NeuralAcid set;
  - synthetic generation from 303-style rules (16 steps, accent, slide, octave flags);
  - self-programmed patterns exported from Phoscyon or RC TB-303.
- Commercial packs (Gumroad, NatLife) almost certainly use "royalty-free for music production" licences that do not cover redistribution or ML training. Treat them as forbidden unless the vendor grants written permission.

### Gaps
- Not researched: Acid Lab, the Phoscyon pattern bank licence, the "200 Drum Machine Patterns" book (René-Pierre Bardet) licence, 909/808 pattern books, Elektron/Novation/Arturia pattern dumps, arpeggiator preset banks. Their licences are unknown, so treat them as all-rights-reserved by default.
- The NRG-CP download URL and actual file contents are unverified.
- The EDM-HSE, TR8 and TR9 JSON schema (timing info present or not) is unverified.

## 3. MIDI pack sites and licences (Looperman, Cymatics, Unison, Splice, freemidi, bitmidi, midiworld, MuseScore, LANDR)

### Takeaway
Free "royalty-free" MIDI packs almost never permit redistribution or ML training. Looperman explicitly prohibits algorithm training and ML use of its content. No CC0 or CC BY house/techno MIDI pack site was found. Treat all commercial or freebie pack sites as excluded unless a specific pack states CC0 or CC BY.

### Cited Findings
- **Looperman terms:**
  - Registered users may use Loops only in "new and original recordings" (Derivative Works). The licence is non-transferable.
  - The terms state that "it is prohibited for anyone to use our content for the training or improvement of any algorithm". They also bar use of data "for machine learning purposes or algorithmic development without explicit authorization".
  - Scraping is prohibited.
  - **Verdict: forbidden.** — [Looperman Terms](https://www.looperman.com/help/terms)
- **AIVA terms:** licensees may not use its MIDI or audio compositions in any ML training dataset without a separate agreement. **Forbidden.** — [AIVA legal](https://aiva.ai/legal/1)
- **Loopmasters licence:** content stays the property of the licensors or company, and the licence is revocable on breach. It was not confirmed whether it addresses AI. — [Loopmasters License Agreement](https://help.loopmasters.com/hc/en-us/articles/27012699080348-Loopmasters-License-Agreement)
- **LANDR** publishes free EDM/house/techno chord-progression MIDI packs. The licence was not shown in results. — [LANDR EDM chord progressions](https://blog.landr.com/edm-chord-progression); [LANDR free MIDI packs](https://blog.landr.com/free-midi-packs)
- **Producer Hive** has a free pack of 50 one-bar chord-progression MIDIs (listed at $0). The licence was not shown. — [Producer Hive MIDI Chords](https://shop.producerhive.com/products/midi-chords-free)
- The Cymatics licence page URL returned 404, so it was not verified. — (attempted https://cymatics.fm/pages/license)

### Inferences
- **Default rule:** sample-pack "royalty-free" licences grant use inside your own musical works, not redistribution or derivative datasets. Since about 2024 many vendors have added explicit AI or ML clauses, as Looperman and AIVA did. Assume Cymatics, Unison, Splice and LANDR packs are not ML-usable unless the pack text grants it.
- freemidi.org, bitmidi.com and midiworld host mostly user-transcribed covers of copyrighted songs with no licence. They are legally unusable and also heavily overlap with Lakh.
- **Hooktheory-style progressions:** a better legal route is to generate progressions procedurally (chord-progression generators or rules) than to scrape such sites.

### Gaps
- Not verified on primary pages: Cymatics (404), Unison, Splice, freemidi.org, bitmidi, midiworld, MuseScore user-upload licence terms, Hooktheory API/TheoryTab terms.
- No CC0 house/techno MIDI pack was found despite a targeted search.

## 4. Drum-pattern datasets in research and on HF/Zenodo (beyond Groove and E-GMD)

### Takeaway
There are few permissive, EDM-specific symbolic drum corpora. The main HF loop corpora (GigaMIDI, MIDI-Loops, Monster MIDI) are non-commercial (NC) licences and overlap with Lakh. WaivOps (CC BY, audio plus JSON note sidecars) is the main EDM-specific permissive option. Groove Monkee (34,828 MIDI files, 1,454 electronic) is commercial.

### Cited Findings
- **GigaMIDI (Metacreation):** over 1.4M unique MIDI files and 7.1M loops. Licence CC BY-NC 4.0, so non-commercial only. — [HF GigaMIDI](https://huggingface.co/datasets/Metacreation/GigaMIDI)
- **asigalov61/MIDI-Loops:** 8-bar quality-labelled loops taken from LAKH and the Annotated MIDI Dataset. Licence cc-by-nc-sa-4.0, and it overlaps fully with Lakh. — [HF MIDI-Loops](https://huggingface.co/datasets/asigalov61/MIDI-Loops)
- **Monster MIDI Dataset:** tagged cc-by-nc-sa-4.0. — [HF Monster-MIDI-Dataset](https://huggingface.co/datasets/projectlosangeles/Monster-MIDI-Dataset)
- **Discover-MIDI:** the tooling repo is Apache-2.0. The dataset's own licence was not confirmed. — [GitHub discovermidi](https://github.com/asigalov61/discovermidi)
- **E-GMD:** CC BY 4.0, human drum performances (already held). — [Kaggle E-GMD mirror](https://www.kaggle.com/datasets/alexignatov/the-expanded-groove-midi-dataset)
- The "Can GAN originate new EDM genres?" paper used the commercial Groove Monkee Mega Pack GM³: 34,828 MIDI files, 1,454 labelled electronic. **Commercial, not redistributable.** — [arXiv 2011.13062](https://arxiv.org/pdf/2011.13062)
- **Zenodo "Dataset of Drum Patterns 2":** 10 patterns × 10 variations on an electronic kit. Tiny and not EDM. — [Zenodo 18395007](https://zenodo.org/records/18395007)
- WaivOps EDM-TR9, EDM-TR8, EDM-HSE and EDM-TECH: see section 2 (CC BY 4.0, audio, some JSON note data). — [Patchbanks WaivOps](https://www.patchbanks.com/waivops/)

### Inferences
- For a commercial or redistributable model, the NC corpora (GigaMIDI, MIDI-Loops, Monster) are out, or usable for internal research pretraining only. Check the project's legal stance.
- Most practical permissive EDM drum source: synthetic step patterns generated from genre rules (four-on-the-floor kick, offbeat open hats, 909 clap on 2 and 4, shuffle), plus the WaivOps sidecars, plus drum-role-extracted CC-licensed tracker modules.

### Gaps
- Not checked: DrumBench, "Lakh drums" subsets, BeatBank, Magenta drum datasets beyond GMD/E-GMD, ISMIR EDM drum corpora. Their status is unknown.
- No Zenodo or HF dataset of EDM drum patterns in MIDI with a permissive licence was found. Absence is not proven.
