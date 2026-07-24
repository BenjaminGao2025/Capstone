import os
import json
import hashlib
import argparse
import re
from pathlib import Path

SECRET_PATTERNS = [
    re.compile(r"hooks\.slack"),
    re.compile(r"xox[baprs]-"),
    re.compile(r"ghp_"),
    re.compile(r"github_pat_"),
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"BEGIN PRIVATE KEY")
]

def hash_file(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def check_secrets(content):
    for pattern in SECRET_PATTERNS:
        if pattern.search(content):
            return True
    return False

def check_scheduler_match(manifest_arm, json_schedule_type):
    if manifest_arm == "fcfs" and json_schedule_type == "fcfs": return True
    if manifest_arm == "ltr" and json_schedule_type.startswith("opt-"): return True
    if manifest_arm == "v1" and json_schedule_type.startswith("opt-aging-"): return True
    if manifest_arm.startswith("opt-aging-") and json_schedule_type.startswith("opt-aging-"): return True
    if manifest_arm.startswith("opt-") and not manifest_arm.startswith("opt-aging-") and json_schedule_type.startswith("opt-") and not json_schedule_type.startswith("opt-aging-"): return True
    
    # Just generic fallback match
    if manifest_arm == json_schedule_type: return True
    
    return False

def audit_manifest(manifest_path, repo_root):
    with open(manifest_path, "r") as f:
        manifest = json.load(f)

    if "schema_version" not in manifest:
        return {"error": "Missing schema_version"}

    seen_ids = set()
    seen_shas = {}
    
    results = []
    has_blockers = False
    
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
            "audit_verdict": "PASS",
            "warnings": [],
            "errors": []
        }

        # 3. Verify experiment_id uniqueness
        if exp_id in seen_ids:
            audit_result["errors"].append("Duplicate experiment_id")
            has_blockers = True
        seen_ids.add(exp_id)

        # 4a. Verify result_path exists
        result_rel_path = exp.get("result_path")
        result_abs_path = os.path.join(repo_root, result_rel_path) if result_rel_path else None
        
        if not result_abs_path or not os.path.exists(result_abs_path):
            audit_result["errors"].append("Result file does not exist")
            audit_result["sha_status"] = "FAIL"
            has_blockers = True
            results.append(audit_result)
            continue
            
        # 4b. Compute SHA-256 of result file and compare
        actual_sha = hash_file(result_abs_path)
        expected_sha = exp.get("result_sha256")
        if actual_sha != expected_sha:
            audit_result["errors"].append("SHA-256 mismatch")
            audit_result["sha_status"] = "FAIL"
            has_blockers = True
            
        # 4c. Check for duplicate SHA-256 across experiments
        if actual_sha in seen_shas:
            audit_result["errors"].append(f"Duplicate result SHA-256 with {seen_shas[actual_sha]}")
            has_blockers = True
        seen_shas[actual_sha] = exp_id
        
        # Open result JSON
        with open(result_abs_path, "r") as f:
            content_start = f.read(10240) # first 10KB
            f.seek(0)
            try:
                res_data = json.load(f)
            except Exception as e:
                audit_result["errors"].append(f"Failed to parse result JSON: {e}")
                has_blockers = True
                results.append(audit_result)
                continue
                
        # 4d. Open result JSON and check
        res_sched = res_data.get("schedule_type")
        # Primary check: manifest scheduler_type vs JSON schedule_type
        manifest_sched = exp.get("scheduler_type")
        arm_matches = False
        if manifest_sched and res_sched:
            arm_matches = (manifest_sched == res_sched)
        if not arm_matches and res_sched:
            # Fallback: check arm name
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
            
        # 4e. Check if generated_texts exists
        if "generated_texts" in res_data:
            audit_result["warnings"].append("generated_texts found in results")
            
        # 4f. Search for secret-like patterns
        if check_secrets(content_start):
            audit_result["errors"].append("Secret-like string detection")
            has_blockers = True
            
        # 4g. Verify distribution_relation consistency
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
            
        # 4h. Verify crash/incomplete entries
        if exp.get("status") in ["crashed", "incomplete"] and exp.get("eligible_for_aggregation"):
            audit_result["errors"].append("Crash/incomplete entry incorrectly set as eligible_for_aggregation=true")
            has_blockers = True
            
        # 4i. Check latency array lengths
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
            "passed": sum(1 for r in results if r["audit_verdict"] == "PASS"),
            "failed": sum(1 for r in results if r["audit_verdict"] == "FAIL"),
        }
    }

def format_markdown(audit_results):
    lines = []
    lines.append("| experiment_id | phase | arm | rate | seed | predictor | train_dist | test_dist | relation | completed/expected | SHA status | eligible | audit_verdict | warnings |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    
    for r in audit_results["results"]:
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
    
    args = parser.parse_args()
    
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    manifest_path = os.path.abspath(args.manifest)
    
    audit_data = audit_manifest(manifest_path, repo_root)
    
    with open(args.json_output, "w") as f:
        json.dump(audit_data, f, indent=2)
        
    with open(args.markdown_output, "w") as f:
        f.write(format_markdown(audit_data))
        
    if audit_data.get("has_blockers") or "error" in audit_data:
        exit(1)
    else:
        exit(0)

if __name__ == "__main__":
    main()
