#!/bin/bash
set -e
source /hy-tmp/env.sh

export MODEL=/hy-tmp/models/Meta-Llama-3-8B-Instruct
export DATASET=llama3-8b-sharegpt-test-t1-s0-8192.jsonl
export OUTPUT_LEN=-1
export NUM_PROMPTS=500
export PREDICTOR=/hy-tmp/vllm-ltr/benchmarks/MODEL/results/opt-125m-llama3-8b-sharegpt-score-trainbucket10-b32/usage_config.json

echo "=== PART 2: RATE 4 Group ==="
export REQUEST_RATE=4

for seed in 0 1 2; do
  export SEED=$seed
  
  # FCFS
  bash /hy-tmp/scripts/run_fcfs.sh
  latest=$(ls -t /hy-tmp/results/*.json | head -1)
  mv "$latest" /hy-tmp/results/part2_r4_fcfs_seed${seed}.json
  sleep 5

  # LTR
  bash /hy-tmp/scripts/run_ltr.sh
  latest=$(ls -t /hy-tmp/results/*.json | head -1)
  mv "$latest" /hy-tmp/results/part2_r4_ltr_seed${seed}.json
  sleep 5

  # V1
  export AGING_GATE_S=60
  export PREEMPT_PROTECT=1
  bash /hy-tmp/scripts/run_ltr_aging.sh
  latest=$(ls -t /hy-tmp/results/*.json | head -1)
  mv "$latest" /hy-tmp/results/part2_r4_v1_seed${seed}.json
  sleep 5
done

echo "=== PART 2: RATE 8 Group ==="
export REQUEST_RATE=8

for seed in 0 1 2; do
  export SEED=$seed
  
  # FCFS
  bash /hy-tmp/scripts/run_fcfs.sh
  latest=$(ls -t /hy-tmp/results/*.json | head -1)
  mv "$latest" /hy-tmp/results/part2_r8_fcfs_seed${seed}.json
  sleep 5

  # V1
  export AGING_GATE_S=60
  export PREEMPT_PROTECT=1
  bash /hy-tmp/scripts/run_ltr_aging.sh
  latest=$(ls -t /hy-tmp/results/*.json | head -1)
  mv "$latest" /hy-tmp/results/part2_r8_v1_seed${seed}.json
  sleep 5
done

# LTR on seed 1 (CRASH RUN)
echo "=== PART 2: RATE 8 LTR Seed 1 (Crash Run) ==="
export SEED=1
export REQUEST_RATE=8
bash /hy-tmp/scripts/run_ltr.sh || true
latest=$(ls -t /hy-tmp/results/*.json | head -1)
mv "$latest" /hy-tmp/results/part2_r8_ltr_seed1.json || true
