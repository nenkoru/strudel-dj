#!/bin/bash
# Every MTG-Jamendo part in turn: download (1.7 GB), transcribe its dance tracks to MIDI
# (tiny/audio2midi.py, into data/raw/dl/jamendo/midi), delete the archive. Resumes: finished parts
# are listed in data/raw/dl/jamendo/parts-done; tracks already in meta.jsonl are skipped.
# The freesound CDN is slow (0.1-1.5 MB/s a connection), so the next AHEAD parts download in the
# background while one is transcribed; each goes to part-NN.tar.part (resumed with a range) and is
# renamed when complete, and a .lock marks a download in progress.
#   tiny/jamendo.sh [first part] [last part] [demucs device]
# WORKER=k/n splits the parts between n workers (worker k takes parts where 10#part % n == k);
# unset = 0/1 = every part. The 3rd arg accepts cuda:0, cuda:1, mps or cpu.
set -uo pipefail
cd "$(dirname "$0")/.."
J=data/raw/dl/jamendo
PY=${BP_PYTHON:?set BP_PYTHON to the demucs/basic-pitch environment python}
AHEAD=${AHEAD:-3}
W=${WORKER:-0/1}
wk=${W%/*}; wn=${W#*/}
touch $J/parts-done

fetch() {  # download part $1 unless it is here or already being fetched
  local tar=$J/part-$1.tar
  [ -f $tar ] || [ -f $tar.lock ] && return 0
  touch $tar.lock
  curl -sfL --retry 10 --retry-delay 20 --retry-all-errors -C - -o $tar.part \
    "https://cdn.freesound.org/mtg-jamendo/raw_30s/audio-low/raw_30s_audio-low-$1.tar" && mv $tar.part $tar
  rm -f $tar.lock
}

ready=(); rest=()  # parts already downloaded go first, so the GPU starts at once
for i in $(seq -w ${1:-0} ${2:-99}); do
  grep -qx "$i" $J/parts-done && continue
  [ $((10#$i % wn)) -eq $wk ] || continue
  if [ -f $J/part-$i.tar ]; then ready+=("$i"); else rest+=("$i"); fi
done
todo=("${ready[@]}" "${rest[@]}")
for n in "${!todo[@]}"; do
  i=${todo[$n]}
  free=$(df -Pk . | awk 'NR==2 {print int($4 / 1048576)}')  # GB, on macOS and Linux
  [ "$free" -ge 8 ] || { echo "under 8 GB free, stopping"; exit 1; }
  for j in "${todo[@]:$((n + 1)):$AHEAD}"; do fetch $j & done
  tar=$J/part-$i.tar
  while [ -f $tar.lock ]; do sleep 20; done
  fetch $i
  [ -f $tar ] || { echo "part $i: download failed"; continue; }
  want=$(grep "audio-low-$i.tar" $J/tars.txt | cut -c1-64)
  [ "$( (sha256sum $tar 2>/dev/null || shasum -a 256 $tar) | cut -c1-64)" = "$want" ] || { echo "part $i: checksum mismatch"; rm -f -- "$tar"; continue; }
  # the whole output to part-NN.log; a part whose transcription fails keeps its archive and is not marked
  # done (2026-11-24: four parts failed silently behind the grep, were marked done and deleted)
  $PY tiny/audio2midi.py $tar $J/genre.tsv $J/midi --device ${3:-cpu} > $J/part-$i.log 2>&1
  rc=$?
  grep -E "bpm|skipped" $J/part-$i.log | tail -3
  [ $rc -eq 0 ] || { echo "part $i: audio2midi failed ($rc), kept for a retry:"; grep -v Predicting $J/part-$i.log | tail -5; continue; }
  echo "$i" >> $J/parts-done
  echo "part $i done: $(ls $J/midi/*.mid | wc -l) midi files"
  rm -- "$J/part-$i.tar"
done
wait
