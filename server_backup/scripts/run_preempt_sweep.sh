#!/bin/bash
export MODEL=/hy-tmp/models/Meta-Llama-3-8B-Instruct
export DATASET=llama3-8b-sharegpt-test-t1-s0-8192.jsonl
export OUTPUT_LEN=-1
export NUM_PROMPTS=500
export SEED=0
export MAX_MODEL_LEN=8192
export SWAP_SPACE=4
export PREEMPT_PROTECT=1

for RATE in 4 8; do
    for GATE in 30 60; do
        export REQUEST_RATE=$RATE
        export AGING_GATE_S=$GATE
        echo "Starting Rate $RATE, Gate $GATE"
        bash /hy-tmp/scripts/run_ltr_aging.sh || echo "Run crashed at Rate $RATE, Gate $GATE"
        sleep 5
    done
done
