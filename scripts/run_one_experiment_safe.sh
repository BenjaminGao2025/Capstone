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

# 2. Input validation to prevent injection
if [[ "$PHASE" =~ [^a-zA-Z0-9_-] ]] || [[ "$ARM" =~ [^a-zA-Z0-9_-] ]] || [[ ! "$REQUEST_RATE" =~ ^[0-9]+(\.[0-9]+)?$ ]] || [[ ! "$SEED" =~ ^[0-9]+$ ]] || [[ ! "$NUM_PROMPTS" =~ ^[1-9][0-9]*$ ]]; then
    echo "ERROR: Invalid characters or values in inputs." >&2
    exit 1
fi

if [[ "$PHASE" == *..* ]] || [[ "$PHASE" == */* ]] || [[ "$PHASE" == *\\* ]] || [[ -z "$PHASE" ]]; then
    echo "ERROR: Path traversal detected in PHASE." >&2
    exit 1
fi

# 3. Numeric constraints
# REQUEST_RATE must be > 0
if (( $(echo "$REQUEST_RATE <= 0" | bc -l) )); then
    echo "ERROR: REQUEST_RATE must be > 0." >&2
    exit 1
fi

# 4. Determine which runner to use based on ARM
if [ -n "${RUNNER_SCRIPT:-}" ]; then
    SCRIPT_TO_RUN="$RUNNER_SCRIPT"
elif [ "$ARM" = "fcfs" ]; then
    SCRIPT_TO_RUN="scripts/run_fcfs.sh"
elif [ "$ARM" = "ltr" ]; then
    SCRIPT_TO_RUN="scripts/run_ltr.sh"
elif [ "$ARM" = "v1" ]; then
    SCRIPT_TO_RUN="scripts/run_ltr_aging.sh"
else
    echo "ERROR: ARM must be fcfs, ltr, or v1 unless RUNNER_SCRIPT is provided." >&2
    exit 1
fi

if [[ "$SCRIPT_TO_RUN" == *..* ]] || [ ! -f "$SCRIPT_TO_RUN" ]; then
    echo "ERROR: RUNNER_SCRIPT is invalid, contains path traversal, or does not exist." >&2
    exit 1
fi

# 5. Validate PREDICTOR safely if provided or required
if [[ "$ARM" == "ltr" || "$ARM" == "v1" ]]; then
    : "${PREDICTOR?ERROR: PREDICTOR environment variable is required for $ARM arm}"
    if [[ "$PREDICTOR" == *..* ]]; then
        echo "ERROR: Path traversal in PREDICTOR." >&2
        exit 1
    fi
    if [ ! -f "$PREDICTOR" ]; then
        echo "ERROR: PREDICTOR file does not exist or is not a regular file: $PREDICTOR" >&2
        exit 1
    fi
    export PREDICTOR
fi

# 6. For v1 arm, set AGING_GATE_S and PREEMPT_PROTECT defaults if not provided
if [[ "$ARM" == "v1" ]]; then
    export AGING_GATE_S="${AGING_GATE_S:-60}"
    export PREEMPT_PROTECT="${PREEMPT_PROTECT:-1}"
fi

# 7. Safe to create output directory now
OUT_DIR="${RESULT_ROOT}/${PHASE}/rate${REQUEST_RATE}/seed${SEED}/${ARM}"

if [ -d "$OUT_DIR" ] && [ "$(ls -A "$OUT_DIR" 2>/dev/null)" ]; then
    echo "ERROR: Output directory $OUT_DIR already exists and is not empty." >&2
    exit 1
fi

mkdir -p "$OUT_DIR"

# 8. Record JSON file set BEFORE running the underlying experiment
BEFORE_FILES="$OUT_DIR/.before_json_files"
find "$OUT_DIR" -maxdepth 1 -name "*.json" | sort > "$BEFORE_FILES"

# 9. Set RESULT_DIR to the isolated directory
export RESULT_DIR="$OUT_DIR"

# 10. Run the experiment, capturing exit code
echo "Starting experiment for ARM=$ARM in $OUT_DIR..."
set +e
bash "$SCRIPT_TO_RUN" > "$OUT_DIR/runner.log" 2>&1
RUN_EXIT_CODE=$?
set -e

# 11. Record JSON file set AFTER running
AFTER_FILES="$OUT_DIR/.after_json_files"
find "$OUT_DIR" -maxdepth 1 -name "*.json" | sort > "$AFTER_FILES"

# 12. Compute the diff (new files only)
NEW_JSONS=$(comm -13 "$BEFORE_FILES" "$AFTER_FILES")

# 13. If runner failed:
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

# 14. If no new JSON file appeared, fail
if [ -z "$NEW_JSONS" ]; then
    echo "ERROR: No new JSON results found in $OUT_DIR after successful run." >&2
    exit 1
fi

# 15. If more than one new JSON file appeared, fail
NUM_NEW_FILES=$(echo "$NEW_JSONS" | wc -l)
if [ "$NUM_NEW_FILES" -gt 1 ]; then
    echo "ERROR: Multiple new JSON results found in $OUT_DIR:" >&2
    echo "$NEW_JSONS" >&2
    exit 1
fi

# 16. The single new JSON is the result
RESULT_FILE="$NEW_JSONS"

# 17. Python Validation
echo "Validating result JSON..."
set +e
VALIDATOR_OUT=$(python3 scripts/validate_single_result.py \
    --result-path "$RESULT_FILE" \
    --arm "$ARM" \
    --request-rate "$REQUEST_RATE" \
    --expected-seed "$SEED" \
    --expected-prompts "$NUM_PROMPTS" 2>&1)
VAL_CODE=$?
set -e

if [ $VAL_CODE -ne 0 ]; then
    echo "ERROR: Validation failed:" >&2
    echo "$VALIDATOR_OUT" >&2
    exit 1
fi

# Parse the sidecar JSON output from validator using jq or python
HAS_SEED=$(echo "$VALIDATOR_OUT" | python3 -c 'import sys, json; print(json.load(sys.stdin).get("has_seed", False))' 2>/dev/null || echo "False")
HAS_GEN_TEXTS=$(echo "$VALIDATOR_OUT" | python3 -c 'import sys, json; print(json.load(sys.stdin).get("contains_generated_texts", False))' 2>/dev/null || echo "False")
ELIGIBLE=$(echo "$VALIDATOR_OUT" | python3 -c 'import sys, json; print(json.load(sys.stdin).get("eligible_for_public_submission", False))' 2>/dev/null || echo "False")

# Generate sanitized derivative if necessary
FINAL_RESULT_FILE="$RESULT_FILE"
if [ "$HAS_GEN_TEXTS" = "True" ]; then
    echo "Raw result contains generated_texts. Creating sanitized derivative..."
    SANITIZED_FILE="${RESULT_FILE%.json}_sanitized.json"
    python3 scripts/sanitize_result_json.py --input "$RESULT_FILE" --output "$SANITIZED_FILE" || exit 1
    # Check the newly sanitized file to ensure it's clean and safe
    SANITIZED_VALIDATOR_OUT=$(python3 scripts/validate_single_result.py \
        --result-path "$SANITIZED_FILE" \
        --arm "$ARM" \
        --request-rate "$REQUEST_RATE" \
        --expected-seed "$SEED" \
        --expected-prompts "$NUM_PROMPTS")
    
    if [ $? -ne 0 ]; then
        echo "ERROR: Sanitized file validation failed:" >&2
        echo "$SANITIZED_VALIDATOR_OUT" >&2
        exit 1
    fi
    ELIGIBLE=$(echo "$SANITIZED_VALIDATOR_OUT" | python3 -c 'import sys, json; print(json.load(sys.stdin).get("eligible_for_public_submission", False))' 2>/dev/null || echo "False")
    FINAL_RESULT_FILE="$SANITIZED_FILE"
fi

ELIGIBLE_JSON="false"
if [ "$ELIGIBLE" = "True" ]; then
    ELIGIBLE_JSON="true"
fi

SEED_VERIFICATION="verified_from_result"
if [ "$HAS_SEED" = "False" ]; then
    SEED_VERIFICATION="requested_only_not_embedded_in_result"
fi

# 18. Record metadata:
RESULT_SHA=$(shasum -a 256 "$FINAL_RESULT_FILE" | awk '{print $1}')

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
    "result_file": "$(basename "$FINAL_RESULT_FILE")",
    "result_sha256": "$RESULT_SHA",
    "predictor_sha256": $PREDICTOR_SHA,
    "repo_commit": "$REPO_COMMIT",
    "source_script": "$SCRIPT_TO_RUN",
    "timestamp": "$TIMESTAMP",
    "status": "success",
    "eligible_for_aggregation": $ELIGIBLE_JSON
}
EOF

echo "Experiment successful. Manifest and results written to $OUT_DIR."
exit 0
