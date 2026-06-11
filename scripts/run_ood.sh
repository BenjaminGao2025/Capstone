#!/bin/bash
# OOD 失效证据初版:ShareGPT trace × lmsys-score 预测器(故意分布错配)
# rate=8 一档,两臂各一轮,JSON 重命名加 -ood-sharegpt 标记
# 注意:LTR 臂的 PREDICTOR 保持 run_ltr.sh 默认值(lmsys-score)= 错配的来源,勿改
set -e
source /hy-tmp/env.sh
export MODEL=/hy-tmp/models/Meta-Llama-3-8B-Instruct
export DATASET=llama3-8b-sharegpt-test-t1-s0-8192.jsonl
export OUTPUT_LEN=-1
export NUM_PROMPTS=500
export REQUEST_RATE="${REQUEST_RATE:-8}"
export SEED=0
export MAX_MODEL_LEN=8192
export SWAP_SPACE="${SWAP_SPACE:-4}"
R=/hy-tmp/results

echo "=== OOD: FCFS (sharegpt trace) ==="
bash /hy-tmp/scripts/run_fcfs.sh
f=$(ls -t $R/vllm-*-fcfs-*.json | head -1)
mv "$f" "${f%.json}-ood-sharegpt.json"
echo "renamed -> ${f%.json}-ood-sharegpt.json"
sleep 20

echo "=== OOD: LTR (sharegpt trace x lmsys-score predictor, 故意错配) ==="
bash /hy-tmp/scripts/run_ltr.sh
f=$(ls -t $R/vllm-*-opt-xxx-*.json | head -1)
mv "$f" "${f%.json}-ood-sharegpt.json"
echo "renamed -> ${f%.json}-ood-sharegpt.json"

echo "OOD_DONE"
ls -lh $R/*ood*.json
