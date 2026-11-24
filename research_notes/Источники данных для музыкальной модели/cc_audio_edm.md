# CC and public-domain EDM audio sources for Demucs + basic-pitch MIDI transcription

Research date: 2026-11-05. Numbers marked "live query" came from the sites' own APIs or search pages, run during this research (curl against archive.org advancedsearch, the ccMixter query API and Freesound search pages). Already in use and not re-researched here: MTG-Jamendo, WaivOps EDM-HSE/EDM-TECH, FSL10K.

## Internet Archive netlabels collection

### Takeaway
The IA `netlabels` collection is the biggest new source. About 11.3k items (releases) carry techno/house/minimal/trance/progressive/tech-house subjects. That is roughly 85k tracks and around 8–9k hours, fetchable in bulk with `ia` or the metadata API. But about 47% of those items are ND (mostly BY-NC-ND), and only about 14% are free of both NC and ND (CC BY, BY-SA, CC0, PD). The classic minimal/techno labels (Thinner, Autoplate, Monotonik, Kahvi) are largely ND. The big exceptions are **Genetic Trance** (mostly CC0) and **Monokrak** (mostly BY-NC-SA, which allows derivatives).

### Cited Findings
- `collection:netlabels` has 80,555 items, 77,108 of them `mediatype:audio`, plus 2,014 sub-collections (labels and user "fav-" lists). Live query, 2026-11-05 — [IA advancedsearch](https://archive.org/advancedsearch.php?q=collection%3Anetlabels&rows=0&output=json)
- Subject counts inside netlabels (live query, items not tracks; subjects overlap): electronic 13,510; techno 6,226; minimal 3,868; house 2,882; trance 1,313; "minimal techno" 769; dub techno 579; "deep house" 395 — [IA advancedsearch](https://archive.org/advancedsearch.php)
- Union query `collection:netlabels AND (subject:techno OR house OR minimal OR trance OR progressive OR "tech house")` returns **11,346 items** with a summed `item_size` of **≈5.1 TB**. That size includes IA's derivative files, so it overstates the originals. Live query — [IA advancedsearch](https://archive.org/advancedsearch.php)
- Licence split of those 11,346 items, from the `licenseurl` field (live query):
  - BY-NC-ND 4,728 + "by-nd-nc" 92 = 4,820
  - BY-NC-SA 2,198
  - no licenseurl 1,772
  - BY-SA 597
  - CC0 593
  - BY-NC 461
  - BY-ND 460
  - BY 313
  - PD Mark 78
  - publicdomain 49
  - Sampling / NC-Sampling+ 5

  [IA advancedsearch](https://archive.org/advancedsearch.php)
  - Derived from those counts:
    - **ND** (no derivatives) = 5,280 items (≈47%).
    - **Derivatives allowed** (BY, BY-SA, BY-NC, BY-NC-SA, CC0, PD) = 4,289 (≈38%).
    - **No NC and no ND** (BY, BY-SA, CC0, PD) = 1,630 (≈14%).
    - **No licenseurl** = 1,772 (≈16%; licence may be stated only in the description, unverified).
- Sample of 40 random EDM-subject items via `https://archive.org/metadata/{id}/files`: about **7.6 tracks and about 46 min per item**. Live query; small sample, high variance — [IA metadata API](https://archive.org/developers/md-read.html)
- Per-label figures (live query; items, summed size incl. derivatives, licences):

  | Collection | Items | Size | Licences |
  |---|---|---|---|
  | `thinner` | 44 | 2.8 GB | all BY-NC-ND |
  | `autoplate` | 33 | 2.2 GB | all BY-NC-ND |
  | `kahvi` | 269 | 29.4 GB | BY 71, BY-ND 106, BY-NC-ND 48, none 44 |
  | `monotonik` | 514 | 68.9 GB | BY-NC-ND 256, none 256, BY-ND 2 |
  | `mimi` | 274 | 37.6 GB | all "none" in licenseurl |
  | `test_tube` | 58 | 9.0 GB | all "none" in licenseurl |
  | `ideology` | 1 | – | the label is essentially absent from IA |
  | `deepindub` (dub techno) | 220 | 69 GB | mostly BY-NC-ND |
  | `zimmer` | 214 | 68 GB | mostly BY-NC-ND |
  | `kreislauf` | 235 | 41 GB | 226 BY-NC-ND |
  | `mnmnrecords` (minimal) | 573 | 159 GB | 568 BY-NC-ND |
  | `monokrak` | 284 | 120 GB | **BY-NC-SA 210, BY-SA 40**, BY-NC 11 |
  | `genetic-trance` | 946 | 227 GB | **CC0 571**, none 333, BY 11 |
  | `netwaves` | 786 | 306 GB | BY-NC-SA 455, BY-NC-ND 284 |
  | `cianorbe` | 743 | 451 GB | 713 BY-NC-ND |

  [IA advancedsearch](https://archive.org/advancedsearch.php)
- Labels contributing the most EDM-subject items include genetic-trance, rodenttapesbackstage, netwaves, cianorbe, unclassedmedia, monokrak, bumpfoot, toucan, zimmer, kreislauf, mnmnrecords and deepindub. Collections named `fav-*` are user favourites lists, not labels. Live query — [IA advancedsearch](https://archive.org/advancedsearch.php)
- Bulk access:
  - `advancedsearch.php` returns any field list (identifier, licenseurl, subject, collection, item_size) as JSON with large `rows`.
  - Per-item file lists, with `length` and `format`, come from `archive.org/metadata/{id}`.
  - Both worked without authentication in this session — [IA metadata API docs](https://archive.org/developers/md-read.html)
  - The `ia` CLI (internetarchive Python package) supports `ia search` and `ia download --glob`; this is from prior knowledge and was not re-fetched this session.

### Inferences
- **Estimated EDM total:** 11,346 items × 46 min ≈ 8,700 h and ≈ 85k tracks, before deduplication. Of that, about 1,200 h is NC/ND-free (BY/BY-SA/CC0/PD), and about 3,300 h allows derivatives if NC is acceptable for a research model.
- **"minimal" subject is noisy.** It also matches minimal ambient/experimental, so the true count of dance-floor tracks is lower. Filter on genre tags plus a BPM/onset classifier after download.
- **Mimi and Test Tube:** the empty licenseurl most likely means the CC licence sits in the description text. Check per item before use.
- **ND licences:** they forbid sharing adapted material. Whether privately transcribing to MIDI for training counts as an "adaptation", and whether training is a TDM exception or fair use, is a legal question. The conservative route is to exclude ND, or keep ND material internal and never redistribute the MIDI.
- **Possible overlap with FMA:** many netlabel releases were also mirrored on FMA, so deduplicate by audio fingerprint (e.g. Chromaprint). Overlap with Jamendo is likely small.

### Gaps
- Kahvi's newest releases may be hosted on kahvi.org rather than IA. Not checked.
- No exact sum of track durations. The figure is extrapolated from 40 items.
- Licence for the 1,772 "none" items not resolved.
- Ideology netlabel: only 1 IA item found. Its catalogue location (if any) is unknown.

## Jamendo beyond MTG-Jamendo (API v3)

### Takeaway
The Jamendo API needs your own registered `client_id` (developer portal app). It is free for non-commercial use, but the terms forbid apps built to cache content or give offline access. Bulk-downloading the catalogue for training conflicts with the spirit of the API terms even though each track is CC-licensed; contacting Jamendo Licensing is the clean route. A public example client_id returned "Application has been suspended" when tested.

### Cited Findings
- The API gives access to "a catalog of half-a-million tracks". It needs a developer-portal account and an application, uses OAuth2/app authentication, and has an "XML dump" section in the nav — [Jamendo API docs](https://developer.jamendo.com/v3.0/docs)
- API terms, clause 3.3:
  - Free for non-commercial use; any other use needs a quote from licensing@jamendo.com.
  - Jamendo may set request limits.
  - "Applications must not be specifically designed to cache the content nor offering an offline access to the content."
  - Content must be used under each track's CC licence, crediting the artist and Jamendo.
  - No mention of AI/ML.

  [Jamendo API Terms](https://devportal.jamendo.com/api_terms_of_use)
- A test call with a client_id found in old public examples returned `code 11 "Jamendo Api Suspended Application Error"`. Live query, 2026-11-05 — [api.jamendo.com](https://api.jamendo.com/v3.0/tracks/?client_id=709fa152&tags=techno)

### Inferences
- The likely gain beyond MTG-Jamendo: uploads after 2019 and tags other than house/techno/trance (minimal, deep, progressive, electro, idm) via `tags=`/`fuzzytags=`. Licence filters exist in the v3 tracks endpoint per prior knowledge (`ccsa`, `ccnd`, `ccnc` booleans) and an `audiodownload` URL is returned when `audiodownload_allowed`. Not re-verified on the docs page this session; check them in the docs before building a fetcher.
- Jamendo historically defaulted many tracks to BY-NC-SA / BY-NC-ND. Expect a large NC share.

### Gaps
- No current count of CC tracks tagged electronic/techno/house: it needs a valid client_id with `fullcount=true`.
- Status and contents of the XML dump not verified.

## ccMixter

### Takeaway
ccMixter is small (about 52k uploads in total, about 11.7k tagged electronic, about 1.9k techno, about 1.2k house). Its strength is **stems/samples and a cappellas**: separated parts that could skip Demucs. A free query API returns counts and file URLs. Licences are CC BY, BY-NC and the Sampling+ family. Note that NC-Sampling+ is restrictive.

### Cited Findings
- Live counts from `ccmixter.org/api/query?f=count` (2026-11-05):

  | Query | Count |
  |---|---|
  | all uploads | 51,842 |
  | tags=electronic | 11,746 |
  | tags=techno | 1,939 |
  | tags=house | 1,229 |
  | reqtags=sample | 15,971 |
  | reqtags=acappella | 5,989 |
  | lic=by: all | 9,824 |
  | lic=by: electronic | 2,340 |
  | lic=by: techno | 418 |
  | lic=by: house | 206 |
  | lic=by: trance | 90 |

  Other `lic=` values tried (by-sa, noncommercial, sampling+, cczero) returned "invalid license argument" — [ccMixter Query API](https://ccmixter.org/api/query?f=count&tags=electronic)
- About page:
  - Music is under CC licences marked per upload, including noncommercial and "Sampling" licences.
  - Songwriters are asked to "submit individual tracks (a.k.a. stems)"; there are Samples/"Browse Stems" and A Cappellas sections.
  - The ccHost Query API is "an open, publicly available interface".
  - No data dump is mentioned.

  [ccMixter About](https://ccmixter.org/about)

### Inferences
- The ~2.3k CC BY electronic uploads are the cleanest subset. The sample/stem packs can feed per-instrument MIDI directly (basic-pitch on isolated stems, no Demucs artefacts).
- Many electronic uploads are remixes, which carry the licence chain of their sources. The overlap with netlabels/Jamendo is likely small.

### Gaps
- Licence split beyond CC BY is unknown: the correct `lic=` codes were not found.
- Total hours unknown.
- ccMixter's Terms of Use on AI not read.

## Freesound via API

### Takeaway
Freesound has about 82k sounds matching "loop" (≈33k CC0, ≈39k CC BY, ≈9k BY-NC). About 4.8k of them match house, ≈4.9k techno, ≈3.1k trance, ≈16k synth, ≈14k bass and ≈31k drum (text-search counts; they overlap). Previews (mp3/ogg) need only an API token. Originals need OAuth2 and are capped at 500/day. With CC0+BY loops at a few to 30 s each, usable material is likely only a few hundred hours, and much of it overlaps FSL10K.

### Cited Findings
- Freesound site search counts (live, 2026-11-05):

  | Query | Sounds |
  |---|---|
  | "loop" | 82,107 |
  | "loop drum" | 31,087 |
  | "loop synth" | 16,250 |
  | "loop bass" | 13,910 |
  | "loop techno" | 4,881 |
  | "loop house" | 4,836 |
  | "loop trance" | 3,138 |
  | "house" | 15,325 |
  | "techno" | 9,279 |
  | "loop", CC0 | 32,777 |
  | "loop", Attribution | 38,947 |
  | "loop", Attribution-NonCommercial | 9,088 |

  [Freesound search](https://freesound.org/search/?q=loop)
- API facts:
  - Basic calls use an API key passed as `token`.
  - Downloading the original-quality file needs OAuth2.
  - Previews (.ogg/.mp3 at several qualities) need no OAuth2 and are faster to retrieve.
  - Standard limit: 60 requests/min and 2,000/day.
  - Original downloads: 30/min and 500/day.
  - HTTP 429 when exceeded; higher limits can be requested.

  [Freesound API overview](https://freesound.org/docs/api/overview.html)

### Inferences
- **Estimated hours:** at about 10 s average, the ~72k CC0+BY loops come to roughly 200 h. The EDM-tagged subset is a few tens of hours.
- **Bulk route:** use text search with `page_size` up to 150 to fetch metadata and preview URLs, then download previews. Originals at 500/day would take months, so ask Freesound for raised limits for research.
- **Overlap with FSL10K:** FSL10K (~10k loops) is itself drawn from Freesound, so expect heavy overlap. Deduplicate by sound id.
- Melodic synth/bass loops suit basic-pitch better than full mixes.

### Gaps
- Freesound Terms of Use on ML not fetched.
- Average loop duration not measured. Search counts are text matches (they include the tag and description) and may group packs.

## Free Music Archive (FMA)

### Takeaway
`fma_full` is 106,574 untrimmed tracks, 161 genres and 879 GiB (≈8.2k hours in total). Each track keeps its artist's licence, and the dataset is labelled for research. The licence split for Electronic was not obtained; it needs `tracks.csv` (`track.license` column) from fma_metadata.zip.

### Cited Findings
- Subset sizes:

  | Subset | Tracks | Audio | Size |
  |---|---|---|---|
  | fma_small | 8k | 30 s clips | 7.2 GiB |
  | fma_medium | 25k | 30 s clips | 22 GiB |
  | fma_large | 106,574 | 30 s clips | 93 GiB |
  | fma_full | 106,574 | untrimmed | 879 GiB |

  - 343 days of audio in total.
  - Metadata is CC BY 4.0; audio is under each artist's licence; the dataset is for research purposes.
  - Download links point to `os.unil.cloud.switch.ch`.

  [mdeff/fma GitHub](https://github.com/mdeff/fma)

### Inferences
- Electronic is one of FMA's largest top-level genres (≈34k tracks in fma_full, per the FMA paper's genre table, from memory; **unverified this session**).
- FMA overlaps with IA netlabels, since many netlabels cross-posted, but probably little with Jamendo.
- FMA's own licence mix historically leaned BY-NC-SA / BY-NC-ND, so expect a large NC/ND share.

### Gaps
- Licence split of Electronic tracks (how many are free of NC/ND) is not computed. Run a pandas groupby on `tracks.csv` [`track`,`license`] × `genre_top=='Electronic'`.
- Whether the SWITCH links for fma_full are currently live was not verified: the page fetch could not confirm it.

## SoundCloud, Bandcamp, Musopen, Incompetech, Pixabay, YouTube Audio Library

### Takeaway
None of these is a good bulk EDM source:
- **SoundCloud:** the API reopened in 2026 but needs Artist Pro, and bulk scraping is risky.
- **Bandcamp:** no API.
- **Musopen:** classical only.
- **Incompetech:** CC BY, but small and mostly non-EDM.
- **Pixabay:** its terms **explicitly prohibit scraping and automated collection "for machine learning purposes"**.
- **YouTube Audio Library:** terms don't address ML, and downloads are one track at a time.

### Cited Findings
- **SoundCloud:** app registration has been self-serve since a May 2026 announcement but needs an **Artist Pro subscription**. A June 2026 CLI registers apps via OAuth. The OpenAPI spec is at github.com/soundcloud/api — [SoundCloud register-app docs](https://developers.soundcloud.com/docs/api/register-app); [SoundCloud blog: API credentials CLI](https://developers.soundcloud.com/blog/api-credentials-cli-openapi-github)
- **Pixabay** Terms, updated 20 Oct 2026:
  - Section 8 prohibits "Data mining, extraction, scraping and the use of programs or robots for automatic data collection … for all unauthorised purposes, including without limitation for machine learning purposes".
  - "Bulk, large-scale or systematic copying of Content is strictly prohibited".
  - Standalone redistribution is banned.
  - Section 7A lets Pixabay itself use uploads for ML.

  [Pixabay Terms](https://pixabay.com/service/terms/); [Pixabay License Summary](https://pixabay.com/service/license-summary/)
- **YouTube Audio Library:**
  - Offers CC-attribution tracks and "Attribution not required" (standard licence) tracks.
  - MP3 download is via the Studio UI.
  - The help page says nothing about AI training or use outside YouTube.

  [YouTube Help: Audio Library](https://support.google.com/youtube/answer/3376882?hl=en)
- **YouTube ToS and AI training** is under litigation in 2026, with Google arguing its ToS licence covers training — [RightsTech, June 2026](https://rightstech.com/2026/06/youtube-terms-of-service-allow-ai-music-training-google-says-in-copyright-lawsuit/)
- **Incompetech (Kevin MacLeod):** free "Creative Commons" option requiring credit, or a paid Standard License. The page doesn't state a CC version, a track count or any AI terms — [Incompetech licenses](https://incompetech.com/music/royalty-free/licenses/)

### Inferences
- **SoundCloud:** CC-licensed tracks exist and the API historically exposed a `license` field. Bulk audio download for training would likely clash with SoundCloud's ToS; treat it as not recommended.
- **Bandcamp:** has no public API, so CC labels there would need manual or scraped downloads. That is not recommended under its ToS; prefer finding the same labels on IA.
- **Musopen:** public-domain/CC classical. Irrelevant for EDM, apart from possible pretraining on general harmony.
- **YouTube Audio Library:** treat as not usable for bulk ML; there is no API or bulk download, and no permission is stated.

### Gaps
- SoundCloud and Bandcamp ToS clauses on scraping/AI not fetched this session.
- Incompetech's exact CC version (believed CC BY 4.0) and track count (~2k) not verified.
- Musopen licences not checked.
- Pixabay Music track counts not checked; not worth it given Section 8.
