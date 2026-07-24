import os
import json
import hashlib
import argparse
import re
import pathlib

SECRET_PATTERNS = [
    re.compile(r"hooks\.slack"),
    re.compile(r"xox[baprs]-"),
    re.compile(r"ghp_"),
    re.compile(r"github_pat_"),
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"BEGIN PRIVATE KEY")
]

# Standard library schema validation
def validate_schema(manifest, repo_root):
    errors = []
    if not isinstance(manifest, dict):
        return ["Manifest is not a JSON object"]

    schema_path = os.path.join(repo_root, "results", "submission_manifest.schema.json")
    try:
        with open(schema_path, "r") as f:
            schema = json.load(f)
    except Exception as e:
        return [f"Failed to load schema file: {e}"]

    # Validate top level
    required_top = schema.get("required", [])
    for req in required_top:
        if req not in manifest:
            errors.append(f"Missing top-level required field: {req}")

    if schema.get("additionalProperties") is False:
        for k in manifest.keys():
            if k not in schema.get("properties", {}):
                errors.append(f"Top-level has unauthorized additional property: {k}")

    if "experiments" in manifest and not isinstance(manifest["experiments"], list):
        errors.append("Field 'experiments' must be a list")
        return errors

    exp_schema = schema.get("properties", {}).get("experiments", {}).get("items", {})
    required_exp = exp_schema.get("required", [])
    exp_props = exp_schema.get("properties", {})
    
    for i, exp in enumerate(manifest.get("experiments", [])):
        if not isinstance(exp, dict):
            errors.append(f"Experiment {i} is not an object")
            continue
            
        for req in required_exp:
            if req not in exp:
                errors.append(f"Experiment {i} missing required field: {req}")
                
        if exp_schema.get("additionalProperties") is False:
            for k in exp.keys():
                if k not in exp_props:
                    errors.append(f"Experiment {i} has unauthorized additional property: {k}")
                
        if not exp.get("experiment_id"):
            errors.append(f"Experiment {i} has empty experiment_id")
            
        for k, v in exp.items():
            if k not in exp_props:
                continue
            prop_def = exp_props[k]
            
            # Enums
            if "enum" in prop_def and v not in prop_def["enum"]:
                errors.append(f"Experiment {i} field '{k}' value '{v}' not in allowed enums")
                
            # Basic type checks
            t = prop_def.get("type")
            if t:
                types = [t] if isinstance(t, str) else t
                valid_type = False
                for t_str in types:
                    if t_str == "string" and isinstance(v, str): valid_type = True
                    elif t_str == "number" and isinstance(v, (int, float)): valid_type = True
                    elif t_str == "integer" and isinstance(v, int) and not isinstance(v, bool): valid_type = True
                    elif t_str == "boolean" and isinstance(v, bool): valid_type = True
                    elif t_str == "null" and v is None: valid_type = True
                
                if not valid_type:
                    errors.append(f"Experiment {i} field '{k}' has wrong type (expected {types})")
            
            # Pattern matching
            pattern = prop_def.get("pattern")
            if pattern and isinstance(v, str):
                if not re.match(pattern, v):
                    errors.append(f"Experiment {i} field '{k}' does not match pattern {pattern}")
                    
    return errors

def validate_path_safety(path_str, repo_root):
    if not path_str:
        return True
    
    # Reject backslashes (Windows-style or escaping abuse)
    if '\\' in path_str:
        return False
        
    # Reject absolute POSIX paths
    if path_str.startswith('/'):
        return False
        
    # Reject Windows drive letters and UNC paths
    if re.match(r'^[a-zA-Z]:', path_str):
        return False
        
    # Reject obvious traversal parts
    parts = path_str.split('/')
    if '..' in parts or '.' in parts:
        return False

    try:
        p = pathlib.Path(repo_root) / path_str
        return p.resolve().is_relative_to(pathlib.Path(repo_root).resolve())
    except Exception:
        return False

def hash_file(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def check_secrets_in_data(data):
    # Serialize data without generated_texts to scan for secrets
    data_copy = {k: v for k, v in data.items() if k != "generated_texts"}
    s = json.dumps(data_copy)
    for pattern in SECRET_PATTERNS:
        if pattern.search(s):
            return True
    return False

def check_scheduler_match(manifest_arm, json_schedule_type):
    if manifest_arm == "fcfs" and json_schedule_type == "fcfs": return True
    if manifest_arm == "ltr" and json_schedule_type.startswith("opt-") and not json_schedule_type.startswith("opt-aging-"): return True
    if manifest_arm == "v1" and json_schedule_type.startswith("opt-aging-"): return True
    if manifest_arm.startswith("opt-aging-") and json_schedule_type.startswith("opt-aging-"): return True
    if manifest_arm.startswith("opt-") and not manifest_arm.startswith("opt-aging-") and json_schedule_type.startswith("opt-") and not json_schedule_type.startswith("opt-aging-"): return True
    if manifest_arm == json_schedule_type: return True
    return False

def audit_manifest(manifest_path, repo_root):
    with open(manifest_path, "r") as f:
        manifest = json.load(f)

    results = []
    has_blockers = False
    
    schema_errors = validate_schema(manifest, repo_root)
    if schema_errors:
        return {"error": "Schema validation failed:\n" + "\n".join(schema_errors), "has_blockers": True, "results": []}

    seen_ids = set()
    seen_shas = {}
    
    for exp in manifest.get("experiments", []):
        exp_id = exp.get("experiment_id")
        audit_result = {
            "experiment_id": exp_id,
            "phase": exp.get("phase"),
            "arm": exp.get("arm"),
            "request_rate": exp.get("request_rate"),
            "seed": exp.get("seed"),
            "predictor_name": exp.get("predictor_name"),
            "predictor_training_distribution": exp.get("predictor_training_distribution"),
            "test_distribution": exp.get("test_distribution"),
            "distribution_relation": exp.get("distribution_relation"),
            "completed": exp.get("completed"),
            "expected_num_prompts": exp.get("expected_num_prompts"),
            "eligible_for_aggregation": exp.get("eligible_for_aggregation"),
            "sha_status": "PASS",
            "audit_verdict": "METADATA_VERIFIED", # Base successful verdict
            "warnings": [],
            "errors": []
        }

        # Verify experiment_id uniqueness
        if exp_id in seen_ids:
            audit_result["errors"].append("Duplicate experiment_id")
            has_blockers = True
        seen_ids.add(exp_id)

        # Path safety validation
        paths_to_check = ["result_path", "log_path", "source_script", "predictor_config_path"]
        for p in paths_to_check:
            if not validate_path_safety(exp.get(p), repo_root):
                audit_result["errors"].append(f"Invalid/unsafe path for {p}: {exp.get(p)}")
                has_blockers = True

        result_rel_path = exp.get("result_path")
        result_abs_path = os.path.join(repo_root, result_rel_path) if result_rel_path else None
        
        if not result_abs_path or not os.path.exists(result_abs_path):
            audit_result["errors"].append("Result file does not exist")
            audit_result["sha_status"] = "FAIL"
            audit_result["audit_verdict"] = "FAIL"
            has_blockers = True
            results.append(audit_result)
            continue
            
        # Compute SHA-256 of result file and compare
        actual_sha = hash_file(result_abs_path)
        expected_sha = exp.get("result_sha256")
        if actual_sha != expected_sha:
            audit_result["errors"].append("SHA-256 mismatch")
            audit_result["sha_status"] = "FAIL"
            has_blockers = True
            
        # Check for duplicate SHA-256 across experiments
        if actual_sha in seen_shas:
            audit_result["errors"].append(f"Duplicate result SHA-256 with {seen_shas[actual_sha]}")
            has_blockers = True
        seen_shas[actual_sha] = exp_id
        
        # Open result JSON
        try:
            with open(result_abs_path, "r") as f:
                res_data = json.load(f)
        except Exception as e:
            audit_result["errors"].append(f"Failed to parse result JSON: {e}")
            audit_result["audit_verdict"] = "FAIL"
            has_blockers = True
            results.append(audit_result)
            continue
                
        # JSON validation checks
        res_sched = res_data.get("schedule_type")
        manifest_sched = exp.get("scheduler_type")
        arm_matches = False
        if manifest_sched and res_sched:
            arm_matches = (manifest_sched == res_sched)
        if not arm_matches and res_sched:
            arm_matches = check_scheduler_match(exp.get("arm"), res_sched)
        if res_sched and not arm_matches:
             audit_result["errors"].append("Scheduler arm conflict")
             has_blockers = True
             
        if "request_rate" in res_data and abs(res_data["request_rate"] - exp.get("request_rate", -1)) > 1e-5:
            audit_result["errors"].append("Request rate conflict")
            has_blockers = True
            
        if "completed" in res_data and res_data["completed"] != exp.get("completed"):
            audit_result["errors"].append("Completed count conflict")
            has_blockers = True
            
        if exp.get("eligible_for_aggregation") and exp.get("completed") != exp.get("expected_num_prompts"):
            audit_result["errors"].append("Completed < expected_num_prompts while eligible_for_aggregation=true")
            has_blockers = True
            
        # Generated Texts Check
        if "generated_texts" in res_data:
            audit_result["errors"].append("Sanitized derivative MUST NOT contain generated_texts")
            has_blockers = True

        # Sanitizer Verification
        orig_path_rel = exp.get("original_result_path")
        orig_sha_manifest = exp.get("original_result_sha256")
        san_ver = exp.get("sanitizer_version")
        
        if orig_path_rel or orig_sha_manifest or san_ver:
            if not (orig_path_rel and orig_sha_manifest and san_ver):
                audit_result["errors"].append("If one sanitizer field is provided, all three must be provided")
                has_blockers = True
            else:
                if san_ver != "1.0.0":
                    audit_result["errors"].append(f"Unsupported sanitizer_version: {san_ver}")
                    has_blockers = True
                if not validate_path_safety(orig_path_rel, repo_root):
                    audit_result["errors"].append(f"Invalid/unsafe path for original_result_path: {orig_path_rel}")
                    has_blockers = True
                
                orig_abs_path = os.path.join(repo_root, orig_path_rel)
                if not os.path.exists(orig_abs_path):
                    audit_result["errors"].append(f"Original file does not exist: {orig_path_rel}")
                    has_blockers = True
                else:
                    actual_orig_sha = hash_file(orig_abs_path)
                    if actual_orig_sha != orig_sha_manifest:
                        audit_result["errors"].append(f"Original SHA-256 mismatch: expected {orig_sha_manifest}, got {actual_orig_sha}")
                        has_blockers = True
                    
                    try:
                        with open(orig_abs_path, "r") as f:
                            orig_data = json.load(f)
                        
                        if "generated_texts" not in orig_data:
                            audit_result["warnings"].append("Original file did not contain generated_texts, sanitization was unnecessary")
                        else:
                            del orig_data["generated_texts"]
                            if orig_data != res_data:
                                audit_result["errors"].append("Sanitized file does not match original file without generated_texts")
                                has_blockers = True
                    except Exception as e:
                        audit_result["errors"].append(f"Failed to parse original result JSON: {e}")
                        has_blockers = True
            
        # Secret Search on non-generated_texts
        if check_secrets_in_data(res_data):
            audit_result["errors"].append("Secret-like string detection")
            has_blockers = True
            
        # Verify distribution_relation consistency
        train_dist = exp.get("predictor_training_distribution")
        test_dist = exp.get("test_distribution")
        rel = exp.get("distribution_relation")
        phase = exp.get("phase")
        
        if train_dist and train_dist != "unknown" and test_dist and test_dist != "unknown":
            if train_dist == test_dist and rel == "ood":
                audit_result["errors"].append("Marked 'ood' but train and test distribution are same")
                has_blockers = True
                
        if phase == "D" and train_dist == "sharegpt" and test_dist == "sharegpt" and rel == "ood":
            audit_result["errors"].append("Phase D entry correctly ShareGPT-ShareGPT but incorrectly labeled as OOD")
            has_blockers = True
            
        # Verify crash/incomplete entries
        if exp.get("status") in ["crashed", "incomplete"] and exp.get("eligible_for_aggregation"):
            audit_result["errors"].append("Crash/incomplete entry incorrectly set as eligible_for_aggregation=true")
            has_blockers = True
            
        # Check latency array lengths
        ttfts = res_data.get("ttfts", [])
        itls = res_data.get("itls", [])
        expected_len = res_data.get("num_prompts", res_data.get("completed", -1))
        is_eligible = exp.get("eligible_for_aggregation", False)
        if len(ttfts) != expected_len:
            if is_eligible:
                audit_result["errors"].append("ttfts array length mismatch")
                has_blockers = True
            else:
                audit_result["warnings"].append("ttfts array length mismatch (non-eligible)")
        if len(itls) != expected_len:
            if is_eligible:
                audit_result["errors"].append("itls array length mismatch")
                has_blockers = True
            else:
                audit_result["warnings"].append("itls array length mismatch (non-eligible)")

        if len(audit_result["errors"]) > 0:
            audit_result["audit_verdict"] = "FAIL"
            
        results.append(audit_result)
        
    return {
        "results": results,
        "has_blockers": has_blockers,
        "summary": {
            "total": len(manifest.get("experiments", [])),
            "passed": sum(1 for r in results if r["audit_verdict"] != "FAIL"),
            "failed": sum(1 for r in results if r["audit_verdict"] == "FAIL"),
        }
    }

def format_markdown(audit_results):
    lines = []
    lines.append("| experiment_id | phase | arm | rate | seed | predictor | train_dist | test_dist | relation | completed/expected | SHA status | eligible | audit_verdict | warnings |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    
    for r in audit_results.get("results", []):
        exp_id = r.get("experiment_id", "")
        phase = r.get("phase", "")
        arm = r.get("arm", "")
        rate = r.get("request_rate", "")
        seed = r.get("seed", "")
        predictor = r.get("predictor_name", "")
        train_dist = r.get("predictor_training_distribution", "")
        test_dist = r.get("test_distribution", "")
        relation = r.get("distribution_relation", "")
        comp_exp = f"{r.get('completed', '')}/{r.get('expected_num_prompts', '')}"
        sha_stat = r.get("sha_status", "")
        eligible = r.get("eligible_for_aggregation", "")
        verdict = r.get("audit_verdict", "")
        warns = ", ".join(r.get("warnings", []) + r.get("errors", []))
        
        lines.append(f"| {exp_id} | {phase} | {arm} | {rate} | {seed} | {predictor} | {train_dist} | {test_dist} | {relation} | {comp_exp} | {sha_stat} | {eligible} | {verdict} | {warns} |")
        
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Audit submission results")
    parser.add_argument("--manifest", required=True, help="Path to submission manifest JSON")
    parser.add_argument("--json-output", required=True, help="Path to output JSON")
    parser.add_argument("--markdown-output", required=True, help="Path to output Markdown")
    parser.add_argument("--repo-root", help="Override repository root path (for testing)")
    
    args = parser.parse_args()
    
    if args.repo_root:
        repo_root = os.path.abspath(args.repo_root)
    else:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
    manifest_path = os.path.abspath(args.manifest)
    
    audit_data = audit_manifest(manifest_path, repo_root)
    
    if "error" in audit_data:
        print(f"FATAL ERROR: {audit_data['error']}")
        # Still write minimal JSON if requested
        with open(args.json_output, "w") as f:
            json.dump(audit_data, f, indent=2)
        exit(1)
    
    with open(args.json_output, "w") as f:
        json.dump(audit_data, f, indent=2)
        
    with open(args.markdown_output, "w") as f:
        f.write(format_markdown(audit_data))
        
    if audit_data.get("has_blockers"):
        exit(1)
    else:
        exit(0)

if __name__ == "__main__":
    main()
