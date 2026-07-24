import os
import json
import tempfile
import unittest
import hashlib
import subprocess
import sys

from scripts.audit_submission_results import audit_manifest, hash_file

class TestSubmissionAudit(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_root = self.temp_dir.name
        
    def tearDown(self):
        self.temp_dir.cleanup()
        
    def create_result_file(self, content, filename):
        path = os.path.join(self.repo_root, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            if isinstance(content, str):
                f.write(content)
            else:
                json.dump(content, f)
        return path, hash_file(path)
        
    def create_manifest(self, experiments, filename="manifest.json"):
        path = os.path.join(self.repo_root, filename)
        manifest = {
            "schema_version": "1.0.0",
            "generated_at": "2026-07-24T00:00:00Z",
            "generator": "test",
            "experiments": experiments
        }
        with open(path, "w") as f:
            json.dump(manifest, f)
        return path

    def get_base_experiment(self):
        return {
            "experiment_id": "exp_1",
            "phase": "A",
            "claim_category": "in_distribution",
            "arm": "fcfs",
            "scheduler_type": "fcfs",
            "dataset_name": "test-dataset",
            "test_distribution": "lmsys",
            "predictor_name": "none",
            "predictor_training_distribution": "unknown",
            "predictor_config_path": None,
            "predictor_config_sha256": None,
            "predictor_provenance_quality": "unknown",
            "distribution_relation": "unknown",
            "request_rate": 4.0,
            "seed": 42,
            "expected_num_prompts": 500,
            "completed": 500,
            "status": "valid",
            "eligible_for_aggregation": True,
            "result_path": "results/exp_1.json",
            "result_sha256": "",
            "log_path": None,
            "source_script": None,
            "source_commit": None,
            "duplicate_of": None,
            "notes": None
        }

    def get_base_result(self):
        return {
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

    # a. Valid manifest with all checks passing
    def test_valid_manifest(self):
        exp = self.get_base_experiment()
        res = self.get_base_result()
        path, sha = self.create_result_file(res, "results/exp_1.json")
        exp["result_sha256"] = sha
        manifest_path = self.create_manifest([exp])
        
        audit = audit_manifest(manifest_path, self.repo_root)
        self.assertFalse(audit["has_blockers"])
        self.assertEqual(audit["results"][0]["audit_verdict"], "PASS")

    # b. Result file does not exist
    def test_missing_result_file(self):
        exp = self.get_base_experiment()
        exp["result_path"] = "results/missing.json"
        manifest_path = self.create_manifest([exp])
        
        audit = audit_manifest(manifest_path, self.repo_root)
        self.assertTrue(audit["has_blockers"])
        self.assertIn("Result file does not exist", audit["results"][0]["errors"])

    # c. SHA-256 mismatch
    def test_sha_mismatch(self):
        exp = self.get_base_experiment()
        res = self.get_base_result()
        path, sha = self.create_result_file(res, "results/exp_1.json")
        exp["result_sha256"] = "badsha"
        manifest_path = self.create_manifest([exp])
        
        audit = audit_manifest(manifest_path, self.repo_root)
        self.assertTrue(audit["has_blockers"])
        self.assertIn("SHA-256 mismatch", audit["results"][0]["errors"])

    # d. Duplicate result SHA-256
    def test_duplicate_sha(self):
        exp1 = self.get_base_experiment()
        exp2 = self.get_base_experiment()
        exp2["experiment_id"] = "exp_2"
        exp2["result_path"] = "results/exp_2.json"
        
        res = self.get_base_result()
        path1, sha1 = self.create_result_file(res, "results/exp_1.json")
        path2, sha2 = self.create_result_file(res, "results/exp_2.json")
        
        exp1["result_sha256"] = sha1
        exp2["result_sha256"] = sha2
        
        manifest_path = self.create_manifest([exp1, exp2])
        audit = audit_manifest(manifest_path, self.repo_root)
        self.assertTrue(audit["has_blockers"])
        
        found = False
        for err in audit["results"][1]["errors"]:
            if "Duplicate result SHA-256" in err:
                found = True
        self.assertTrue(found)

    # e. Completed < expected_num_prompts
    def test_completed_less_than_expected(self):
        exp = self.get_base_experiment()
        exp["completed"] = 499
        exp["expected_num_prompts"] = 500
        exp["eligible_for_aggregation"] = True
        
        res = self.get_base_result()
        res["completed"] = 499
        res["ttfts"] = [0.1] * 499
        res["itls"] = [[0.1]] * 499
        
        path, sha = self.create_result_file(res, "results/exp_1.json")
        exp["result_sha256"] = sha
        
        manifest_path = self.create_manifest([exp])
        audit = audit_manifest(manifest_path, self.repo_root)
        self.assertTrue(audit["has_blockers"])
        self.assertIn("Completed < expected_num_prompts while eligible_for_aggregation=true", audit["results"][0]["errors"])

    # f. Crash entry incorrectly set as eligible_for_aggregation=true
    def test_crash_eligible(self):
        exp = self.get_base_experiment()
        exp["status"] = "crashed"
        exp["eligible_for_aggregation"] = True
        
        res = self.get_base_result()
        path, sha = self.create_result_file(res, "results/exp_1.json")
        exp["result_sha256"] = sha
        
        manifest_path = self.create_manifest([exp])
        audit = audit_manifest(manifest_path, self.repo_root)
        self.assertTrue(audit["has_blockers"])
        self.assertIn("Crash/incomplete entry incorrectly set as eligible_for_aggregation=true", audit["results"][0]["errors"])

    # g. ShareGPT predictor + ShareGPT test marked as 'ood' (should fail)
    def test_train_test_same_ood(self):
        exp = self.get_base_experiment()
        exp["predictor_training_distribution"] = "sharegpt"
        exp["test_distribution"] = "sharegpt"
        exp["distribution_relation"] = "ood"
        
        res = self.get_base_result()
        path, sha = self.create_result_file(res, "results/exp_1.json")
        exp["result_sha256"] = sha
        
        manifest_path = self.create_manifest([exp])
        audit = audit_manifest(manifest_path, self.repo_root)
        self.assertTrue(audit["has_blockers"])
        
        errs = audit["results"][0]["errors"]
        found = any("train and test distribution are same" in e for e in errs)
        self.assertTrue(found)

    # h. Phase D entry incorrectly labeled as OOD
    def test_phase_d_ood(self):
        exp = self.get_base_experiment()
        exp["phase"] = "D"
        exp["predictor_training_distribution"] = "sharegpt"
        exp["test_distribution"] = "sharegpt"
        exp["distribution_relation"] = "ood"
        
        res = self.get_base_result()
        path, sha = self.create_result_file(res, "results/exp_1.json")
        exp["result_sha256"] = sha
        
        manifest_path = self.create_manifest([exp])
        audit = audit_manifest(manifest_path, self.repo_root)
        self.assertTrue(audit["has_blockers"])
        
        errs = audit["results"][0]["errors"]
        found = any("Phase D entry correctly ShareGPT-ShareGPT but incorrectly labeled as OOD" in e for e in errs)
        self.assertTrue(found)

    # i. generated_texts detection
    def test_generated_texts(self):
        exp = self.get_base_experiment()
        res = self.get_base_result()
        res["generated_texts"] = ["hello"]
        path, sha = self.create_result_file(res, "results/exp_1.json")
        exp["result_sha256"] = sha
        
        manifest_path = self.create_manifest([exp])
        audit = audit_manifest(manifest_path, self.repo_root)
        
        self.assertFalse(audit["has_blockers"])
        self.assertIn("generated_texts found in results", audit["results"][0]["warnings"])

    # j. Secret-like string detection
    def test_secret_detection(self):
        exp = self.get_base_experiment()
        res = self.get_base_result()
        res["some_field"] = "hooks.slack.com/services/T000/B000/XXX"
        path, sha = self.create_result_file(res, "results/exp_1.json")
        exp["result_sha256"] = sha
        
        manifest_path = self.create_manifest([exp])
        audit = audit_manifest(manifest_path, self.repo_root)
        self.assertTrue(audit["has_blockers"])
        self.assertIn("Secret-like string detection", audit["results"][0]["errors"])

    # k. Scheduler arm conflict
    def test_scheduler_arm_conflict(self):
        exp = self.get_base_experiment()
        exp["arm"] = "fcfs"
        res = self.get_base_result()
        res["schedule_type"] = "opt-test"
        path, sha = self.create_result_file(res, "results/exp_1.json")
        exp["result_sha256"] = sha
        
        manifest_path = self.create_manifest([exp])
        audit = audit_manifest(manifest_path, self.repo_root)
        self.assertTrue(audit["has_blockers"])
        self.assertIn("Scheduler arm conflict", audit["results"][0]["errors"])

    # l. Request rate conflict
    def test_request_rate_conflict(self):
        exp = self.get_base_experiment()
        exp["request_rate"] = 4.0
        res = self.get_base_result()
        res["request_rate"] = 5.0
        path, sha = self.create_result_file(res, "results/exp_1.json")
        exp["result_sha256"] = sha
        
        manifest_path = self.create_manifest([exp])
        audit = audit_manifest(manifest_path, self.repo_root)
        self.assertTrue(audit["has_blockers"])
        self.assertIn("Request rate conflict", audit["results"][0]["errors"])

    def test_cli(self):
        exp = self.get_base_experiment()
        res = self.get_base_result()
        path, sha = self.create_result_file(res, "results/exp_1.json")
        exp["result_sha256"] = sha
        # Using absolute path for result_path to bypass repo_root assumption
        exp["result_path"] = path
        manifest_path = self.create_manifest([exp], "manifest2.json")
        
        script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts", "audit_submission_results.py")
        json_out = os.path.join(self.temp_dir.name, "out.json")
        md_out = os.path.join(self.temp_dir.name, "out.md")
        
        cmd = [
            sys.executable,
            script_path,
            "--manifest", manifest_path,
            "--json-output", json_out,
            "--markdown-output", md_out
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(os.path.exists(json_out))
        self.assertTrue(os.path.exists(md_out))

if __name__ == '__main__':
    unittest.main()
