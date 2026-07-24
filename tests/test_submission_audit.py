import unittest
import os
import json
import tempfile
import subprocess
import shutil
from pathlib import Path
from scripts.audit_submission_results import audit_manifest, validate_path_safety

# Import the script to test functions directly
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts')))
import audit_submission_results

class TestSubmissionAudit(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.repo_root = self.temp_dir
        os.makedirs(os.path.join(self.repo_root, "results"))
        self.manifest_path = os.path.join(self.repo_root, "results", "submission_manifest.json")
        
        # Copy the actual schema file into the temp dir
        import shutil
        actual_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        actual_schema_path = os.path.join(actual_repo_root, "results", "submission_manifest.schema.json")
        shutil.copy(actual_schema_path, os.path.join(self.repo_root, "results", "submission_manifest.schema.json"))
        
        # Base valid result JSON
        self.valid_result = {
            "date": "20260709-000000",
            "model_id": "test-model",
            "schedule_type": "fcfs",
            "request_rate": 4.0,
            "completed": 500,
            "num_prompts": 500,
            "mean_ttft_ms": 100.0,
            "ttfts": [0.1] * 500,
            "itls": [[0.01]] * 500
        }
        
        # Base valid manifest structure
        self.valid_manifest = {
            "schema_version": "1.0.0",
            "generated_at": "2026-07-24T00:00:00Z",
            "generator": "test",
            "experiments": [
                self.create_valid_exp("exp1")
            ]
        }

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def create_valid_exp(self, exp_id="exp1"):
        return {
            "experiment_id": exp_id,
            "phase": "A",
            "claim_category": "in_distribution",
            "arm": "fcfs",
            "scheduler_type": "fcfs",
            "dataset_name": "lmsys",
            "test_distribution": "lmsys",
            "predictor_name": "lmsys_pred",
            "predictor_training_distribution": "lmsys",
            "predictor_config_path": "configs/pred.json",
            "predictor_config_sha256": "a" * 64,
            "predictor_provenance_quality": "full",
            "distribution_relation": "in_distribution",
            "request_rate": 4.0,
            "seed": 0,
            "expected_num_prompts": 500,
            "completed": 500,
            "status": "valid",
            "eligible_for_aggregation": True,
            "result_path": f"{exp_id}.json",
            "result_sha256": "", # filled later
            "log_path": None,
            "source_script": "run.sh",
            "source_commit": "abc",
            "duplicate_of": None,
            "notes": None
        }

    def write_json(self, path, data):
        with open(path, "w") as f:
            json.dump(data, f)
        return audit_submission_results.hash_file(path)

    def test_01_valid_manifest(self):
        # a. Valid manifest with all checks passing
        res_path = os.path.join(self.repo_root, "exp1.json")
        sha = self.write_json(res_path, self.valid_result)
        
        self.valid_manifest["experiments"][0]["result_sha256"] = sha
        self.write_json(self.manifest_path, self.valid_manifest)
        
        res = audit_submission_results.audit_manifest(self.manifest_path, self.repo_root)
        self.assertFalse(res["has_blockers"])
        self.assertEqual(res["results"][0]["audit_verdict"], "METADATA_VERIFIED")

    def test_02_missing_result_file(self):
        # b. Result file does not exist
        self.valid_manifest["experiments"][0]["result_sha256"] = "a" * 64
        self.write_json(self.manifest_path, self.valid_manifest)
        
        res = audit_submission_results.audit_manifest(self.manifest_path, self.repo_root)
        self.assertTrue(res["has_blockers"])
        self.assertEqual(res["results"][0]["audit_verdict"], "FAIL")
        self.assertIn("Result file does not exist", res["results"][0]["errors"])

    def test_03_sha256_mismatch(self):
        # c. SHA-256 mismatch
        res_path = os.path.join(self.repo_root, "exp1.json")
        self.write_json(res_path, self.valid_result)
        
        self.valid_manifest["experiments"][0]["result_sha256"] = "b" * 64
        self.write_json(self.manifest_path, self.valid_manifest)
        
        res = audit_submission_results.audit_manifest(self.manifest_path, self.repo_root)
        self.assertTrue(res["has_blockers"])
        self.assertIn("SHA-256 mismatch", res["results"][0]["errors"])

    def test_04_duplicate_sha256(self):
        # d. Duplicate result SHA-256
        res_path1 = os.path.join(self.repo_root, "exp1.json")
        sha = self.write_json(res_path1, self.valid_result)
        
        exp2 = self.create_valid_exp("exp2")
        exp2["result_sha256"] = sha
        self.valid_manifest["experiments"][0]["result_sha256"] = sha
        self.valid_manifest["experiments"].append(exp2)
        
        res_path2 = os.path.join(self.repo_root, "exp2.json")
        self.write_json(res_path2, self.valid_result)
        
        self.write_json(self.manifest_path, self.valid_manifest)
        
        res = audit_submission_results.audit_manifest(self.manifest_path, self.repo_root)
        self.assertTrue(res["has_blockers"])
        self.assertIn("Duplicate result SHA-256 with exp1", res["results"][1]["errors"])

    def test_05_completed_lt_expected(self):
        # e. Completed < expected_num_prompts
        res_path = os.path.join(self.repo_root, "exp1.json")
        res_data = self.valid_result.copy()
        res_data["completed"] = 400
        res_data["ttfts"] = [0.1] * 400
        res_data["itls"] = [[0.01]] * 400
        sha = self.write_json(res_path, res_data)
        
        self.valid_manifest["experiments"][0]["result_sha256"] = sha
        self.valid_manifest["experiments"][0]["completed"] = 400
        self.write_json(self.manifest_path, self.valid_manifest)
        
        res = audit_submission_results.audit_manifest(self.manifest_path, self.repo_root)
        self.assertTrue(res["has_blockers"])
        self.assertIn("Completed < expected_num_prompts while eligible_for_aggregation=true", res["results"][0]["errors"])

    def test_06_crash_eligible(self):
        # f. Crash entry incorrectly set as eligible_for_aggregation=true
        res_path = os.path.join(self.repo_root, "exp1.json")
        sha = self.write_json(res_path, self.valid_result)
        
        self.valid_manifest["experiments"][0]["result_sha256"] = sha
        self.valid_manifest["experiments"][0]["status"] = "crashed"
        self.write_json(self.manifest_path, self.valid_manifest)
        
        res = audit_submission_results.audit_manifest(self.manifest_path, self.repo_root)
        self.assertTrue(res["has_blockers"])
        self.assertIn("Crash/incomplete entry incorrectly set as eligible_for_aggregation=true", res["results"][0]["errors"])

    def test_07_sharegpt_ood(self):
        # g. ShareGPT predictor + ShareGPT test marked as 'ood'
        res_path = os.path.join(self.repo_root, "exp1.json")
        sha = self.write_json(res_path, self.valid_result)
        
        self.valid_manifest["experiments"][0]["result_sha256"] = sha
        self.valid_manifest["experiments"][0]["predictor_training_distribution"] = "sharegpt"
        self.valid_manifest["experiments"][0]["test_distribution"] = "sharegpt"
        self.valid_manifest["experiments"][0]["distribution_relation"] = "ood"
        self.write_json(self.manifest_path, self.valid_manifest)
        
        res = audit_submission_results.audit_manifest(self.manifest_path, self.repo_root)
        self.assertTrue(res["has_blockers"])
        self.assertIn("Marked 'ood' but train and test distribution are same", res["results"][0]["errors"])

    def test_08_phase_d_ood(self):
        # h. Phase D entry incorrectly labeled as OOD
        res_path = os.path.join(self.repo_root, "exp1.json")
        sha = self.write_json(res_path, self.valid_result)
        
        self.valid_manifest["experiments"][0]["result_sha256"] = sha
        self.valid_manifest["experiments"][0]["phase"] = "D"
        self.valid_manifest["experiments"][0]["predictor_training_distribution"] = "sharegpt"
        self.valid_manifest["experiments"][0]["test_distribution"] = "sharegpt"
        self.valid_manifest["experiments"][0]["distribution_relation"] = "ood"
        self.write_json(self.manifest_path, self.valid_manifest)
        
        res = audit_submission_results.audit_manifest(self.manifest_path, self.repo_root)
        self.assertTrue(res["has_blockers"])
        self.assertTrue(any("Phase D entry correctly ShareGPT-ShareGPT but incorrectly labeled as OOD" in e for e in res["results"][0]["errors"]))

    def test_09_generated_texts(self):
        # i. generated_texts detection
        res_path = os.path.join(self.repo_root, "exp1.json")
        res_data = self.valid_result.copy()
        res_data["generated_texts"] = ["text"]
        sha = self.write_json(res_path, res_data)
        
        self.valid_manifest["experiments"][0]["result_sha256"] = sha
        self.write_json(self.manifest_path, self.valid_manifest)
        
        res = audit_submission_results.audit_manifest(self.manifest_path, self.repo_root)
        self.assertTrue(res["has_blockers"])
        self.assertTrue(any("Sanitized derivative MUST NOT contain generated_texts" in e for e in res["results"][0]["errors"]))

    def test_10_secret_detection_stream(self):
        # j. Secret-like string detection > 10KB
        res_path = os.path.join(self.repo_root, "exp1.json")
        res_data = self.valid_result.copy()
        # Add 15KB of padding
        res_data["padding"] = "A" * 15000
        # Add secret
        res_data["secret"] = "https://hooks.slack.com/services/T000/B000/XXXX"
        sha = self.write_json(res_path, res_data)
        
        self.valid_manifest["experiments"][0]["result_sha256"] = sha
        self.write_json(self.manifest_path, self.valid_manifest)
        
        res = audit_submission_results.audit_manifest(self.manifest_path, self.repo_root)
        self.assertTrue(res["has_blockers"])
        self.assertIn("Secret-like string detection", res["results"][0]["errors"])

    def test_11_scheduler_conflict(self):
        # k. Scheduler arm conflict
        res_path = os.path.join(self.repo_root, "exp1.json")
        res_data = self.valid_result.copy()
        res_data["schedule_type"] = "opt-aging-10"
        sha = self.write_json(res_path, res_data)
        
        self.valid_manifest["experiments"][0]["result_sha256"] = sha
        self.valid_manifest["experiments"][0]["arm"] = "fcfs"
        self.valid_manifest["experiments"][0]["scheduler_type"] = "fcfs"
        self.write_json(self.manifest_path, self.valid_manifest)
        
        res = audit_submission_results.audit_manifest(self.manifest_path, self.repo_root)
        self.assertTrue(res["has_blockers"])
        self.assertIn("Scheduler arm conflict", res["results"][0]["errors"])

    def test_12_request_rate_conflict(self):
        # l. Request rate conflict
        res_path = os.path.join(self.repo_root, "exp1.json")
        res_data = self.valid_result.copy()
        res_data["request_rate"] = 8.0
        sha = self.write_json(res_path, res_data)
        
        self.valid_manifest["experiments"][0]["result_sha256"] = sha
        self.valid_manifest["experiments"][0]["request_rate"] = 4.0
        self.write_json(self.manifest_path, self.valid_manifest)
        
        res = audit_submission_results.audit_manifest(self.manifest_path, self.repo_root)
        self.assertTrue(res["has_blockers"])
        self.assertIn("Request rate conflict", res["results"][0]["errors"])
        
    def test_13_path_traversal(self):
        # Path traversal check
        self.valid_manifest["experiments"][0]["result_path"] = "../test.json"
        self.write_json(self.manifest_path, self.valid_manifest)
        
        res = audit_submission_results.audit_manifest(self.manifest_path, self.repo_root)
        self.assertTrue(res["has_blockers"])
        self.assertTrue(any("Invalid/unsafe path for result_path" in e for e in res["results"][0]["errors"]))

    def test_14_absolute_path(self):
        # Absolute path check
        self.valid_manifest["experiments"][0]["result_path"] = "/etc/passwd"
        self.write_json(self.manifest_path, self.valid_manifest)
        
        res = audit_submission_results.audit_manifest(self.manifest_path, self.repo_root)
        self.assertTrue(res["has_blockers"])
        self.assertTrue(any("Invalid/unsafe path for result_path" in e for e in res["results"][0]["errors"]))

    def _setup_sanitizer_test(self):
        orig_path = os.path.join(self.repo_root, "exp1_orig.json")
        san_path = os.path.join(self.repo_root, "exp1.json")
        orig_data = self.valid_result.copy()
        orig_data["generated_texts"] = ["text1", "text2"]
        san_data = self.valid_result.copy()
        
        orig_sha = self.write_json(orig_path, orig_data)
        san_sha = self.write_json(san_path, san_data)
        
        self.valid_manifest["experiments"][0]["original_result_path"] = "exp1_orig.json"
        self.valid_manifest["experiments"][0]["original_result_sha256"] = orig_sha
        self.valid_manifest["experiments"][0]["sanitizer_version"] = "1.0.0"
        self.valid_manifest["experiments"][0]["result_sha256"] = san_sha
        
        return orig_path, san_path, orig_data, san_data

    def test_15_sanitizer_valid(self):
        self._setup_sanitizer_test()
        self.write_json(self.manifest_path, self.valid_manifest)
        res = audit_submission_results.audit_manifest(self.manifest_path, self.repo_root)
        self.assertFalse(res["has_blockers"])

    def test_16_sanitizer_orig_missing(self):
        orig_path, san_path, orig_data, san_data = self._setup_sanitizer_test()
        os.remove(orig_path)
        self.write_json(self.manifest_path, self.valid_manifest)
        res = audit_submission_results.audit_manifest(self.manifest_path, self.repo_root)
        self.assertTrue(res["has_blockers"])
        self.assertTrue(any("Original file does not exist" in e for e in res["results"][0]["errors"]))

    def test_17_sanitizer_orig_sha_mismatch(self):
        orig_path, san_path, orig_data, san_data = self._setup_sanitizer_test()
        self.valid_manifest["experiments"][0]["original_result_sha256"] = "c" * 64
        self.write_json(self.manifest_path, self.valid_manifest)
        res = audit_submission_results.audit_manifest(self.manifest_path, self.repo_root)
        self.assertTrue(res["has_blockers"])
        self.assertTrue(any("Original SHA-256 mismatch" in e for e in res["results"][0]["errors"]))

    def test_18_sanitizer_numeric_mod(self):
        orig_path, san_path, orig_data, san_data = self._setup_sanitizer_test()
        san_data["mean_ttft_ms"] = 999.0
        self.valid_manifest["experiments"][0]["result_sha256"] = self.write_json(san_path, san_data)
        self.write_json(self.manifest_path, self.valid_manifest)
        res = audit_submission_results.audit_manifest(self.manifest_path, self.repo_root)
        self.assertTrue(res["has_blockers"])
        self.assertTrue(any("Sanitized file does not match original file" in e for e in res["results"][0]["errors"]))

    def test_19_sanitizer_extra_deletion(self):
        orig_path, san_path, orig_data, san_data = self._setup_sanitizer_test()
        del san_data["completed"]
        self.valid_manifest["experiments"][0]["result_sha256"] = self.write_json(san_path, san_data)
        self.write_json(self.manifest_path, self.valid_manifest)
        res = audit_submission_results.audit_manifest(self.manifest_path, self.repo_root)
        self.assertTrue(res["has_blockers"])
        self.assertTrue(any("Sanitized file does not match original file" in e for e in res["results"][0]["errors"]))

    def test_20_sanitizer_array_mod(self):
        orig_path, san_path, orig_data, san_data = self._setup_sanitizer_test()
        san_data["ttfts"][0] = 99.9
        self.valid_manifest["experiments"][0]["result_sha256"] = self.write_json(san_path, san_data)
        self.write_json(self.manifest_path, self.valid_manifest)
        res = audit_submission_results.audit_manifest(self.manifest_path, self.repo_root)
        self.assertTrue(res["has_blockers"])
        self.assertTrue(any("Sanitized file does not match original file" in e for e in res["results"][0]["errors"]))

    def test_21_sanitizer_unsafe_orig_path(self):
        self._setup_sanitizer_test()
        self.valid_manifest["experiments"][0]["original_result_path"] = "../foo.json"
        self.write_json(self.manifest_path, self.valid_manifest)
        res = audit_submission_results.audit_manifest(self.manifest_path, self.repo_root)
        self.assertTrue(res["has_blockers"])
        self.assertTrue(any("Invalid/unsafe path for original_result_path" in e for e in res["results"][0]["errors"]))

    def test_22_validate_path_safety_extensions(self):
        self.assertFalse(validate_path_safety("C:\\Windows\\file", self.repo_root))
        self.assertFalse(validate_path_safety("C:/Windows/file", self.repo_root))
        self.assertFalse(validate_path_safety("\\\\server\\share", self.repo_root))
        self.assertFalse(validate_path_safety("//server/share", self.repo_root))
        self.assertFalse(validate_path_safety("/etc/passwd", self.repo_root))
        self.assertFalse(validate_path_safety("folder\\..\\outside.json", self.repo_root))
        self.assertFalse(validate_path_safety("..\\outside.json", self.repo_root))

    def test_cli(self):
        res_path = os.path.join(self.repo_root, "exp1.json")
        sha = self.write_json(res_path, self.valid_result)
        
        self.valid_manifest["experiments"][0]["result_sha256"] = sha
        self.write_json(self.manifest_path, self.valid_manifest)
        
        json_out = os.path.join(self.temp_dir, "out.json")
        md_out = os.path.join(self.temp_dir, "out.md")
        
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts', 'audit_submission_results.py'))
        
        result = subprocess.run([
            "python3", script_path,
            "--manifest", self.manifest_path,
            "--json-output", json_out,
            "--markdown-output", md_out,
            "--repo-root", self.repo_root
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(os.path.exists(json_out))
        self.assertTrue(os.path.exists(md_out))

if __name__ == '__main__':
    unittest.main()
