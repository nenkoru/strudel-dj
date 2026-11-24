#!/bin/zsh
# LoRA SFT of LFM3-1.7B through mlx-vlm (released mlx-lm cannot load LFM3 yet: ml-explore/mlx-lm#2016).
# Same data, rank and step budget as lora.yaml for Qwen, so the two adapters compare directly.
#   ./train_lfm3.sh [data dir] [output adapter dir]
data=${1:-data/mlx}; out=${2:-adapters/lfm3-1.7b}
mkdir -p "$out" logs
uv run python -m mlx_vlm.train --algorithm sft \
  --model LiquidAI/LFM3-1.7B-MLX-bf16 \
  --data "$data" --train-split train --validation-split valid \
  --train-type lora --lora-rank 16 --lora-alpha 32 \
  --learning-rate 1e-4 --batch-size 4 --iters 1200 --max-seq-length 1400 \
  --train-on-completions --grad-checkpoint \
  --steps-per-report 25 --steps-per-eval 200 --val-batches 25 --steps-per-save 400 \
  --output-path "$out"
