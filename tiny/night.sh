#!/bin/bash
# The overnight run after pretraining (tiny/big.*): fine-tune on style + effects + ratings, then two
# rounds of critic-picked self-training (sample -> critic -> fine-tune), and one comparison of every
# model on the same 200 prompts. Log: tiny/night.log. Steps whose output exists are skipped, so a
# rerun after a failure resumes.
set -euo pipefail
cd "$(dirname "$0")/.."
export NODE_PATH=js/node_modules
W=tiny/work; mkdir -p $W
log() { echo "$(date +%H:%M) $*" | tee -a tiny/night.log; }
space() { local free; free=$(df -g . | awk 'NR==2 {print $4}'); log "free ${free} GB"; [ "$free" -ge 5 ] || { log 'under 5 GB free, stopping'; exit 1; }; }

space
if [ ! -f tiny/bigft.safetensors ]; then
  python3 tiny/mix.py ft >> tiny/night.log
  uv run python tiny/train.py --data ft --init big --out bigft --steps 1500 --lr 3e-4 > tiny/train-bigft.log 2>&1
  log "bigft: $(tail -1 tiny/train-bigft.log)"
fi

cur=bigft
for round in 1 2; do
  if [ -f tiny/bigrest$round.safetensors ]; then cur=bigrest$round; continue; fi
  space
  if [ ! -f $W/s$round.jsonl ]; then
    node tiny/critic.mjs prompts 800 $W/p$round.jsonl $round 2>/dev/null
    (cd tiny && uv run python sample.py $cur work/p$round.jsonl work/s$round.jsonl --n 8 > /dev/null)
  fi
  log "round $round picks: $(node tiny/critic.mjs score $W/s$round.jsonl tiny/reward.json $W/picks$round.txt 2>/dev/null | tail -1)"
  python3 tiny/mix.py rest$round --picks $W/picks$round.txt --big 100000 >> tiny/night.log
  uv run python tiny/train.py --data rest$round --init $cur --out bigrest$round --steps 600 --lr 2e-4 > tiny/train-bigrest$round.log 2>&1
  log "bigrest$round: $(tail -1 tiny/train-bigrest$round.log)"
  cur=bigrest$round
  rm -f $W/s$round.jsonl
done

# the same 200 prompts for every model: the critic's mean on the first draft and on the best of 8
node tiny/critic.mjs prompts 200 $W/eval.jsonl 99 plain 2>/dev/null  # a seed the rounds never use; no section tags, so the old model can read them
for m in tiny-style3 big bigft bigrest1 bigrest2; do
  (cd tiny && uv run python sample.py $m work/eval.jsonl work/eval-$m.jsonl --n 8 > /dev/null)
  log "eval $m: $(node tiny/critic.mjs score $W/eval-$m.jsonl tiny/reward.json /dev/null 2>/dev/null | tail -1)"
done
log done
