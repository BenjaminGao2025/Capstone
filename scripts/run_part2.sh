#!/bin/bash
# DEPRECATED / UNSAFE FOR NEW RUNS
#
# Historical Phase-D orchestrator.
# It writes all arms into a shared output directory and selects the newest
# global JSON. It also uses a ShareGPT-trained predictor on a ShareGPT trace.
# Therefore its outputs must not be described as LMSYS->ShareGPT OOD validation.
#
# Use scripts/run_one_experiment_safe.sh for all future runs.
if [[ "${ALLOW_UNSAFE_HISTORICAL_RUNNER:-0}" != "1" ]]; then
  echo "ERROR: Refusing deprecated unsafe runner." >&2
  echo "This script uses a shared output directory and global-latest-JSON" >&2
  echo "selection, which risks result contamination." >&2
  echo "" >&2
  echo "Use scripts/run_one_experiment_safe.sh for new experiments." >&2
  echo "To run this historical script for reproduction purposes only:" >&2
  echo "  ALLOW_UNSAFE_HISTORICAL_RUNNER=1 bash scripts/run_part2.sh" >&2
  exit 2
fi
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
