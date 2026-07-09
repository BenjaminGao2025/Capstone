#!/bin/bash
# classification 调度臂(论文 Fig.3 的第三条线):rate 2-32 五档
# 与 bench-lmsys.sh 的 opt-class10 段同口径:tpt-class10-xxx + class-trainbucket820 预测器
set -e
source /hy-tmp/env.sh
export MODEL=/hy-tmp/models/Meta-Llama-3-8B-Instruct
export DATASET="lmsys-Meta-Llama-3-8B-Instruct-t1.0-s0-l8192-c10000-rFalse.jsonl"
export OUTPUT_LEN=-1
export NUM_PROMPTS=500
export SEED=0
export MAX_MODEL_LEN=8192
export SWAP_SPACE="${SWAP_SPACE:-4}"
PREDICTOR_CFG="MODEL/results/opt-125m-llama3-8b-lmsys-class-trainbucket820-b32/usage_config.json"
SCHED=tpt-class10-xxx
R=/hy-tmp/results
PORT=3343

cd /hy-tmp/vllm-ltr/benchmarks
for RATE in 2 4 8 16 32; do
  echo "=== class arm rate=$RATE ==="
  python3 -m vllm.entrypoints.openai.api_server \
    --model "$MODEL" --swap-space "$SWAP_SPACE" --disable-log-requests \
    --schedule-type $SCHED --enable-chunked-prefill --enforce-eager \
    --max-model-len "$MAX_MODEL_LEN" \
    --prefill-predictor-model-config "$PREDICTOR_CFG" \
    --port $PORT > "$R/server-class-$(date +%Y%m%d-%H%M%S).log" 2>&1 &
  SERVER_PID=$!
  for i in $(seq 1 120); do
    curl -sf "localhost:$PORT/health" >/dev/null 2>&1 && break
    kill -0 $SERVER_PID 2>/dev/null || { echo "SERVER DIED"; tail -20 "$R"/server-class-*.log | tail -20; exit 1; }
    sleep 5
  done
  curl -sf "localhost:$PORT/health" >/dev/null || { echo "not healthy"; exit 1; }
  python3 benchmark_serving_real.py --backend vllm \
    --model "$MODEL" --tokenizer "$MODEL" \
    --dataset "$DATASET" --num-prompts "$NUM_PROMPTS" \
    --schedule-type $SCHED --output-len "$OUTPUT_LEN" \
    --request-rate "$RATE" --seed "$SEED" \
    --result-dir "$R" --port $PORT
  kill $SERVER_PID 2>/dev/null; wait $SERVER_PID 2>/dev/null || true
  sleep 20
done
echo "CLASS_SWEEP_DONE"
ls -t $R/vllm-*tpt-class*.json | head -5
