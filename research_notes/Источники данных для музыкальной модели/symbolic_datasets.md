# New symbolic music datasets for pretraining (beyond our existing set)

Scope: datasets NOT already in our set (Lakh/MidiCaps, Groove, PDMX, Discover, LAMD, Godzilla, GigaMIDI/MetaMIDI, Aria-MIDI, MAESTRO, GiantMIDI, POP909, Slakh, E-GMD, XMIDI, SymphonyNet, MetaScore, IrishMAN, Nottingham, KernScores, Wikifonia, HLSD/Hooktheory, DadaGP). Checked 2026-11-05. "Unverified" = not confirmed on a primary page in this pass.

## 1. Chord-progression datasets (Chordonomicon, ChoCo, Billboard, jazz corpora, Hooktheory, iReal Pro)

### Takeaway
Chordonomicon is the one large new chord source (~680k progressions with genre tags), but its licence is contradictory (CC BY-NC 4.0 on HF vs Apache-2.0 on GitHub) and it is scraped from user-generated sites, so treat it as non-commercial at best. ChoCo (20k JAMS files, mostly CC BY 4.0) is the cleanest unified chord corpus, but it overlaps heavily with things we already have (Wikifonia, Nottingham) and adds iReal Pro, Band-in-a-Box, Billboard, Weimar and others. Jazz sources (WJazzD, iRb, the iReal Pro JSON dumps) are small but have clean licences.

### Cited Findings
- **Chordonomicon**: HF dataset `ailsntua/Chordonomicon`. 679,807 rows in the train split ("more than 666,000 contemporary music compositions"), 264 MB CSV/Parquet. Columns: `chords` (with section tags like `<verse_1>`, `<chorus_1>`), `release_date`, `genres`, `decade`, `rock_genre`, `artist_id`, `main_genre`, `spotify_song_id`, `spotify_artist_id`. Licence tag: **cc-by-nc-4.0**. Direct download from the HF "Files" tab. — [HF Chordonomicon](https://huggingface.co/datasets/ailsntua/Chordonomicon)
- Chordonomicon progressions were built by "scraping various sources of user-generated progressions and associated metadata". Neither the paper abstract nor the README names the source sites. Paper: arXiv:2410.22046. — [arXiv 2410.22046](https://arxiv.org/abs/2410.22046); [GitHub](https://github.com/spyroskantarelis/chordonomicon)
- The Chordonomicon GitHub repo is listed as **Apache-2.0**, and it does not say whether that covers the data or only the code. This conflicts with the HF CC BY-NC 4.0 tag. No genre breakdown or electronic share is published on either page. — [GitHub](https://github.com/spyroskantarelis/chordonomicon); [HF](https://huggingface.co/datasets/ailsntua/Chordonomicon)
- **ChoCo (Chord Corpus)**: 20,080 JAMS files (2,283 audio-derived, 17,803 symbolic) with 20,530 Harte-notation chord annotations, out of 60,263 annotations overall. It covers 18 sub-corpora. Audio-derived: Isophonics, JAAH, Billboard, Chordify, Robbie Williams, Uspop2002, RWC-Pop, Weimar Jazz DB, Schubert-Winterreise. Symbolic: Wikifonia, iReal Pro, Band-in-a-Box, When in Rome, Rock Corpus, Mozart Piano Sonata, Jazz Corpus, Nottingham, Real Book. Licence: **CC BY 4.0**, except the Chordify, Mozart Piano Sonata and JAAH parts, which are **CC BY-NC-SA 4.0**. Access: GitHub Releases (JAMS), Docker image `andreamust/choco:latest` with include/exclude options, or a SPARQL/RDF knowledge graph. — [ChoCo GitHub](https://github.com/smashub/choco)
- **McGill Billboard**: 890 annotated slots, 740 distinct songs. Files are `salami_chords.txt` (structure plus chords) and HTK-style LAB. — [McGill DDMAL page](https://ddmal.music.mcgill.ca/research/The_McGill_Billboard_Project_(Chord_Analysis_Dataset)) (the direct fetch returned 404; facts come from the search snippet). The CC0 licence for v2.0 is stated only by a third party (unverified). — [RPubs analysis](https://rstudio-pubs-static.s3.amazonaws.com/361368_73c2d5a9ca924b7f9efa9541b38b4226.html). Billboard is also inside ChoCo. — [ChoCo](https://github.com/smashub/choco)
- **Weimar Jazz Database (WJazzD)** v2.1 (DB version 2.2): 456 solo transcriptions, shipped as SQLite with chord and beat annotations, plus a ZIP of unquantized MIDI for all solos. Licence: **Open Database License (ODbL)**, "released under the Open Data Commons". The same page offers the EsAC Folk Song Database v1.0 (7,821 songs, SQLite, "released with kind permission of Ewa Dahlig-Turek"). — [Jazzomat download page](https://jazzomat.hfm-weimar.de/download/download.html)
- **iRb Jazz Corpus**: more than 1,000 jazz standards (chord changes) in Humdrum format, from Ohio State University's Cognitive and Systematic Musicology Lab. It is described as freely available for research. The exact licence was not found (unverified). — [ISMIR 2018 paper / search snippet](https://ismir2018.ismir.net/doc/pdfs/177_Paper.pdf); [sharp11-irb npm](https://www.npmjs.com/package/sharp11-irb)
- **Jazz Harmony Treebank**: expert hierarchical analyses of complete jazz standards based on the open iRealPro collection, released as JSON (Harasim et al., ISMIR 2020). — [Zenodo 4245406](https://zenodo.org/records/4245406); [ISMIR 2020 poster](https://program.ismir2020.net/poster_2-06.html)
- **iReal Pro**: `mikeoliphant/JazzStandards` holds JSON versions of iReal Pro lead sheets. The public playlists (user-submitted) are at irealpro.com/main-playlists. Song count and licence were not verified. — [nostatic blog 2022](https://blog.nostatic.org/2022/); iReal Pro data is also in ChoCo — [ChoCo](https://github.com/smashub/choco)
- **Hooktheory API**: it exposes only chord-probability data (next-chord probabilities, and songs containing a given progression) through OAuth2 bearer tokens obtained with a hooktheory.com login. The docs say "a full dump of TheoryTab data is not available right now". — [Hooktheory API docs](https://hooktheory.com/api/trends/docs)
- **TheoryTab crawl (~10,148 songs, XML)** and its MIDI conversion are on Google Drive via the wayne391 list. This overlaps with our HLSD/Hooktheory data. — [wayne391 list](https://github.com/wayne391/symbolic-music-datasets)

### Inferences
- **Turning chords into training lines.** Chord sequences can be rendered into chord and bass tracks: pick a voicing, put the root (or inversion bass) in the bass, and apply rhythmic templates such as 4-on-the-floor root notes, offbeat bass or arpeggios. With Chordonomicon's ~680k progressions this gives a lot of harmonic diversity, but the rhythms would be synthetic. That fits a "harmony prior" pretraining stage or chord-conditioning, not learning real groove. Chordonomicon has no durations or rhythm (it is a chord-token sequence with section tags), so each chord would get an assumed length, for example one bar.
- Because of its NC licence and scraped user-generated source, Chordonomicon should only go into a non-commercial model, or be used for statistics only (for example progression priors).
- ChoCo is the best legal "one-stop" chord corpus. Once we exclude our duplicates (Wikifonia, Nottingham) and the NC parts, roughly 15k+ CC BY files remain. This is an estimate: we have no per-partition counts.
- Electronic share across all chord corpora: no data. Chordonomicon has a `main_genre` column, which we could use to filter for electronic/dance (needs a local check).

### Gaps
- Chordonomicon: actual source sites (Ultimate Guitar is suspected but not confirmed on a primary page), genre distribution, and which licence is authoritative.
- McGill Billboard licence: not confirmed on a primary page (the official page returned 404).
- iRb and iReal Pro JSON dumps: exact licence and counts not verified.

## 2. Game music and chiptune (NES-MDB, VGMusic, Touhou etc.)

### Takeaway
NES-MDB is the only clean, MIT-licensed game-music dataset: small (5,278 songs) but it has strict 4-voice structure (2 pulse, triangle-as-bass, noise-as-drums), which suits bass/lead/drums. VGMusic (~31.8k MIDI) is explicitly copyrighted by individual arrangers, so it is not legally usable without permission. The 28k "VGMdb" Google-Drive crawl in the wayne391 list is the same problem.

### Cited Findings
- **NES-MDB**: 5,278 songs from 397 NES games, 296 composers, more than 2M notes. Formats: MIDI (12 MB), expressive score (24 Hz piano-roll with velocity/timbre), separated score, blended score, a language-model text format (155 MB), and raw VGM (31 MB, from VGMRips). Repository licence: **MIT**. Downloads are Google Drive links. — [NES-MDB GitHub](https://github.com/chrisdonahue/nesmdb)
- **VGMusic.com**: lists 31,806 game music MIDI files. It states: "All music files on this site, including those within zip files, are copyrighted by their respective authors". Users must contact each author, and direct linking to files is discouraged. No AI clause on the home page. — [VGMusic](https://www.vgmusic.com/)
- The wayne391 list hosts a crawl it labels "VGMdb" (actually vgmusic.com): 28,419 multitrack MIDI files on Google Drive. — [wayne391 list](https://github.com/wayne391/symbolic-music-datasets)

### Inferences
- NES-MDB's triangle channel is a natural "bass" line and its noise channel a "drum" line. It is a good small source of loop-like 4-voice patterns, and it converts to MIDI trivially (MIDI is already provided).
- The VGMusic and wayne391 crawls are very likely already inside Lakh, MetaMIDI, GigaMIDI and Discover/Godzilla, since those aggregators scraped the web. Expected new content is low, and the licence is unclear anyway.

### Gaps
- No dedicated, licensed Touhou or other game-MIDI dataset was found in this pass.
- The VGMusic Terms of Service page (information/legal.php) was not fetched.

## 3. Large MIDI and symbolic collections released 2024-2026 not in our set

### Takeaway
Few genuinely new large multi-instrument MIDI corpora appeared in 2025-2026; most new HF releases are piano-only or derivatives of what we already have (Aria-MIDI, Lakh). Notable additions: the IMSLP MIDI dumps (about 15.7k files in three licence-split repos, including CC0 and CC BY-SA), Lyrics-MIDI (~180k, likely overlapping with Discover), Monster-MIDI (35 GB, NC), PianoCoRe (piano, NC), and MulTTiPop (tiny, CC BY).

### Cited Findings
- **IMSLP MIDI (TiMauzi)**: `imslp-midi-by-sa` has 6,992 files (about 299 MB, **CC BY-SA 4.0**), crawled from IMSLP on 21-22 July 2024, with per-file source and uploader. Sister sets: `imslp-midi-cc0-1.0` (about 1.11k according to the HF listing) and `imslp-midi-by-nc-sa` (about 7.59k according to the listing). — [HF imslp-midi-by-sa](https://huggingface.co/datasets/TiMauzi/imslp-midi-by-sa); [HF MIDI tag listing](https://huggingface.co/datasets?other=midi&sort=downloads)
- **Monster-MIDI-Dataset** (projectlosangeles): 35.4 GB, size category 1M-10M, licence **CC BY-NC-SA 4.0**. Its source and relation to LAMD/Godzilla are not stated. — [HF Monster-MIDI](https://huggingface.co/datasets/projectlosangeles/Monster-MIDI-Dataset)
- **Lyrics-MIDI-Dataset** (asigalov61): 179,562 MIDI files with lyric .txt files, updated in 2026 (144,417 normalized MIDI files, standardized data dated 04/23/2026). — [HF Lyrics-MIDI](https://huggingface.co/datasets/asigalov61/Lyrics-MIDI-Dataset) (from the search snippet; licence not verified)
- **Extended GigaMIDI**: more than 2.1M unique MIDI files with loop-detection annotations. This is a newer version of GigaMIDI, which we already have, so check our version. — [HF GigaMIDI](https://huggingface.co/datasets/Metacreation/GigaMIDI) (search snippet)
- **PianoCoRe** (SyMuPe): piano score-to-performance data, 100K-1M entries in Parquet, **CC BY-NC-SA 4.0**, arXiv 2605.06627. Its sources are not stated on the card. — [HF PianoCoRe](https://huggingface.co/datasets/SyMuPe/PianoCoRe)
- **TASTE** (Itsuki-music): about 493k rows of text annotations (emotion, genre, key, BPM, section structure) for piano pieces drawn from aria_midi, pop2piano, piast_yt, emopia, pijama and others. Licence **CC BY-NC-SA 4.0**, arXiv 2610.15960. It is metadata/captions, not new notes. — [HF TASTE](https://huggingface.co/datasets/Itsuki-music/TASTE)
- **MulTTiPop** (CMU G-CLef, 2026, arXiv 2607.08756): 572 TheoryTab segments (about 3.5 h) aligned with multitrack Lakh MIDI. **CC BY 4.0**. — [MulTTiPop](https://gclef-cmu.org/multtipop/)
- Other MIDI-tagged HF datasets seen in the listing (not inspected): `J1mmymm/MIMuT_Data_v2`, `wmatejuk/midi-tokens-dyadic-*` (tokenized performances), `Wayne42/gangqinpu` (38.6k), `xavriley/GAPS`, `xavriley/CharlieParkerAlignedOmnibook`, `NEXTLab-ZJU/popular-hook`, `ygonet/midi-classical-music` (4.8k), `breadlicker45/bread-midi-dataset`. — [HF MIDI tag listing](https://huggingface.co/datasets?other=midi&sort=downloads); [search](https://huggingface.co/datasets/breadlicker45/bread-midi-dataset)
- 2025 Lakh de-duplication paper (arXiv 2509.16662): relevant for removing Lakh duplicates across our aggregators. — [arXiv 2509.16662](https://arxiv.org/pdf/2509.16662)
- Loop-extraction precedent: SYMPLEX built about 250k 4-bar multi-instrument loops from MetaMIDI. — [arXiv 2405.12666](https://arxiv.org/pdf/2405.12666)
- **Tegridy MIDI Dataset** hub (asigalov61) indexes Discover (6.74M) and Godzilla (5.8M). — [Tegridy GitHub](https://github.com/asigalov61/Tegridy-MIDI-Dataset)

### Inferences
- Among 2024-26 releases, no new EDM/house/techno-specific symbolic dataset was found. Fine-tuning data for house/techno will have to come from filtering our aggregators (Discover, Godzilla, GigaMIDI, MetaMIDI genre tags) or from loop extraction, not from a new public corpus.
- The IMSLP CC0 and CC BY-SA sets are small but legally clean. Much of the IMSLP MIDI is probably already in Discover/Godzilla (unverified).
- Monster-MIDI and Lyrics-MIDI come from the same author as Discover/LAMD/Godzilla. Expect large overlap, so de-duplicate by MD5 or note hash before adding.

### Gaps
- Electronic share and overlap figures for any of the new HF sets were not measured.
- Monster-MIDI's source and file count are not stated. The MIMuT and gangqinpu contents were not inspected.

## 4. Guitar Pro / tab corpora besides DadaGP

### Takeaway
No large, legally clean Guitar Pro corpus besides DadaGP was found. Recent sets (SCORE-SET, GOAT, Guitar-TECHS, SynthTab) are small, synthetic or audio-centric. Songsterr and Ultimate Guitar dumps are user-transcribed copyrighted songs, and we found no licence permitting bulk use, so avoid them.

### Cited Findings
- **SCORE-SET** (2025): Guitar Pro (.gp5) files derived from MAESTRO and GiantMIDI notes, adapted into rhythm-guitar tracks. Licence not stated in the snippet. This overlaps with our MAESTRO/GiantMIDI. — [arXiv 2507.18723](https://arxiv.org/abs/2507.18723v1)
- **GOAT** (2025): 5.9 h of DI electric-guitar audio paired with Guitar Pro tabs. **Guitar-TECHS** (2025): electric guitar with MIDI labels, **CC BY 4.0**. **SynthTab**: synthesized from DadaGP tabs. — [arXiv 2501.03720](https://arxiv.org/pdf/2501.03720); [arXiv 2309.09085](https://arxiv.org/html/2309.09085v4)
- DadaGP itself: 26,181 GuitarPro song scores (already in our set). — [arXiv 2107.14653](https://arxiv.org/abs/2107.14653?context=cs)

### Inferences
- Bass tabs: none of these offers a dedicated bass-tab set. DadaGP's bass tracks are the practical source.

### Gaps
- Songsterr and Ultimate Guitar terms of service were not fetched in this pass, so the claim that they prohibit scraping or ML use is unverified (but expected).
- No dedicated bass-tab dataset was found.

## 5. Lead sheets, jazz, Bach/classical score corpora, ABC/folk

### Takeaway
Clean classical additions: OpenScore Lieder (CC0, about 1,350-1,460 songs) and String Quartets (CC0, about 106-122), both in MuseScore format and convertible to MIDI with the MuseScore CLI. Mutopia (2,124 pieces, PD or CC, with LilyPond and MIDI) is also clean. Essen is already inside KernScores (overlap) and its licence is unclear. abcnotation.com is huge (about 830k tunes) but its terms are unverified, and The Session's data is on GitHub with an unconfirmed licence.

### Cited Findings
- **OpenScore Lieder**: CC0. More than 1,200 songs in a 2022 paper; later counts are 1,356 files (OMR dataset tools) and about 1,460 (HF card). — [OpenScore Lieder GitHub](https://github.com/OpenScore/Lieder); [MuseScore news, 1350 scores](https://musescore.org/en/node/325308); [HF zzsi/openscore](https://huggingface.co/datasets/zzsi/openscore/blob/main/README.md)
- **OpenScore String Quartets**: **CC0** (LICENSE.txt), with a credit request. Stored as `.mscx` in `scores/`; bulk conversion via the MuseScore batch plugin or CLI. Count not shown on the README; secondary sources give 106 to about 122. A Durham repository record lists CC BY-SA 4.0, which conflicts; the GitHub CC0 is authoritative. — [OpenScore StringQuartets GitHub](https://github.com/OpenScore/StringQuartets); [Durham record](https://durham-repository.worktribe.com/output/1876229)
- **Mutopia Project**: 2,124 pieces, public domain or Creative Commons (licence per piece), with PDF, MIDI and LilyPond source. No bulk download is mentioned on the home page; an RSS feed exists. — [Mutopia](https://www.mutopiaproject.org/)
- **Essen Folksong Collection**: 8,473 folk songs in **kern, a zip download on KernScores, so it is already in our set via KernScores. Copyright 1995, estate of Helmut Schaffrath; music21 calls its legal status "unclear". — [KernScores data](https://kernscores.stanford.edu/help/data); [music21 Essen licence](https://piano.thomer.com/venv/lib/python3.13/site-packages/music21/corpus/essenFolksong/license.txt)
- **EsAC Folk Song DB**: 7,821 songs, SQLite via Jazzomat, distributed "with kind permission" (no open licence). — [Jazzomat download](https://jazzomat.hfm-weimar.de/download/download.html)
- **abcnotation.com**: "around 830,000 tunes" as sheet music or MIDI, some linking to external hosts. Copyright and content-policy pages exist but were not read. — [abcnotation.com](https://abcnotation.com/)
- **The Session**: data dump on GitHub (`adactio/TheSession-data`) as CSV, JSON and SQLite (tunes, settings, sets, aliases, popularity). The LICENSE.md text could not be read, and the API page returned 403. — [TheSession-data GitHub](https://github.com/adactio/TheSession-data). The brief's note that The Session forbids LLM use is **unverified in this pass**. Also, IrishMAN (in our set) is largely derived from The Session.
- **Hymnal** (hymnal.net crawl): 3,358 MIDI lead sheets. **Doug McKenzie Jazz**: 297 multitrack jazz MIDI. Both are Google-Drive crawls with no licence (both from the wayne391 list). — [wayne391 list](https://github.com/wayne391/symbolic-music-datasets)
- **Charlie Parker Aligned Omnibook** (`xavriley/CharlieParkerAlignedOmnibook`, 50 entries) is on HF. Not inspected. — [HF MIDI listing](https://huggingface.co/datasets?other=midi&sort=downloads)

### Inferences
- Conversion difficulty: OpenScore needs MuseScore CLI to export MIDI (easy). Mutopia already ships MIDI (trivial). Essen and KernScores use kern, via music21 or verovio (easy). ABC goes through abc2midi or music21 (easy, but folk melodies are monophonic). WJazzD has a MIDI zip (trivial).
- For a 4-bar house/techno pattern model, classical, folk and jazz scores mainly add melodic and harmonic diversity. Electronic share is about zero. Priority should go to chord corpora (for chords/bass) and loop extraction from existing multitrack aggregators.

### Gaps
- Licence terms for abcnotation.com, The Session (LICENSE.md text), Songsterr and Ultimate Guitar were not read on primary pages.
- Exact OpenScore Lieder and String Quartets counts as of Nov 2026 were not confirmed from the repository summary files.
