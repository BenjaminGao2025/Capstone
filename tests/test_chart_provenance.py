import unittest
import os
import tempfile
import json
import shutil
import sys

# Add scripts directory to path to import make_defense_charts
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(repo_root, "scripts"))
import make_defense_charts
import hashlib

def get_hash(data):
    sha = hashlib.sha256()
    sha.update(data)
    return sha.hexdigest()

class TestChartProvenance(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        make_defense_charts.REPO_ROOT = self.temp_dir
        
        self.result_path = os.path.join(self.temp_dir, "test.json")
        self.result_data = json.dumps({"ttfts": [0.1], "itls": [[0.1]], "mean_ttft_ms": 100.0, "schedule_type": "fcfs", "request_rate": 4.0, "completed": 1})
        with open(self.result_path, "w") as f:
            f.write(self.result_data)
        
        self.result_sha = get_hash(self.result_data.encode())
        
        self.manifest = {
            "experiments": [
                {
                    "experiment_id": "test-exp",
                    "eligible_for_aggregation": True,
                    "status": "valid",
                    "result_path": "test.json",
                    "result_sha256": self.result_sha,
                    "arm": "fcfs",
                    "request_rate": 4.0,
                    "completed": 1,
                    "expected_num_prompts": 1
                }
            ]
        }
        make_defense_charts.manifest = self.manifest

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_valid_load(self):
        data = make_defense_charts.get_experiment_data("test-exp")
        self.assertAlmostEqual(data["mean_ttft"], 0.1)

    def test_missing_id(self):
        with self.assertRaisesRegex(RuntimeError, "Missing experiment ID"):
            make_defense_charts.get_experiment_data("nonexistent")

    def test_duplicate_id(self):
        self.manifest["experiments"].append(self.manifest["experiments"][0].copy())
        with self.assertRaisesRegex(RuntimeError, "Duplicate experiment ID"):
            make_defense_charts.get_experiment_data("test-exp")

    def test_ineligible_id(self):
        self.manifest["experiments"][0]["eligible_for_aggregation"] = False
        with self.assertRaisesRegex(RuntimeError, "Ineligible ID"):
            make_defense_charts.get_experiment_data("test-exp")

    def test_sha_mismatch(self):
        self.manifest["experiments"][0]["result_sha256"] = "badsha"
        with self.assertRaisesRegex(RuntimeError, "SHA mismatch"):
            make_defense_charts.get_experiment_data("test-exp")

    def test_missing_result(self):
        self.manifest["experiments"][0]["result_path"] = "missing.json"
        with self.assertRaisesRegex(RuntimeError, "Missing result file"):
            make_defense_charts.get_experiment_data("test-exp")

    def test_wrong_scheduler(self):
        self.manifest["experiments"][0]["arm"] = "ltr"
        with self.assertRaisesRegex(RuntimeError, "Wrong scheduler"):
            make_defense_charts.get_experiment_data("test-exp")

    def test_path_traversal(self):
        self.manifest["experiments"][0]["result_path"] = "../outside.json"
        with self.assertRaisesRegex(RuntimeError, "Unsafe path traversal"):
            make_defense_charts.get_experiment_data("test-exp")

if __name__ == '__main__':
    unittest.main()
