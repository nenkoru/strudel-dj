#!/bin/bash
# Fine-tune a model to hear the track: lanes of multitrack MIDI with `on` words for what the other
# parts play (tiny/prep_big.py --hear) plus the style, rated and picked lines with plausible `on`
# words, then mark it (cfg.hear) so the pages put the track's words in its prompts, and compare it
# with where it started on the same 200 prompts.   tiny/hear.sh <from> [out]
set -euo pipefail
cd "$(dirname "$0")/.."
export NODE_PATH=js/node_modules
FROM=$1 OUT=${2:-bighear}; W=tiny/work
python3 tiny/mix.py hear --hear --big 1000000 --picks $W/picks2.txt
uv run python tiny/train.py --data hear --init $FROM --out $OUT --steps 3000 --lr 3e-4 > tiny/train-$OUT.log 2>&1
tail -1 tiny/train-$OUT.log
python3 -c "import json,sys; p='tiny/$OUT.json'; c=json.load(open(p)); c['hear']=True; c['from']='$FROM'; json.dump(c, open(p,'w'))"
node tiny/critic.mjs prompts 200 $W/evalh.jsonl 99 hear 2>/dev/null
(cd tiny && uv run python sample.py $OUT work/evalh.jsonl work/evalh-$OUT.jsonl --n 8 > /dev/null)
echo "hear prompts $OUT: $(node tiny/critic.mjs score $W/evalh-$OUT.jsonl tiny/reward.json /dev/null 2>/dev/null | tail -1)"
(cd tiny && uv run python sample.py $OUT work/evals.jsonl work/evals-$OUT.jsonl --n 8 > /dev/null)
echo "section prompts $OUT: $(node tiny/critic.mjs score $W/evals-$OUT.jsonl tiny/reward.json /dev/null 2>/dev/null | tail -1)"
