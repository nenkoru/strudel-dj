#!/bin/bash
# Every MTG-Jamendo part in turn: download (1.7 GB), transcribe its dance tracks to MIDI
# (tiny/audio2midi.py, into data/raw/dl/jamendo/midi), delete the archive. Resumes: finished parts
# are listed in data/raw/dl/jamendo/parts-done; tracks already in meta.jsonl are skipped.
#   tiny/jamendo.sh [first part] [last part] [demucs device]
set -uo pipefail
cd "$(dirname "$0")/.."
J=data/raw/dl/jamendo
PY=${BP_PYTHON:?set BP_PYTHON to the demucs/basic-pitch environment python}
touch $J/parts-done
for i in $(seq -w ${1:-0} ${2:-99}); do
  grep -qx "$i" $J/parts-done && continue
  free=$(df -g . | awk 'NR==2 {print $4}')
  [ "$free" -ge 8 ] || { echo "under 8 GB free, stopping"; exit 1; }
  tar=$J/part-$i.tar
  [ -f $tar ] || curl -sfL --retry 5 --retry-delay 20 --retry-all-errors -o $tar "https://cdn.freesound.org/mtg-jamendo/raw_30s/audio-low/raw_30s_audio-low-$i.tar" || { echo "part $i: download failed"; continue; }
  want=$(grep "audio-low-$i.tar" $J/tars.txt | cut -c1-64)
  [ "$(shasum -a 256 $tar | cut -c1-64)" = "$want" ] || { echo "part $i: checksum mismatch"; continue; }
  $PY tiny/audio2midi.py $tar $J/genre.tsv $J/midi --device ${3:-cpu} 2>&1 | grep -E "bpm|skipped" | tail -3
  echo "$i" >> $J/parts-done
  echo "part $i done: $(ls $J/midi/*.mid | wc -l) midi files"
  rm -- "$J/part-$i.tar"
done
