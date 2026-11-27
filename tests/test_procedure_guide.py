import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "examples/procedure-guide/housing-contract.json"
sys.path.insert(0, str(SAMPLE.parent))
from build_guide import render


class ProcedureGuideTests(unittest.TestCase):
    def sample(self):
        return json.loads(SAMPLE.read_text(encoding="utf-8"))

    def test_guide_and_unverified_status(self):
        output = render(self.sample())
        self.assertIn("❓ 未確認", output)
        self.assertIn("🟠 操作済み・受領未確認", output)
        self.assertIn("📄 自治体発行の住民票の写し", output)

    def test_no_raw_records(self):
        graph = self.sample()
        graph["nodes"][0]["address"] = "private"
        with self.assertRaises(ValueError):
            render(graph)
        graph = self.sample()
        graph["privacy"]["raw_records_included"] = True
        with self.assertRaises(ValueError):
            render(graph)

    def test_cycles_and_unknown_class_rejected(self):
        graph = self.sample()
        graph["edges"].append({"source":"switch","relation":"precedes","target":"notice"})
        with self.assertRaises(ValueError):
            render(graph)
        graph = self.sample()
        graph["nodes"][0]["type"] = "Unknown"
        with self.assertRaises(ValueError):
            render(graph)

    def test_cli_without_dependencies(self):
        run = subprocess.run([sys.executable, "-S", str(SAMPLE.parent / "build_guide.py"), str(SAMPLE)],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("## 手続きの順番と状態", run.stdout)


if __name__ == "__main__":
    unittest.main()
