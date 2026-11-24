# Stem/multitrack datasets, loop datasets, and synthetic symbolic data for a 4-bar house/techno pattern model

Research date: 2026-11-05. Budget-limited pass (about 15 tool calls). Items marked **[UNVERIFIED]** come from prior knowledge and were not confirmed on a primary page in this pass.
Already in hand (not re-researched): MTG-Jamendo, WaivOps EDM-HSE / EDM-TECH, FSL10K, Slakh2100, NeuralAcid, Strudel-Synth.

## 1. Stem / multitrack datasets (parts already isolated): size, licence, electronic share, access

### Takeaway
No open, training-permitted, EDM-specific stem dataset turned up. The usable multitrack sets are small (hundreds of songs at most), mostly pop/rock, and almost all are non-commercial or research-only. The single largest pool of free techno/house stems (Native Instruments' 65 Stems tracks) has no stated licence, and the "Mixing Secrets" library explicitly forbids AI training. For this project, stems are a small, research-only supplement, not a main data source.

### Cited Findings
**MoisesDB**
- 240 tracks. The ISMIR paper says 45 artists; the Music.AI press release says 47 artists (the two sources disagree). 12 high-level genres, Electronic among them. 3 to 10 stems per track, organised in a two-level taxonomy with 11 top-level stems — [ISMIR 2023 paper](https://archives.ismir.net/ismir2023/paper/000073.pdf); [Music.AI blog](https://music.ai/blog/news/introducing-moisesdb-the-ultimate-multitrack-dataset-for-source-separation-beyond-4-stems)
- Licence: the GitHub README says CC BY-NC-SA 4.0. The search snippet for the same repo's metadata mentioned an "NC-RCL" licence, and the GitHub API reports "NOASSERTION". The licence is non-commercial for research use only. To get it, download from the Music.AI research site, set the `MOISESDB_PATH` variable, and use the `pip install git+https://github.com/moises-ai/moises-db.git` loader — [GitHub moises-ai/moises-db](https://github.com/moises-ai/moises-db)
- A secondary summary describes the genre mix as mostly Western pop/rock with only a little electronic. I could not get an exact electronic track count — [emergentmind summary](https://www.emergentmind.com/topics/moisesdb-dataset)

**MUSDB18 / MUSDB18-HQ / DSD100**
- 150 full tracks (about 10 h) with drums, bass, vocals and "other" stems. The MUSDB18 audio is compressed (bandwidth limited to 16 kHz); HQ is the same content as uncompressed WAV — [sigsep MUSDB18 page](https://sigsep.github.io/datasets/musdb.html)
- Licence: "can only be used for academic purposes"; "educational purposes only", no commercial use without permission. Some tracks carry their own CC BY-NC-SA 3.0 licences. Zenodo lists HQ as "Open", but the original requires an access request — [sigsep](https://sigsep.github.io/datasets/musdb.html); [Zenodo MUSDB18-HQ](https://zenodo.org/records/3338373)
- DSD100 is the predecessor and a subset (100 of the 150 tracks) **[UNVERIFIED in this pass]**. Electronic share is low (pop/rock dominated) **[UNVERIFIED count]**.

**MedleyDB 1.0 / 2.0**
- v1: 122 multitracks **[count UNVERIFIED this pass]**. v2 adds 74 new multitracks, for 194 in total according to Papers with Code. The ISMIR 2016 text says 254, which conflicts — [Papers with Code MedleyDB 2.0](https://paperswithcode.com/dataset/medleydb-2-0); [Zenodo record](https://zenodo.org/record/1715175)
- Licence: CC BY-NC-SA 4.0 for v1 (per Papers with Code), described as "royalty-free ... for non-commercial and academic research". The Zenodo record for the 2.0 audio is "Restricted" (access on request) — [Papers with Code](https://PapersWithCode.com/dataset/medleydb); [Zenodo](https://zenodo.org/record/1715175)
- Genres are mostly acoustic, rock, jazz and classical; electronic share is small **[UNVERIFIED]**. Includes pitch annotations (melody f0), which helps transcription.

**"Mixing Secrets" Free Multitrack Download Library (Cambridge Music Technology)**
- The official FAQ says **no** to using the multitracks to train an AI engine. That needs individual licensing deals with each contributor. Research use has not been formally agreed with contributors either. **This licence blocks ML training.** — [cambridge-mt FAQ](https://cambridge-mt.com/ms3/mtk-faq/) (the page itself returned HTTP 403 to my fetcher; finding taken from the search-engine extract of the FAQ)
- A community scraper repo exists ([carlmoore256/Cambridge-Multitrack-Dataset](https://github.com/carlmoore256/Cambridge-Multitrack-Dataset/blob/main/README.md)), and some papers (e.g. Diff-MSTC, ACM CHI EA 2025) have trained on this data. Neither grants permission — [ACM](https://dl.acm.org/doi/10.1145/3706599.3721167)

**OnAir Music Dataset**
- V4 has 11 songs (5 from "LoFi Vol. 3" plus 6 miscellaneous), each with its mix and all stems. Licence is **CC BY-SA 4.0** (training allowed with attribution; share-alike may apply to derived datasets). Distributed as Git LFS zips — [GitHub sevagh/OnAir-Music-Dataset](https://github.com/sevagh/OnAir-Music-Dataset)
- Tiny; the genre is lo-fi/production music, not techno.

**Native Instruments free Stems pack**
- 65 Stems tracks, about 1.5 GB, "derived from selected MASCHINE expansions". Genres are techno, house, funk, trap, DnB, dubstep and more. Stems are usually bass / drums / vocals / melody — [NI Stems page](https://www.native-instruments.com/en/specials/stems/)
- **The page gives no licence or terms of use.** It does not say whether AI training or redistribution is allowed, so treat it as all rights reserved by default. This is the most genre-relevant stem source found, but it is not cleared for training.

**Other EDM stem datasets (2023-2026)**
- I found no public EDM-specific stem dataset. A 2025 sample-identification paper trains on a **proprietary** set of 21k multitrack recordings (1,350 h) that includes an "electro" genre; it is not released — [arXiv 2510.11507](https://arxiv.org/html/2510.11507v2)

**URMP, Bach10, MIR-1K**
- Not checked in this pass. From prior knowledge: URMP has 44 classical chamber pieces with per-instrument audio and MIDI scores; Bach10 has 10 Bach chorales (4 parts); MIR-1K has 1,000 Chinese karaoke vocal clips (vocal and accompaniment). None of them is electronic, and none is relevant to bass/lead/chords/drums in house **[UNVERIFIED]**.

### Inferences
- Ranked by usefulness for a house/techno symbolic model: NI Stems (most relevant, licence unknown, so do not train without clearance) > MoisesDB electronic subset (CC BY-NC-SA, research only, small) > MUSDB18/MedleyDB (academic only, few electronic tracks) > OnAir (CC BY-SA, tiny). Mixing Secrets is excluded because training is explicitly forbidden.
- Every usable stem set carries NC or academic-only terms. A model trained on MIDI transcribed from them would inherit the NC risk, so these sets suit pretraining experiments, not a commercial release.
- The total electronic content across all of these is probably in the tens of songs, far less than WaivOps EDM-HSE/TECH and Slakh already provide. Transcription accuracy from stems is better, but the volume gain is negligible.
- Converting stems to MIDI: bass and lead stems → monophonic pitch tracking (Basic Pitch or pYIN); drum stems → ADT model; "other/melody" stems are often polyphonic pads plus FX and harder to transcribe. MoisesDB's fine-grained sub-stems (e.g. bass synth vs bass guitar) make bass extraction easier.

### Gaps
- Exact electronic track count in MoisesDB, MUSDB18 and MedleyDB was not found.
- The governing MoisesDB licence (CC BY-NC-SA vs NC-RCL) is inconsistent across pages; check the LICENSE file inside the downloaded package.
- The NI Stems pack's EULA (likely in the download or the NI general EULA) was not found; ask NI directly before using it.
- The Cambridge-MT FAQ wording could not be fetched directly (HTTP 403); verify it manually.

## 2. Loop datasets beyond FSL10K (audio and MIDI loops)

### Takeaway
Looperman now explicitly forbids ML training and scraping, so it is excluded. The strongest options are MIDI loop sets extracted from big MIDI corpora: GigaMIDI's about 7.1M detected loops (CC BY-NC 4.0, gated), Lakh-derived loop sets built with published heuristics you can reimplement yourself, and the Groove MIDI drum dataset (CC BY 4.0, recorded on an electronic kit). Extracting 4-bar loops from Lakh/MetaMIDI with the published detectors is the most scalable licence-tolerable route.

### Cited Findings
**Looperman (audio loops)**
- The terms say "it is prohibited for anyone to use our content for the training or improvement of any algorithm", including "machine learning purposes ... without explicit authorization". Scraping and automated data extraction are also prohibited, and so is redistribution of content. Registered users may only use loops in new original recordings — [Looperman terms](https://www.looperman.com/help/terms)
- **This blocks ML training. Do not use it.** Note that Han et al. (ISMIR 2022) trained their loop detector on 1,000 Looperman loops; that was before these terms or in conflict with them, so do not copy that approach — [arXiv 2208.05605](https://export.arxiv.org/abs/2208.05605)
- Related: the Loopmasters licence also prohibits using its products to train generative AI, which shows the Splice-like commercial sample stores are generally closed — [Loopmasters licence](https://help.loopmasters.com/hc/en-us/articles/27012699080348-Loopmasters-License-Agreement)

**GigaMIDI (and its loops)**
- 7,108,181 loops of 1 to 8 bars, extracted from GigaMIDI tracks with an adapted loop detection algorithm — [emergentmind summary](https://www.emergentmind.com/topics/gigamidi); [GigaMIDI GitHub](https://gh.r-mj.com/Metacreation-Lab/GigaMIDI-Dataset)
- The HF dataset is **CC BY-NC 4.0** and gated ("auto" approval after agreeing to share contact information) — [HF Metacreation/GigaMIDI](https://huggingface.co/datasets/Metacreation/GigaMIDI) (licence tag read via the HF API)
- **GigaMIDI-Loop**: a *synthetic* set of 1.3M loops generated by a fine-tuned MIDI-GPT, with controls for expressiveness (NOMML level) and instrument group. No separate licence was found — [HF card](https://huggingface.co/datasets/Metacreation/GigaMIDI); [Metacreation newsletter Feb 2025](https://www.metacreation.net/newsletters/february-2025)

**Lakh-derived MIDI loops (papers with reproducible methods)**
- Han et al. 2021 (VQ-VAE): a loop is taken where bar 1 and bar 5 of the window are highly correlated; non-4/4 files are dropped. This gave **150,750 loops from 114,444 LMD MIDIs** — [arXiv 2111.07657](https://arxiv.org/pdf/2111.07657)
- Han et al. 2022 (ISMIR): a cross-modal One-Class Deep SVDD loop detector extracts 8-bar loops from LMD — [arXiv 2208.05605](https://arxiv.org/pdf/2208.05605)
- SYMPLEX (2024) builds **4-bar loops from MetaMIDI**, matching the target format of this project — [arXiv 2405.12666](https://arxiv.org/pdf/2405.12666)
- "Learning Normal Patterns in Musical Loops" (2025) continues the loop-detection line — [arXiv 2505.23784](https://arxiv.org/pdf/2505.23784)
- The loop sets from these papers do not appear to be redistributed as datasets **[UNVERIFIED]**; reimplementing the heuristic on Lakh is easy.

**Groove MIDI Dataset (GMD) / E-GMD (drums)**
- GMD: 13.6 h, 1,150 MIDI files, more than 22,000 measures of human drumming played on a Roland TD-11 electronic kit. **CC BY 4.0** (training and commercial use allowed with attribution). The MIDI-only download is about 3 MB — [Magenta GMD](https://magenta.tensorflow.org/datasets/groove)
- E-GMD: 444.5 h of audio over 43 kits, 1,059 unique sequences, CC BY 4.0. For symbolic work, Magenta recommends the original GMD — [Magenta E-GMD](https://magenta.tensorflow.org/datasets/e-gmd); [Zenodo](https://zenodo.org/record/4300943)

**Other MIDI corpora that could feed loop extraction**
- Los Angeles MIDI Dataset: the repo is Apache-2.0, but that covers the code. The MIDI files are scraped content, so provenance is unclear — [GitHub](https://github.com/asigalov61/Los-Angeles-MIDI-Dataset)
- MidiCaps: text captions for Lakh MIDI, **CC BY-SA 4.0**; useful for conditioning on genre or tempo tags — [HF amaai-lab/MidiCaps](https://huggingface.co/datasets/amaai-lab/MidiCaps)

### Inferences
- GMD is drum-only and played by humans (mostly rock, funk and jazz styles **[UNVERIFIED style share]**). Its timing and velocity are useful for the "humanised" drums of progressive house, but straight techno 4/4 grooves must come from elsewhere (WaivOps, procedural generation).
- Most scalable loop pipeline: Lakh/MetaMIDI → filter 4/4 → bar-1-vs-bar-5 correlation (Han 2021) or 4-bar self-similarity → split per instrument role (bass, lead, chords, drums) → filter by tempo (118 to 135 BPM) and by MidiCaps genre tags. It yields a large volume quickly, but the electronic share of Lakh is small, so it fits pretraining, not fine-tuning.
- GigaMIDI loops are ready-made and very large, but CC BY-NC means research or pretraining experiments only.
- I found no open "Splice-like" set of loops licensed for training.

### Gaps
- Groove2Groove (Cífka et al.) was not separately verified. The 2019 style-translation paper does use synthetic Band-in-a-Box data (see section 4), but whether that data is redistributable and under what licence is unknown.
- I found no "FMA loops" or "LoopNet" dataset.
- A loop-specific FSL10K subset is already in hand. I did not search further for other Freesound loop subsets (Freesound licences are per-file CC0/BY/BY-NC).

## 3. Synthetic / procedural generators and open symbolic models: licences on outputs

### Takeaway
Most open symbolic generators carry permissive code and weight licences: Anticipatory Music Transformer, SkyTNT midi-model, Moonbeam and Aria are Apache-2.0; Text2midi, MuseCoco and NotaGen are MIT. MIDI-GPT is Open RAIL-M (use restrictions), and MIDI-LLM inherits the Llama 3.2 licence. None found claims rights over generated MIDI. Their training data (Lakh, GigaMIDI, etc.) has murky provenance, though. For house/techno, a rule-based procedural generator is the cleaner and more controllable source of synthetic 4-bar patterns; these models are better used to add diversity in pretraining.

### Cited Findings (licences read from the GitHub API / HF API on 2026-11-05)
| Model | Code licence | Weights licence | Notes |
|---|---|---|---|
| Anticipatory Music Transformer (`jthickstun/anticipation`, HF `stanford-crfm/music-large-800k`) | Apache-2.0 | Apache-2.0 | Multitrack MIDI infilling, trained on Lakh — [GitHub](https://github.com/jthickstun/anticipation); [HF](https://huggingface.co/stanford-crfm/music-large-800k) |
| MIDI-GPT (Metacreation) | — | **Open RAIL-M** (use-based restrictions) | The paper says legal status of the model is unclear; trained on GigaMIDI-like data — [arXiv 2501.17011](https://arxiv.org/pdf/2501.17011). Predecessor MMM: [jeffreyjohnens/MMM](https://github.com/jeffreyjohnens/MMM) (no licence on GitHub) |
| Text2midi (AMAAI-Lab) | MIT | Apache-2.0 (HF tag) | Text → MIDI, trained on MidiCaps (Lakh) — [GitHub](https://github.com/AMAAI-Lab/Text2midi); [HF](https://huggingface.co/amaai-lab/text2midi) |
| MuseCoco (in `microsoft/muzic`) | MIT | (not checked) | Text → attributes → MIDI — [GitHub](https://github.com/microsoft/muzic) |
| NotaGen | MIT | MIT | ABC notation, classical sheet music; low relevance — [GitHub](https://github.com/ElectricAlexis/NotaGen); [HF](https://huggingface.co/ElectricAlexis/NotaGen) |
| SkyTNT midi-model | Apache-2.0 | Apache-2.0 | MIDI event transformer, multitrack — [GitHub](https://github.com/SkyTNT/midi-model); [HF](https://huggingface.co/skytnt/midi-model) |
| Moonbeam | Apache-2.0 | (not checked) | Pretrained on 81.6K h (~18B tokens) of "freely available" MIDI — [GitHub](https://github.com/guozixunnicolas/Moonbeam-MIDI-Foundation-Model); [arXiv 2505.15559](https://www.arxiv.org/pdf/2505.15559) |
| Aria (EleutherAI) | Apache-2.0 | Apache-2.0 | **Piano only** — [GitHub](https://github.com/EleutherAI/aria); [HF](https://huggingface.co/loubb/aria-medium) |
| ChatMusician | (no licence on GitHub) | MIT (HF tag) | ABC notation; built on LLaMA-2, so the LLaMA-2 licence likely also applies **[UNVERIFIED]** — [HF](https://huggingface.co/m-a-p/ChatMusician) |
| MIDI-LLM (ISMIR '26) | NOASSERTION | **llama3.2** licence | Text → MIDI on Llama-3.2-1B — [GitHub](https://github.com/slSeanWU/MIDI-LLM); [HF](https://huggingface.co/slseanwu/MIDI-LLM_Llama-3.2-1B) |
| Magenta (MusicVAE, GrooVAE etc.) | Apache-2.0 | Apache-2.0 **[weights UNVERIFIED]** | MusicVAE samples 2-bar/16-bar melodies, drums, trios; GrooVAE trained on GMD — [GitHub magenta/magenta](https://github.com/magenta/magenta) |
| Magenta RealTime (now "Magenta RealTime 2") | Apache-2.0 | CC BY 4.0 | **Audio** model, not symbolic; outputs would need transcription — [GitHub](https://github.com/magenta/magenta-realtime); [HF](https://huggingface.co/google/magenta-realtime) |

- Training-data caveat: GigaMIDI (CC BY-NC 4.0) and Lakh-based corpora are scraped. Generator licences do not cure upstream copyright questions — [HF GigaMIDI](https://huggingface.co/datasets/Metacreation/GigaMIDI); [MIDI-GPT paper](https://arxiv.org/pdf/2501.17011)

**Rule-based / procedural generators**
- I did not verify any specific open "procedural EDM generator" project, Wolfram Tones licence, or generative-grammar house generator in this pass **[GAP]**. NeuralAcid and Strudel-Synth (already in hand) cover part of this space.

### Inferences
- Apache-2.0 / MIT models (AMT, SkyTNT, Text2midi, Moonbeam) can generate MIDI at scale with no output restriction stated. Open RAIL-M (MIDI-GPT) and Llama-licensed (MIDI-LLM, possibly ChatMusician) outputs need a check of their use-restriction and naming clauses before you train a model you will distribute. From memory, the Llama 3.x licence requires "Llama" in the name of models trained on its outputs **[UNVERIFIED]**.
- These general models are trained mostly on Lakh-style pop/rock/classical MIDI, so their samples drift away from house idioms. Their best use is AMT/MIDI-GPT-style **infilling conditioned on real house loops** (e.g. given drums plus bass, infill chords) to multiply scarce genre data, not unconditional generation.
- For the 4-bar bass/lead/chords/drums target, a hand-written procedural generator gives exact labels, full genre control and no licence issues. It can encode four-on-the-floor kicks, off-beat hats, 16th-note rolling or off-beat basslines, minor-key i-VI-VII / i-iv vamps, and stab chords. This is a few hundred lines of code, which fits the user's "delegate mechanical work to the local model" rule.

### Gaps
- Licences on MuseCoco weights and Moonbeam weights were not checked separately.
- Wolfram Tones terms were not checked; I am not aware of an export or bulk API **[UNVERIFIED]**.
- No open, maintained "procedural house/techno MIDI generator" repository was found in this pass.

## 4. Does training on synthetic symbolic music help small models? Model-collapse risk

### Takeaway
I found no study that tests model collapse specifically for symbolic music. The evidence is indirect. Synthetic MIDI has worked as a primary training source for narrow tasks (Band-in-a-Box style translation; GigaMIDI-Loop trained on MIDI-GPT outputs). General LLM research shows collapse comes from *replacing* real data recursively, and that *accumulating* synthetic data alongside real data avoids it. Synthetic-to-real gaps remain large in audio-domain tasks.

### Cited Findings
- Cífka et al. (ISMIR 2019) trained style translation entirely on synthetic accompaniments generated with Band-in-a-Box/RealBand and called the data an effective resource; this is the Groove2Groove line — [ISMIR 2019](https://archives.ismir.net/ismir2019/paper/000071.pdf)
- GigaMIDI-Loop: 1.3M synthetic loops generated by fine-tuned MIDI-GPT were used to train a loop-generation transformer — [HF GigaMIDI](https://huggingface.co/datasets/Metacreation/GigaMIDI); [Metacreation Feb 2025](https://www.metacreation.net/newsletters/february-2025)
- MIDI-RWKV saw degenerate output where a repeated-bar token dominated on sparse, repetitive tracks, so the authors excluded those sections from training. This is directly relevant to loop-heavy techno data — [arXiv 2506.13001](https://arxiv.org/pdf/2506.13001)
- Chamber Ensemble Generator: a generative model was used to create "limitless" high-quality MIR training data (audio rendered from symbolic) — [arXiv 2209.14458](https://arxiv.org/pdf/2209.14458)
- Drum transcription trained only on MIDI-rendered synthetic audio still showed a synthetic-real gap too large to rely on synthetic data alone (2026) — [arXiv 2601.09520](https://arxiv.org/html/2601.09520v1)
- General: one-round training on synthetic data did not necessarily degrade LLM pretraining, and the effect depends on the type of synthetic data — [arXiv 2510.01631](https://arxiv.org/pdf/2510.01631). Collapse can be avoided by accumulating synthetic data with real data rather than replacing it (Gerstgrasser et al. line) — [arXiv 2502.18049](https://arxiv.org/pdf/2502.18049); [arXiv 2607.17043](https://arxiv.org/pdf/2607.17043)

### Inferences
- For a small model: (1) mix procedural/model-generated data with real data and never train recursively on your own model's outputs; (2) cap the synthetic share and put it mainly in pretraining or curriculum stages; (3) fine-tune the last stage on real house/techno (WaivOps, transcribed EDM stems) only.
- The repeated-bar degeneracy found in MIDI-RWKV is a specific risk for 4-bar loops. Deduplicate identical bars and patterns, add a diversity filter (e.g. pitch-class and rhythm entropy thresholds), and avoid over-weighting trivially repeating synthetic loops.
- Procedural data is low-entropy by construction. Its value is in teaching the grammar (grid, role separation, key). Musical "taste" must come from real data.

### Gaps
- No controlled experiment on synthetic vs real data for symbolic EDM generation was found; you would have to run your own ablation.
- No quantitative figure on the best synthetic:real ratio for symbolic music was found.
