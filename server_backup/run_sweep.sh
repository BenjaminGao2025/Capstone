export MODEL=/hy-tmp/models/Meta-Llama-3-8B-Instruct
export DATASET=llama3-8b-sharegpt-test-t1-s0-8192.jsonl
export OUTPUT_LEN=-1
export NUM_PROMPTS=500
export SEED=0
export MAX_MODEL_LEN=8192
export SWAP_SPACE=4
export REQUEST_RATE=4

for GATE in 30 60; do
  echo "Running AGING_GATE_S=$GATE at RATE=4"
  export AGING_GATE_S=$GATE
  bash /hy-tmp/scripts/run_ltr_aging.sh
done
