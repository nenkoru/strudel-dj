#!/bin/zsh
# Transcribe tracks and build A/B loops: ./batch.sh out "<track1>" "<track2>" ...
# One JSON line per track goes to <out>/summary.jsonl.
out=$1; shift
mkdir -p "$out"
for track in "$@"; do
  echo "== $track" >&2
  uv run python track2midi.py "$track" "$out" 2>>"$out/batch.err" | grep '^{' >&2 || { echo "transcribe failed: $track" >&2; continue; }
  name=$(basename "$track"); name=${name%.*}; name=${name%% -  - *}
  uv run python ab.py "$out/$name.json" 2>>"$out/batch.err" | grep '^{"name"' >> "$out/summary.jsonl" || echo "ab failed: $track" >&2
done
