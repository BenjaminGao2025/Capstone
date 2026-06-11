#!/bin/bash
# 正式实验:request_rate 扫描(论文口径),从低负载 2 开始——LTR 收益在中高负载、
# 未完全饱和区间;只测饱和区会看不到 p99 优势
# 前置:run_llama_probe.sh 已确认 SWAP_SPACE 水位安全
set -e
source /hy-tmp/env.sh
export MODEL=/hy-tmp/models/Meta-Llama-3-8B-Instruct
export OUTPUT_LEN=-1
export NUM_PROMPTS=500
export SEED=0
export MAX_MODEL_LEN=8192
export SWAP_SPACE="${SWAP_SPACE:-4}"   # 按 probe 结果调整,两臂始终同值

for RATE in 2 4 8 16 32; do
  export REQUEST_RATE=$RATE
  echo "=== sweep rate=$RATE : FCFS ==="
  bash /hy-tmp/scripts/run_fcfs.sh
  sleep 20
  echo "=== sweep rate=$RATE : LTR ==="
  bash /hy-tmp/scripts/run_ltr.sh
  sleep 20
done
echo "SWEEP_DONE - 每档两臂各一份 JSON,共 10 份,在 /hy-tmp/results/"
ls -lh /hy-tmp/results/*.json | tail -12
