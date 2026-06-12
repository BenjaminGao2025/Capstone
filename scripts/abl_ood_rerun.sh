#!/bin/bash
set -e
source /hy-tmp/env.sh
R=/hy-tmp/results
SGPT="llama3-8b-sharegpt-test-t1-s0-8192.jsonl"
MODEL=/hy-tmp/models/Meta-Llama-3-8B-Instruct
PORT=3343
echo "=== ABL-OOD-R4 RERUN (opt-xxx + FileAuxScorer, sharegpt, rate 4) ==="
env IPT_SCORE_FILE=/hy-tmp/models/ipt_scores_sharegpt.json python3 -m vllm.entrypoints.openai.api_server \
  --model "$MODEL" --swap-space 4 --disable-log-requests \
  --schedule-type opt-xxx --enable-chunked-prefill --enforce-eager \
  --max-model-len 8192 --port $PORT > "$R/server-abl-ood-rerun.log" 2>&1 &
SPID=$!
for i in $(seq 1 120); do
  curl -sf "localhost:$PORT/health" >/dev/null 2>&1 && break
  kill -0 $SPID 2>/dev/null || { echo "SERVER_DIED_AT_START"; exit 1; }
  sleep 5
done
cd /hy-tmp/vllm-ltr/benchmarks
python3 benchmark_serving_real.py --backend vllm --model "$MODEL" --tokenizer "$MODEL" \
  --dataset "$SGPT" --num-prompts 500 --schedule-type opt-xxx --output-len -1 \
  --request-rate 4 --seed 0 --result-dir "$R" --port $PORT || echo CLIENT_ERR
kill $SPID 2>/dev/null; wait $SPID 2>/dev/null || true
f=$(ls -t $R/vllm-4.0qps-*opt-xxx*.json | grep -v -- "-ablation\|ood-sharegpt\." | head -1)
n=$(python3 -c "import json;print(json.load(open(\"$f\"))[\"completed\"])")
mv "$f" "${f%.json}-ablation-ourshead-ood-sharegpt.json"
echo "ABL_RERUN_RESULT n=$n/500 file=${f##*/}"
echo "ABL_RERUN_DONE"
