#!/bin/bash
set -e
source /hy-tmp/env.sh
LMSYS="lmsys-Meta-Llama-3-8B-Instruct-t1.0-s0-l8192-c10000-rFalse.jsonl"
SGPT="llama3-8b-sharegpt-test-t1-s0-8192.jsonl"
for CFG in "lmsys:8:$LMSYS" "lmsys:16:$LMSYS" "lmsys:32:$LMSYS" "ood:4:$SGPT" "ood-crashreplay:8:$SGPT"; do
  TAG="${CFG%%:*}"; REST="${CFG#*:}"; RATE="${REST%%:*}"; DS="${REST#*:}"
  echo "=== WP4 $TAG rate=$RATE ==="
  if env DATASET="$DS" NUM_PROMPTS=500 REQUEST_RATE=$RATE bash /hy-tmp/scripts/run_ipt.sh; then
    echo "WP4_RUN_OK $TAG rate=$RATE"
  else
    echo "WP4_RUN_FAILED $TAG rate=$RATE (continuing)"
  fi
  sleep 20
done
echo "WP4_DONE"
