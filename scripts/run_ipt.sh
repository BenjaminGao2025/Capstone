#!/bin/bash
# LTR-ours (ipt): internal-predictor scheduling — main-model hidden state + tiny head
# No aux engine, no external predictor; head loaded by the worker via IPT_HEAD_PATH.
# Smoke:  NUM_PROMPTS=50 REQUEST_RATE=4 bash run_ipt.sh
# Full:   NUM_PROMPTS=500 REQUEST_RATE=8 bash run_ipt.sh
set -e
source /hy-tmp/env.sh

MODEL="${MODEL:-/hy-tmp/models/Meta-Llama-3-8B-Instruct}"
TOKENIZER="${TOKENIZER:-$MODEL}"
DATASET="${DATASET:-lmsys-Meta-Llama-3-8B-Instruct-t1.0-s0-l8192-c10000-rFalse.jsonl}"
NUM_PROMPTS="${NUM_PROMPTS:-500}"
REQUEST_RATE="${REQUEST_RATE:-8}"
OUTPUT_LEN="${OUTPUT_LEN:--1}"
SEED="${SEED:-0}"
SWAP_SPACE="${SWAP_SPACE:-4}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-8192}"
PORT="${PORT:-3343}"
export IPT_HEAD_PATH="${IPT_HEAD_PATH:-/hy-tmp/models/egtp_head_last32.pt}"
RESULT_DIR=/hy-tmp/results
SCHED=ipt-xxx

cd /hy-tmp/vllm-ltr/benchmarks
mkdir -p "$RESULT_DIR"

python3 -m vllm.entrypoints.openai.api_server \
  --model "$MODEL" --swap-space "$SWAP_SPACE" --disable-log-requests \
  --schedule-type $SCHED --enable-chunked-prefill --enforce-eager \
  --max-model-len "$MAX_MODEL_LEN" \
  --port "$PORT" > "$RESULT_DIR/server-ipt-$(date +%Y%m%d-%H%M%S).log" 2>&1 &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null; wait $SERVER_PID 2>/dev/null || true' EXIT

echo "waiting for server (pid=$SERVER_PID) ..."
for i in $(seq 1 120); do
  curl -sf "localhost:$PORT/health" >/dev/null 2>&1 && break
  kill -0 $SERVER_PID 2>/dev/null || { echo "SERVER DIED, log tail:"; tail -30 "$RESULT_DIR"/server-ipt-*.log | tail -30; exit 1; }
  sleep 5
done
curl -sf "localhost:$PORT/health" >/dev/null || { echo "server not healthy after 600s"; exit 1; }
echo "server healthy: sched=$SCHED head=$IPT_HEAD_PATH n=$NUM_PROMPTS rate=$REQUEST_RATE"

python3 benchmark_serving_real.py --backend vllm \
  --model "$MODEL" --tokenizer "$TOKENIZER" \
  --dataset "$DATASET" --num-prompts "$NUM_PROMPTS" \
  --schedule-type $SCHED --output-len "$OUTPUT_LEN" \
  --request-rate "$REQUEST_RATE" --seed "$SEED" \
  --result-dir "$RESULT_DIR" --port "$PORT"

echo "DONE. JSON results in $RESULT_DIR:"
ls -t "$RESULT_DIR"/*.json | head -2
