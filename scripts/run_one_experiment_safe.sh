#!/bin/bash
# Safe single-experiment runner with fail-closed result collection.
# Replaces the dangerous global-latest-JSON pattern used in historical runners.
#
# Required environment variables:
#   PHASE         - experiment phase (e.g., phase_a, phase_d)
#   ARM           - arm name (fcfs, ltr, v1)
#   REQUEST_RATE  - request rate
#   SEED          - random seed
#   NUM_PROMPTS   - number of prompts
#   RESULT_ROOT   - root directory for results
#
# Required for LTR/V1 arms:
#   PREDICTOR     - predictor config path
#
# Optional:
#   AGING_GATE_S     - aging gate threshold (required for v1 arm)
#   PREEMPT_PROTECT  - enable preemption protection (required for v1 arm)
#   MODEL            - model path
#   DATASET          - dataset file name
#   RUNNER_SCRIPT    - path to the underlying runner script

set -euo pipefail

# 1. Validate all required env vars are set (fail with clear error if missing)
: "${PHASE?ERROR: PHASE environment variable is required}"
: "${ARM?ERROR: ARM environment variable is required}"
: "${REQUEST_RATE?ERROR: REQUEST_RATE environment variable is required}"
: "${SEED?ERROR: SEED environment variable is required}"
: "${NUM_PROMPTS?ERROR: NUM_PROMPTS environment variable is required}"
: "${RESULT_ROOT?ERROR: RESULT_ROOT environment variable is required}"

# Input validation to prevent injection
if [[ "$PHASE" =~ [^a-zA-Z0-9_-] ]] || [[ "$ARM" =~ [^a-zA-Z0-9_-] ]] || [[ ! "$REQUEST_RATE" =~ ^[0-9]+(\.[0-9]+)?$ ]] || [[ ! "$SEED" =~ ^[0-9]+$ ]] || [[ ! "$NUM_PROMPTS" =~ ^[1-9][0-9]*$ ]]; then
    echo "ERROR: Invalid characters or values in inputs." >&2
    exit 1
fi

if [[ "$PHASE" == *..* ]] || [[ "$PHASE" == */* ]] || [[ "$PHASE" == *\\* ]] || [[ -z "$PHASE" ]]; then
    echo "ERROR: Path traversal detected in PHASE." >&2
    exit 1
fi

# Allow only standard arms unless RUNNER_SCRIPT is defined
if [[ -z "${RUNNER_SCRIPT:-}" ]]; then
    if [[ "$ARM" != "fcfs" && "$ARM" != "ltr" && "$ARM" != "v1" ]]; then
        echo "ERROR: ARM must be fcfs, ltr, or v1 unless RUNNER_SCRIPT is provided." >&2
        exit 1
    fi
else
    if [ ! -f "$RUNNER_SCRIPT" ] || [[ "$RUNNER_SCRIPT" == *..* ]]; then
        echo "ERROR: RUNNER_SCRIPT is invalid or contains path traversal." >&2
        exit 1
    fi
fi

# Validate PREDICTOR safely if provided
if [ -n "${PREDICTOR:-}" ]; then
    if [[ "$PREDICTOR" == *..* ]]; then
        echo "ERROR: Path traversal in PREDICTOR." >&2
        exit 1
    fi
fi

# 2. Create output directory
OUT_DIR="${RESULT_ROOT}/${PHASE}/rate${REQUEST_RATE}/seed${SEED}/${ARM}"

# 3. If directory exists and is non-empty, fail immediately
if [ -d "$OUT_DIR" ] && [ "$(ls -A "$OUT_DIR" 2>/dev/null)" ]; then
    echo "ERROR: Output directory $OUT_DIR already exists and is not empty." >&2
    exit 1
fi

mkdir -p "$OUT_DIR"

# 4. Record JSON file set BEFORE running the underlying experiment
BEFORE_FILES="$OUT_DIR/.before_json_files"
find "$OUT_DIR" -maxdepth 1 -name "*.json" | sort > "$BEFORE_FILES"

# 5. Set RESULT_DIR to the isolated directory
export RESULT_DIR="$OUT_DIR"

# 6. Determine which runner to use based on ARM
if [ -n "${RUNNER_SCRIPT:-}" ]; then
    SCRIPT_TO_RUN="$RUNNER_SCRIPT"
elif [ "$ARM" = "fcfs" ]; then
    SCRIPT_TO_RUN="scripts/run_fcfs.sh"
elif [ "$ARM" = "ltr" ]; then
    SCRIPT_TO_RUN="scripts/run_ltr.sh"
elif [ "$ARM" = "v1" ]; then
    SCRIPT_TO_RUN="scripts/run_ltr_aging.sh"
fi

if [ ! -f "$SCRIPT_TO_RUN" ]; then
    echo "ERROR: Runner script $SCRIPT_TO_RUN does not exist." >&2
    exit 1
fi

# 7. For ltr/v1 arms, verify PREDICTOR is set and exists
if [[ "$ARM" == "ltr" || "$ARM" == "v1" ]]; then
    : "${PREDICTOR?ERROR: PREDICTOR environment variable is required for $ARM arm}"
    if [ ! -f "$PREDICTOR" ]; then
        echo "ERROR: PREDICTOR file does not exist: $PREDICTOR" >&2
        exit 1
    fi
    export PREDICTOR
fi

# 8. For v1 arm, set AGING_GATE_S and PREEMPT_PROTECT defaults if not provided
if [[ "$ARM" == "v1" ]]; then
    export AGING_GATE_S="${AGING_GATE_S:-60}"
    export PREEMPT_PROTECT="${PREEMPT_PROTECT:-1}"
fi

# 9. Run the experiment, capturing exit code
echo "Starting experiment for ARM=$ARM in $OUT_DIR..."
set +e
bash "$SCRIPT_TO_RUN" > "$OUT_DIR/runner.log" 2>&1
RUN_EXIT_CODE=$?
set -e

# 10. Record JSON file set AFTER running
AFTER_FILES="$OUT_DIR/.after_json_files"
find "$OUT_DIR" -maxdepth 1 -name "*.json" | sort > "$AFTER_FILES"

# 11. Compute the diff (new files only)
NEW_JSONS=$(comm -13 "$BEFORE_FILES" "$AFTER_FILES")

# 12. If runner failed:
if [ $RUN_EXIT_CODE -ne 0 ]; then
    echo "Runner script failed with exit code $RUN_EXIT_CODE." >&2
    cp "$OUT_DIR/runner.log" "$OUT_DIR/crash.log"
    cat <<EOF > "$OUT_DIR/crash_manifest.json"
{
    "status": "crashed",
    "eligible_for_aggregation": false
}
EOF
    exit $RUN_EXIT_CODE
fi

# 13. If no new JSON file appeared, fail
if [ -z "$NEW_JSONS" ]; then
    echo "ERROR: No new JSON results found in $OUT_DIR after successful run." >&2
    exit 1
fi

# 14. If more than one new JSON file appeared, fail
NUM_NEW_FILES=$(echo "$NEW_JSONS" | wc -l)
if [ "$NUM_NEW_FILES" -gt 1 ]; then
    echo "ERROR: Multiple new JSON results found in $OUT_DIR:" >&2
    echo "$NEW_JSONS" >&2
    exit 1
fi

# 15. The single new JSON is the result
RESULT_FILE="$NEW_JSONS"

# 16. Python Validation
echo "Validating result JSON..."
python3 scripts/validate_single_result.py \
    --result-path "$RESULT_FILE" \
    --arm "$ARM" \
    --request-rate "$REQUEST_RATE" \
    --expected-seed "$SEED" \
    --expected-prompts "$NUM_PROMPTS" || exit 1

# Check if seed was found in JSON
HAS_SEED=$(python3 -c "import json; print('true' if 'seed' in json.load(open('$RESULT_FILE')) else 'false')" 2>/dev/null || echo "false")
SEED_VERIFICATION="verified_from_result"
if [ "$HAS_SEED" = "false" ]; then
    SEED_VERIFICATION="requested_only_not_embedded_in_result"
fi

# 17. Record metadata:
RESULT_SHA=$(shasum -a 256 "$RESULT_FILE" | awk '{print $1}')

PREDICTOR_SHA="null"
if [ -n "${PREDICTOR:-}" ] && [ -f "$PREDICTOR" ]; then
    PREDICTOR_SHA='"'"$(shasum -a 256 "$PREDICTOR" | awk '{print $1}')"'"'
fi

REPO_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")



# 19. Write experiment_manifest.json ONLY after all passes
cat <<EOF > "$OUT_DIR/experiment_manifest.json"
{
    "phase": "$PHASE",
    "arm": "$ARM",
    "request_rate": $REQUEST_RATE,
    "seed": $SEED,
    "requested_seed": $SEED,
    "seed_verification": "$SEED_VERIFICATION",
    "num_prompts": $NUM_PROMPTS,
    "result_file": "$(basename "$RESULT_FILE")",
    "result_sha256": "$RESULT_SHA",
    "predictor_sha256": $PREDICTOR_SHA,
    "repo_commit": "$REPO_COMMIT",
    "source_script": "$SCRIPT_TO_RUN",
    "timestamp": "$TIMESTAMP",
    "status": "success",
    "eligible_for_aggregation": true
}
EOF

echo "Experiment successful. Manifest and results written to $OUT_DIR."
exit 0
