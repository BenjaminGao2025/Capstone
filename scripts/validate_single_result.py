#!/usr/bin/env python3
import json
import sys
import argparse
import re

SECRET_PATTERNS = [
    re.compile(r"hooks\.slack"),
    re.compile(r"xox[baprs]-"),
    re.compile(r"ghp_"),
    re.compile(r"github_pat_"),
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"BEGIN PRIVATE KEY")
]

def check_secrets_stream(filepath):
    with open(filepath, "r", errors="ignore") as f:
        for line in f:
            for pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    return True
    return False

def main():
    parser = argparse.ArgumentParser(description="Validate single experiment result JSON")
    parser.add_argument("--result-path", required=True, help="Path to result JSON")
    parser.add_argument("--arm", required=True, help="Experiment arm")
    parser.add_argument("--request-rate", required=True, type=float, help="Expected request rate")
    parser.add_argument("--expected-seed", required=True, type=int, help="Expected random seed")
    parser.add_argument("--expected-prompts", required=True, type=int, help="Expected number of completed prompts")
    args = parser.parse_args()

    result_file = args.result_path
    
    try:
        with open(result_file, "r") as f:
            data = json.load(f)
    except Exception as e:
        print(f"ERROR: Failed to parse JSON: {e}", file=sys.stderr)
        sys.exit(1)
        
    if not isinstance(data, dict):
        print("ERROR: JSON is not an object", file=sys.stderr)
        sys.exit(1)
        
    if "generated_texts" in data:
        print("ERROR: generated_texts must not be present in public results", file=sys.stderr)
        sys.exit(1)
        
    req_rate = float(data.get("request_rate", -1))
    if abs(req_rate - args.request_rate) > 1e-5:
        print(f"ERROR: request_rate mismatch. Expected {args.request_rate}, got {req_rate}", file=sys.stderr)
        sys.exit(1)

    completed = data.get("completed", -1)
    if completed != args.expected_prompts:
        print(f"ERROR: completed count {completed} != expected {args.expected_prompts}", file=sys.stderr)
        sys.exit(1)

    sched_type = data.get("schedule_type", "")
    match = False
    arm = args.arm
    if arm == "fcfs" and sched_type == "fcfs": match = True
    elif arm == "ltr" and sched_type.startswith("opt-") and not sched_type.startswith("opt-aging-"): match = True
    elif arm == "v1" and sched_type.startswith("opt-aging-"): match = True
    elif arm == sched_type: match = True
    elif arm.startswith("opt-aging-") and sched_type.startswith("opt-aging-"): match = True
    elif arm.startswith("opt-") and not arm.startswith("opt-aging-") and sched_type.startswith("opt-") and not sched_type.startswith("opt-aging-"): match = True

    if not match:
        print(f"ERROR: schedule_type mismatch. ARM={arm}, json={sched_type}", file=sys.stderr)
        sys.exit(1)

    # array length checks
    ttfts = data.get("ttfts", [])
    itls = data.get("itls", [])
    if len(ttfts) != completed:
        print(f"ERROR: ttfts length {len(ttfts)} != completed {completed}", file=sys.stderr)
        sys.exit(1)
    if len(itls) != completed:
        print(f"ERROR: itls length {len(itls)} != completed {completed}", file=sys.stderr)
        sys.exit(1)

    # errors/failed requests check
    if data.get("errors", 0) > 0 or data.get("failed_requests", 0) > 0 or data.get("failed", 0) > 0:
        print("ERROR: Result contains errors or failed requests", file=sys.stderr)
        sys.exit(1)

    # optional seed check
    if "seed" in data:
        actual_seed = data["seed"]
        if actual_seed != args.expected_seed:
            print(f"ERROR: seed {actual_seed} != expected {args.expected_seed}", file=sys.stderr)
            sys.exit(1)
    # If seed not in data, we pass, but the caller handles writing proper manifest sidecar info

    # secret-like pattern scan
    if check_secrets_stream(result_file):
        print("ERROR: Secret-like string detected in result file", file=sys.stderr)
        sys.exit(1)

    print("VALIDATION SUCCESS")
    sys.exit(0)

if __name__ == "__main__":
    main()
