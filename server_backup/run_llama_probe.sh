#!/bin/bash
# 8B 正式实验前的水位探测:SWAP_SPACE=4 起步,500 prompts / rate 8 / seed 0,FCFS+LTR 各一轮
# 同时每 5s 采样 cgroup 内存,结束报告峰值和 preemption 次数
set -e
source /hy-tmp/env.sh
export MODEL=/hy-tmp/models/Meta-Llama-3-8B-Instruct
export OUTPUT_LEN=-1          # 真实 trace 回放
export NUM_PROMPTS=500
export REQUEST_RATE=8
export SEED=0
export SWAP_SPACE="${SWAP_SPACE:-4}"
export MAX_MODEL_LEN=8192

WM=/hy-tmp/results/mem-watermark-$(date +%Y%m%d-%H%M%S).log
( while true; do echo "$(date +%H:%M:%S) $(cat /sys/fs/cgroup/memory/memory.usage_in_bytes)"; sleep 5; done > "$WM" ) &
SAMPLER=$!
trap 'kill $SAMPLER 2>/dev/null || true' EXIT

echo "=== PROBE: FCFS (swap=$SWAP_SPACE) ==="
bash /hy-tmp/scripts/run_fcfs.sh
sleep 20
echo "=== PROBE: LTR (swap=$SWAP_SPACE) ==="
bash /hy-tmp/scripts/run_ltr.sh

PEAK=$(awk '{if($2>m)m=$2} END{printf "%.1f", m/1073741824}' "$WM")
echo "=== PEAK cgroup memory: ${PEAK} GiB / 23.0 GiB limit (采样日志: $WM) ==="
echo "=== preemption 证据(最近两个 server 日志) ==="
for f in $(ls -t /hy-tmp/results/server-*.log | head -2); do
  echo "$f: $(grep -ic preempt "$f" 2>/dev/null || echo 0) 行含 preempt"
done
echo "PROBE_DONE"
