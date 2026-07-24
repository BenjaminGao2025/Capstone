import unittest
import os
import tempfile
import json
import shutil
import subprocess

class TestSanitizer(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.sanitizer_script = os.path.join(self.repo_root, "scripts", "sanitize_result_json.py")

        self.input_json = os.path.join(self.temp_dir, "input.json")
        with open(self.input_json, "w") as f:
            json.dump({"a": 1, "generated_texts": ["hello"]}, f)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def run_sanitizer(self, input_path, output_path):
        return subprocess.run(
            ["python3", self.sanitizer_script, "--input", input_path, "--output", output_path],
            capture_output=True,
            text=True
        )

    def test_same_file(self):
        res = self.run_sanitizer(self.input_json, self.input_json)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("cannot be the same file", res.stderr)

    def test_output_exists(self):
        out = os.path.join(self.temp_dir, "out.json")
        with open(out, "w") as f:
            f.write("exists")
        res = self.run_sanitizer(self.input_json, out)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("already exists", res.stderr)
        
        with open(out, "r") as f:
            self.assertEqual(f.read(), "exists") # didn't overwrite

    def test_output_symlink_to_input(self):
        out = os.path.join(self.temp_dir, "out_sym.json")
        os.symlink(self.input_json, out)
        res = self.run_sanitizer(self.input_json, out)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("symlink to input", res.stderr)

    def test_missing_generated_texts(self):
        out = os.path.join(self.temp_dir, "out.json")
        inp2 = os.path.join(self.temp_dir, "inp2.json")
        with open(inp2, "w") as f:
            json.dump({"a": 1}, f)
        res = self.run_sanitizer(inp2, out)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("generated_texts not found", res.stderr)

    def test_valid_sanitization(self):
        out = os.path.join(self.temp_dir, "out.json")
        res = self.run_sanitizer(self.input_json, out)
        self.assertEqual(res.returncode, 0)
        
        out_data = json.loads(res.stdout)
        self.assertEqual(out_data["sanitizer_version"], "1.0.0")
        
        with open(out, "r") as f:
            san_json = json.load(f)
        self.assertEqual(san_json, {"a": 1})

if __name__ == '__main__':
    unittest.main()
