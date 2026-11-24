#!/bin/bash
# Self-improvement by preferences, no listener needed: 8 drafts per prompt from the current model,
# the critic's best against its worst as pairs, DPO on them (plus the rating page's A/B pairs when
# exported to $PAGE), then the same 200 section prompts as tiny/night.sh's comparison.
#   tiny/dpo.sh <from> <out> [page pairs dir]
set -euo pipefail
cd "$(dirname "$0")/.."
export NODE_PATH=js/node_modules
FROM=$1 OUT=$2 PAGE=${3:-}; W=tiny/work
node tiny/critic.mjs prompts 800 $W/dp.jsonl 3 2>/dev/null
(cd tiny && uv run python sample.py $FROM work/dp.jsonl work/ds.jsonl --n 8 > /dev/null)
node tiny/critic.mjs pairs $W/ds.jsonl tiny/reward.json $W/cpairs.jsonl 2>/dev/null
(cd tiny && uv run python dpo.py $FROM --out $OUT --pairs work/cpairs.jsonl ${PAGE:+--page "$PAGE"})
(cd tiny && uv run python sample.py $OUT work/evals.jsonl work/evals-$OUT.jsonl --n 8 > /dev/null)
echo "sections $FROM: $(node tiny/critic.mjs score $W/evals-$FROM.jsonl tiny/reward.json /dev/null 2>/dev/null | tail -1)"
echo "sections $OUT: $(node tiny/critic.mjs score $W/evals-$OUT.jsonl tiny/reward.json /dev/null 2>/dev/null | tail -1)"
rm -f $W/ds.jsonl
