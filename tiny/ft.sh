#!/bin/bash
# The genre fine-tune of the base model (base130 -> base130ft) on the GPU server, started by hand and left to
# wait: packs the corpus tiny/genre.py wrote (genre programs twice, genre lines, a replay of general
# programs as large as the genre programs), waits for pretraining to end (BASEDONE in train-base130.log),
# fine-tunes about one epoch at a third of the base's rates, decaying over the last 30%, then compares
# both models (tiny/evalft.py -> eval-*.json, ft-samples-*.txt). Conversions stay off the last cores.
cd ~/strudel-lm
export PYTHONHASHSEED=0
D=tiny/data
P="nice -n 19 taskset -c 0-9 venv/bin/python tiny/train_torch.py pack"
[ -f $D/ft.json ] || $P $D/genre-pieces.txt.gz $D/genre-lines.txt.gz $D/replay-pieces.txt.gz --weight 2,1,1 \
  --tokenizer tok4k --out $D/ft > packft.log 2>&1 || exit 1
[ -f $D/ev-genre-pieces.json ] || $P $D/genre-pieces.txt.gz --tokenizer tok4k --out $D/ev-genre-pieces >> packft.log 2>&1
[ -f $D/ev-genre-lines.json ] || $P $D/genre-lines.txt.gz --tokenizer tok4k --out $D/ev-genre-lines >> packft.log 2>&1
echo PACKDONE >> packft.log
until grep -q BASEDONE train-base130.log; do sleep 120; done
STEPS=$(python3 -c "import json; print(json.load(open('$D/ft.json'))['train'] // (32 * 2048))")
venv/bin/torchrun --nproc_per_node 2 tiny/train_torch.py train --init base130 --bin $D/ft --steps $STEPS \
  --batch 32 --accum 4 --every 250 --muon 0.007 --lr 2e-4 --decay 0.3 --compile --flash --out base130ft > train-ft.log 2>&1
echo FTDONE >> train-ft.log
venv/bin/python tiny/evalft.py base130 base130ft > eval.log 2>&1
echo EVALDONE >> eval.log
