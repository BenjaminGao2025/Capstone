#!/bin/bash
# OOD aging-gate validation: 3 arms × 2 rates on ShareGPT trace
#
# Arms:  FCFS | LTR (opt) | LTR+aging (opt-aging, W≈8 → AGING_GATE_S=120s)
# Rates: 4 and 8
# Trace: ShareGPT (OOD — predictor trained on LMSYS)
#
# SWAP_SPACE=4 matches the original rate-8 crash configuration.
# The FCFS and LTR arms at rate-4 should reproduce committed baselines
# (FCFS mean TTFT ≈40,892ms, LTR ≈23,810ms).  If they differ, the
# discrepancy is flagged — existing committed values are NOT overwritten.
#
# Expected outcome at rate-8:
#   FCFS: completes (500/500)
#   LTR:  crashes (swap exhaustion from preemption churn)
#   LTR+aging: should complete if the gate bounds preemption
#
# Usage:
#   bash run_ood_aging.sh
#   # Optional: AGING_GATE_S=180 bash run_ood_aging.sh
set -e
source /hy-tmp/env.sh

export MODEL=/hy-tmp/models/Meta-Llama-3-8B-Instruct
export DATASET=llama3-8b-sharegpt-test-t1-s0-8192.jsonl
export OUTPUT_LEN=-1
export NUM_PROMPTS=500
export SEED=0
export MAX_MODEL_LEN=8192
export SWAP_SPACE=4   # MUST match original crash configuration — do not change

R=/hy-tmp/results
AGING_GATE_S="${AGING_GATE_S:-120}"
export AGING_GATE_S

echo "============================================================"
echo "OOD Aging-Gate Validation"
echo "  SWAP_SPACE=$SWAP_SPACE  AGING_GATE_S=${AGING_GATE_S}s"
echo "  Arms: FCFS / LTR(opt) / LTR+aging(opt-aging)"
echo "  Rates: 4, 8"
echo "============================================================"

for RATE in 4 8; do
  export REQUEST_RATE=$RATE
  echo ""
  echo "========== rate=$RATE =========="

  echo "--- rate=$RATE : FCFS ---"
  bash /hy-tmp/scripts/run_fcfs.sh
  f=$(ls -t $R/vllm-*-fcfs-*.json 2>/dev/null | head -1)
  if [ -n "$f" ]; then
    mv "$f" "${f%.json}-ood-sharegpt-aging-val.json"
    echo "renamed -> ${f%.json}-ood-sharegpt-aging-val.json"
  fi
  sleep 20

  echo "--- rate=$RATE : LTR (opt, baseline — expect crash at rate=8) ---"
  # At rate=8, LTR is expected to crash. Capture exit code but don't abort.
  set +e
  bash /hy-tmp/scripts/run_ltr.sh
  LTR_EXIT=$?
  set -e
  if [ $LTR_EXIT -ne 0 ]; then
    echo "WARNING: LTR exited with code $LTR_EXIT (expected at rate=8 due to swap exhaustion)"
  fi
  f=$(ls -t $R/vllm-*-opt-xxx-*.json 2>/dev/null | head -1)
  if [ -n "$f" ]; then
    mv "$f" "${f%.json}-ood-sharegpt-aging-val.json"
    echo "renamed -> ${f%.json}-ood-sharegpt-aging-val.json"
  fi
  sleep 20

  echo "--- rate=$RATE : LTR+aging (opt-aging, AGING_GATE_S=${AGING_GATE_S}s) ---"
  bash /hy-tmp/scripts/run_ltr_aging.sh
  f=$(ls -t $R/vllm-*-opt-aging-xxx-*.json 2>/dev/null | head -1)
  if [ -n "$f" ]; then
    mv "$f" "${f%.json}-ood-sharegpt-aging-val.json"
    echo "renamed -> ${f%.json}-ood-sharegpt-aging-val.json"
  fi
  sleep 20
done

echo ""
echo "============================================================"
echo "OOD_AGING_VALIDATION_DONE"
echo "Results:"
ls -lh $R/*aging-val*.json 2>/dev/null || echo "(no JSON files — check for crashes)"
echo ""
echo "Server logs:"
ls -lh $R/server-*.log | tail -10
echo "============================================================"
