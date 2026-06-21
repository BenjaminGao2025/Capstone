#!/bin/bash
# FCFS baseline — vllm-ltr (commit 13bbf6ff), in-distribution LMSYS trace
# Smoke defaults: facebook/opt-1.3b, 50 prompts, output-len 128
# Llama run:  MODEL=meta-llama/Llama-3.1-8B-Instruct OUTPUT_LEN=-1 NUM_PROMPTS=500 ./run_fcfs.sh
set -e
source /hy-tmp/env.sh

MODEL="${MODEL:-facebook/opt-1.3b}"
TOKENIZER="${TOKENIZER:-$MODEL}"
DATASET="${DATASET:-lmsys-Meta-Llama-3-8B-Instruct-t1.0-s0-l8192-c10000-rFalse.jsonl}"
NUM_PROMPTS="${NUM_PROMPTS:-50}"
REQUEST_RATE="${REQUEST_RATE:-8}"
OUTPUT_LEN="${OUTPUT_LEN:-128}"   # -1 = replay true trace output lengths
SEED="${SEED:-0}"
SWAP_SPACE="${SWAP_SPACE:-8}"     # cgroup RAM limit is 23GiB — do not raise blindly
PORT="${PORT:-3343}"
RESULT_DIR=/hy-tmp/results
SCHED=fcfs
MAXLEN_ARG=""
[ -n "$MAX_MODEL_LEN" ] && MAXLEN_ARG="--max-model-len $MAX_MODEL_LEN"

cd /hy-tmp/vllm-ltr/benchmarks
mkdir -p "$RESULT_DIR"

python3 -m vllm.entrypoints.openai.api_server \
  --model "$MODEL" --swap-space "$SWAP_SPACE" --disable-log-requests \
  --schedule-type $SCHED --enable-chunked-prefill --enforce-eager $MAXLEN_ARG \
  --port "$PORT" > "$RESULT_DIR/server-$SCHED-$(date +%Y%m%d-%H%M%S).log" 2>&1 &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null; wait $SERVER_PID 2>/dev/null || true' EXIT

echo "waiting for server (pid=$SERVER_PID) ..."
for i in $(seq 1 120); do
  curl -sf "localhost:$PORT/health" >/dev/null 2>&1 && break
  kill -0 $SERVER_PID 2>/dev/null || { echo "SERVER DIED, log tail:"; tail -30 "$RESULT_DIR"/server-$SCHED-*.log | tail -30; exit 1; }
  sleep 5
done
curl -sf "localhost:$PORT/health" >/dev/null || { echo "server not healthy after 600s"; exit 1; }
echo "server healthy, starting benchmark: sched=$SCHED model=$MODEL n=$NUM_PROMPTS rate=$REQUEST_RATE seed=$SEED"

python3 benchmark_serving_real.py --backend vllm \
  --model "$MODEL" --tokenizer "$TOKENIZER" \
  --dataset "$DATASET" --num-prompts "$NUM_PROMPTS" \
  --schedule-type $SCHED --output-len "$OUTPUT_LEN" \
  --request-rate "$REQUEST_RATE" --seed "$SEED" \
  --result-dir "$RESULT_DIR" --port "$PORT"

echo "DONE. JSON results in $RESULT_DIR:"
ls -t "$RESULT_DIR"/*.json | head -3
