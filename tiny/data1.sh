#!/bin/bash
# Fine-tune the hearing model on the extra datasets (Strudel-Synth, NeuralAcid) and the liked lines
# from the rating page, then compare it with where it started on the same 200 prompts (with sections
# and `on` words) and check it still writes parts that parse.   tiny/data1.sh [from] [out]
set -euo pipefail
cd "$(dirname "$0")/.."
export NODE_PATH=js/node_modules
FROM=${1:-bighear} OUT=${2:-bigdata}
uv run python tiny/train.py --data data1 --init $FROM --out $OUT --steps 2500 --lr 2e-4 > tiny/train-$OUT.log 2>&1
tail -1 tiny/train-$OUT.log
python3 -c "import json; p='tiny/$OUT.json'; c=json.load(open(p)); c['hear']=True; c['from']='$FROM'; json.dump(c, open(p,'w'))"
for m in $FROM $OUT; do
  (cd tiny && uv run python sample.py $m work/evalh.jsonl work/evalh-$m.jsonl --n 8 > /dev/null)
  echo "hear prompts $m: $(node tiny/critic.mjs score tiny/work/evalh-$m.jsonl tiny/reward.json /dev/null 2>/dev/null | tail -1)"
done
