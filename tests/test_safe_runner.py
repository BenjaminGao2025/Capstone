import unittest
import os
import subprocess
import tempfile
import shutil
import json

class TestSafeRunner(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.runner_script = os.path.join(self.repo_root, "scripts", "run_one_experiment_safe.sh")
        
        # We will mock the underlying runner scripts using RUNNER_SCRIPT
        self.mock_runner = os.path.join(self.temp_dir, "mock_runner.sh")
        with open(self.mock_runner, "w") as f:
            f.write("#!/bin/bash\nexit 0\n")
        self.env = {
            "PHASE": "test_phase",
            "ARM": "fcfs",
            "REQUEST_RATE": "4.0",
            "SEED": "0",
            "NUM_PROMPTS": "500",
            "RESULT_ROOT": self.temp_dir,
            "RUNNER_SCRIPT": self.mock_runner,
            "PATH": os.environ.get("PATH", "")
        }

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def write_mock_runner(self, content):
        with open(self.mock_runner, "w") as f:
            f.write(content)

    def run_safe_runner(self):
        return subprocess.run(
            ["bash", self.runner_script],
            env=self.env,
            capture_output=True,
            text=True,
            cwd=self.repo_root
        )

    def test_01_missing_env(self):
        del self.env["PHASE"]
        res = self.run_safe_runner()
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("PHASE environment variable is required", res.stderr)

    def test_02_invalid_inputs(self):
        self.env["PHASE"] = "../traversal"
        res = self.run_safe_runner()
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Invalid characters or values", res.stderr)
        out_dir = os.path.join(self.temp_dir, "../traversal", "rate4.0", "seed0", "fcfs")
        self.assertFalse(os.path.exists(out_dir))

        self.env["PHASE"] = "test"
        self.env["REQUEST_RATE"] = "-4"
        res = self.run_safe_runner()
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Invalid characters or values", res.stderr)
        
        self.env["REQUEST_RATE"] = "0"
        res = self.run_safe_runner()
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("REQUEST_RATE must be > 0", res.stderr)

    def test_03_nonempty_directory(self):
        out_dir = os.path.join(self.temp_dir, "test_phase", "rate4.0", "seed0", "fcfs")
        os.makedirs(out_dir)
        with open(os.path.join(out_dir, "file.txt"), "w") as f: f.write("a")
        
        res = self.run_safe_runner()
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("already exists and is not empty", res.stderr)

    def test_04_runner_failure(self):
        self.write_mock_runner("#!/bin/bash\nexit 1\n")
        res = self.run_safe_runner()
        self.assertNotEqual(res.returncode, 0)
        
        out_dir = os.path.join(self.temp_dir, "test_phase", "rate4.0", "seed0", "fcfs")
        self.assertTrue(os.path.exists(os.path.join(out_dir, "crash_manifest.json")))
        with open(os.path.join(out_dir, "crash_manifest.json")) as f:
            manifest = json.load(f)
            self.assertEqual(manifest["status"], "crashed")
            self.assertFalse(manifest["eligible_for_aggregation"])

    def test_05_no_json(self):
        self.write_mock_runner("#!/bin/bash\necho 'done'\n")
        res = self.run_safe_runner()
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("No new JSON results found", res.stderr)

    def test_06_malformed_json(self):
        self.write_mock_runner("#!/bin/bash\necho '{' > \"$RESULT_DIR/res.json\"\n")
        res = self.run_safe_runner()
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("Validation failed", res.stderr)

    def test_07_incomplete_completed(self):
        self.write_mock_runner(
            "#!/bin/bash\n"
            "python3 -c \"import json, os; open(os.path.join(os.environ['RESULT_DIR'], 'res.json'), 'w').write(json.dumps({'request_rate': 4.0, 'completed': 400, 'schedule_type': 'fcfs', 'seed': 0, 'ttfts': [0]*400, 'itls': [0]*400}))\"\n"
        )
        res = self.run_safe_runner()
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("completed count 400 != expected 500", res.stderr)

    def test_08_missing_predictor(self):
        self.write_mock_runner("#!/bin/bash\nexit 0\n")
        self.env["ARM"] = "ltr"
        out_dir = os.path.join(self.temp_dir, "test_phase", "rate4.0", "seed0", "ltr")
        res = self.run_safe_runner()
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("PREDICTOR environment variable is required", res.stderr)

    def test_09_successful_fcfs_with_seed(self):
        self.write_mock_runner(
            "#!/bin/bash\n"
            "python3 -c \"import json, os; open(os.path.join(os.environ['RESULT_DIR'], 'res.json'), 'w').write(json.dumps({'request_rate': 4.0, 'completed': 500, 'schedule_type': 'fcfs', 'seed': 0, 'ttfts': [0]*500, 'itls': [0]*500}))\"\n"
        )
        res = self.run_safe_runner()
        self.assertEqual(res.returncode, 0, msg=f"STDOUT: {res.stdout}\nSTDERR: {res.stderr}")
        
        out_dir = os.path.join(self.temp_dir, "test_phase", "rate4.0", "seed0", "fcfs")
        self.assertTrue(os.path.exists(os.path.join(out_dir, "experiment_manifest.json")))
        with open(os.path.join(out_dir, "experiment_manifest.json")) as f:
            manifest = json.load(f)
            self.assertTrue(manifest["eligible_for_public_submission"])
            self.assertEqual(manifest["status"], "success")
            self.assertEqual(manifest["seed_verification"], "verified_from_result")

    def test_10_successful_fcfs_missing_seed(self):
        self.write_mock_runner(
            "#!/bin/bash\n"
            "python3 -c \"import json, os; open(os.path.join(os.environ['RESULT_DIR'], 'res.json'), 'w').write(json.dumps({'request_rate': 4.0, 'completed': 500, 'schedule_type': 'fcfs', 'ttfts': [0]*500, 'itls': [0]*500}))\"\n"
        )
        res = self.run_safe_runner()
        self.assertEqual(res.returncode, 0, msg=f"STDOUT: {res.stdout}\nSTDERR: {res.stderr}")
        
        out_dir = os.path.join(self.temp_dir, "test_phase", "rate4.0", "seed0", "fcfs")
        self.assertTrue(os.path.exists(os.path.join(out_dir, "experiment_manifest.json")))
        with open(os.path.join(out_dir, "experiment_manifest.json")) as f:
            manifest = json.load(f)
            self.assertTrue(manifest["eligible_for_public_submission"])
            self.assertEqual(manifest["status"], "success")
            self.assertEqual(manifest["seed_verification"], "requested_only_not_embedded_in_result")

    def test_11_successful_ltr(self):
        self.env["ARM"] = "ltr"
        pred_path = os.path.join(self.temp_dir, "pred.json")
        with open(pred_path, "w") as f: f.write("{}")
        self.env["PREDICTOR"] = pred_path
        
        self.write_mock_runner(
            "#!/bin/bash\n"
            "python3 -c \"import json, os; open(os.path.join(os.environ['RESULT_DIR'], 'res.json'), 'w').write(json.dumps({'request_rate': 4.0, 'completed': 500, 'schedule_type': 'opt-test', 'seed': 0, 'ttfts': [0]*500, 'itls': [0]*500}))\"\n"
        )
        res = self.run_safe_runner()
        self.assertEqual(res.returncode, 0, msg=f"STDOUT: {res.stdout}\nSTDERR: {res.stderr}")

    def test_12_raw_generated_texts_sanitization(self):
        self.write_mock_runner(
            "#!/bin/bash\n"
            "python3 -c \"import json, os; open(os.path.join(os.environ['RESULT_DIR'], 'res.json'), 'w').write(json.dumps({'request_rate': 4.0, 'completed': 500, 'schedule_type': 'fcfs', 'seed': 0, 'ttfts': [0]*500, 'itls': [0]*500, 'generated_texts': ['bad text']}))\"\n"
        )
        res = self.run_safe_runner()
        self.assertEqual(res.returncode, 0, msg=f"STDOUT: {res.stdout}\nSTDERR: {res.stderr}")
        
        out_dir = os.path.join(self.temp_dir, "test_phase", "rate4.0", "seed0", "fcfs")
        
        self.assertTrue(os.path.exists(os.path.join(out_dir, "res.json")))
        self.assertTrue(os.path.exists(os.path.join(out_dir, "res_sanitized.json")))
        
        with open(os.path.join(out_dir, "res_sanitized.json")) as f:
            sanitized = json.load(f)
            self.assertNotIn("generated_texts", sanitized)
        
        with open(os.path.join(out_dir, "experiment_manifest.json")) as f:
            manifest = json.load(f)
            self.assertTrue(manifest["eligible_for_public_submission"])
            self.assertEqual(manifest["status"], "success")
            self.assertEqual(manifest["sanitized_result_file"], "res_sanitized.json")

if __name__ == '__main__':
    unittest.main()
