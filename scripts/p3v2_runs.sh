#!/bin/bash
# P3 v2 session: 4x v2-policy runs + 2x head-swap ablation runs.
# Every run is verified: completed==NUM_PROMPTS in the produced JSON,
# else marked FAILED (lesson from WP4's misleading OK markers).
set -e
source /hy-tmp/env.sh
R=/hy-tmp/results
LMSYS="lmsys-Meta-Llama-3-8B-Instruct-t1.0-s0-l8192-c10000-rFalse.jsonl"
SGPT="llama3-8b-sharegpt-test-t1-s0-8192.jsonl"
PORT=3343
MODEL=/hy-tmp/models/Meta-Llama-3-8B-Instruct

verify_last_json () {  # $1=glob pattern  $2=tag-suffix to append
  f=$(ls -t $R/$1 2>/dev/null | grep -v -- "-v2\|-ablation\|ood-sharegpt\." | head -1)
  n=$(python3 -c "import json,sys; print(json.load(open('$f'))['completed'])" 2>/dev/null || echo 0)
  mv "$f" "${f%.json}$2.json"
  if [ "$n" = "500" ]; then echo "VERIFIED_OK $2 n=$n ${f##*/}"; else echo "VERIFIED_FAILED $2 n=$n ${f##*/}"; fi
}

run_one () {  # $1=sched $2=dataset $3=rate $4=extra-server-env $5=tag
  echo "=== P3V2 RUN $5 (sched=$1 rate=$3) ==="
  env $4 python3 -m vllm.entrypoints.openai.api_server \
    --model "$MODEL" --swap-space 4 --disable-log-requests \
    --schedule-type "$1" --enable-chunked-prefill --enforce-eager \
    --max-model-len 8192 --port $PORT > "$R/server-$5-$(date +%H%M%S).log" 2>&1 &
  SPID=$!
  for i in $(seq 1 120); do
    curl -sf "localhost:$PORT/health" >/dev/null 2>&1 && break
    kill -0 $SPID 2>/dev/null || { echo "SERVER_DIED_AT_START $5"; return 1; }
    sleep 5
  done
  cd /hy-tmp/vllm-ltr/benchmarks
  python3 benchmark_serving_real.py --backend vllm --model "$MODEL" --tokenizer "$MODEL" \
    --dataset "$2" --num-prompts 500 --schedule-type "$1" --output-len -1 \
    --request-rate "$3" --seed 0 --result-dir "$R" --port $PORT || echo "CLIENT_ERR $5"
  kill $SPID 2>/dev/null; wait $SPID 2>/dev/null || true
  sleep 15
}

cd /hy-tmp/vllm-ltr/benchmarks

# ---- Task 1: v2 policy (ipt head live in worker) ----
run_one ipt-xxx "$LMSYS" 8  "IPT_HEAD_PATH=/hy-tmp/models/egtp_head_last32.pt" v2-lmsys-r8
verify_last_json "vllm-8.0qps-*ipt-xxx*.json" "-v2"
run_one ipt-xxx "$LMSYS" 32 "IPT_HEAD_PATH=/hy-tmp/models/egtp_head_last32.pt" v2-lmsys-r32
verify_last_json "vllm-32.0qps-*ipt-xxx*.json" "-v2"
run_one ipt-xxx "$SGPT" 4  "IPT_HEAD_PATH=/hy-tmp/models/egtp_head_last32.pt" v2-ood-r4
verify_last_json "vllm-4.0qps-*ipt-xxx*.json" "-v2-ood-sharegpt"
run_one ipt-xxx "$SGPT" 8  "IPT_HEAD_PATH=/hy-tmp/models/egtp_head_last32.pt" v2-ood-r8
verify_last_json "vllm-8.0qps-*ipt-xxx*.json" "-v2-ood-sharegpt"

# ---- Task 2: head-swap ablation (ORIGINAL opt policy + our head's scores) ----
run_one opt-xxx "$LMSYS" 8 "IPT_SCORE_FILE=/hy-tmp/models/ipt_scores_lmsys.json" abl-lmsys-r8
verify_last_json "vllm-8.0qps-*opt-xxx*.json" "-ablation-ourshead"
run_one opt-xxx "$SGPT" 4 "IPT_SCORE_FILE=/hy-tmp/models/ipt_scores_sharegpt.json" abl-ood-r4
verify_last_json "vllm-4.0qps-*opt-xxx*.json" "-ablation-ourshead-ood-sharegpt"

echo "P3V2_ALL_DONE"
grep -h "VERIFIED" /dev/null 2>/dev/null; true
