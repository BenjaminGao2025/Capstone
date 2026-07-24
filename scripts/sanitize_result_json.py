#!/usr/bin/env python3
import json
import argparse
import hashlib
import sys
import copy

SANITIZER_VERSION = "v1.0.0"

def hash_file(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def main():
    parser = argparse.ArgumentParser(description="Deterministic result JSON sanitizer")
    parser.add_argument("--input", required=True, help="Original JSON file")
    parser.add_argument("--output", required=True, help="Sanitized JSON file output path")
    args = parser.parse_args()

    # Read original
    try:
        with open(args.input, "r") as f:
            original = json.load(f)
    except Exception as e:
        print(f"Error reading input: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(original, dict):
        print("Input is not a JSON object", file=sys.stderr)
        sys.exit(1)

    if "generated_texts" not in original:
        print("generated_texts not found in input; nothing to sanitize", file=sys.stderr)
        sys.exit(1)

    # Sanitize
    sanitized_data = copy.deepcopy(original)
    del sanitized_data["generated_texts"]

    # Write output deterministically
    try:
        with open(args.output, "w") as f:
            json.dump(sanitized_data, f, indent=2, sort_keys=True)
    except Exception as e:
        print(f"Error writing output: {e}", file=sys.stderr)
        sys.exit(1)

    # Re-read and verify
    with open(args.input, "r") as f:
        re_original = json.load(f)
    with open(args.output, "r") as f:
        re_sanitized = json.load(f)

    del re_original["generated_texts"]
    if re_original != re_sanitized:
        print("Verification failed: other fields were modified during sanitization", file=sys.stderr)
        sys.exit(1)
        
    orig_sha = hash_file(args.input)
    san_sha = hash_file(args.output)
    
    print(json.dumps({
        "sanitizer_version": SANITIZER_VERSION,
        "original_sha256": orig_sha,
        "sanitized_sha256": san_sha
    }))
    
if __name__ == "__main__":
    main()
