import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from mottainai import link_gaps


def edge(source, target, relation="supported_by"):
    return {"source": source, "relation": relation, "target": target}


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "examples/mottainai/evidence-links.json"


def fixture():
    return json.loads(SAMPLE.read_text(encoding="utf-8"))


class LinkGapTests(unittest.TestCase):
    def test_explicit_expectations_distinguish_available_and_unavailable(self):
        graph = fixture()
        results = link_gaps(graph, graph["expected_links"])
        self.assertEqual([(r["target"], r["kind"]) for r in results], [
            ("old", "unavailable-endpoint"), ("stored", "unlinked"), ("unknown", "missing-endpoint")])
        self.assertEqual(link_gaps(graph, []), [])
        self.assertEqual(link_gaps(graph, [edge("assessment", "retained")]), [])

    def test_cli_accepts_stdin_and_fails_on_gap(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "expected.json"
            path.write_text(json.dumps([edge("assessment", "retained")]))
            args = [sys.executable, "-S", str(root / "onto_cli.py"), "audit-links", "-"]
            data = json.dumps(fixture())
            result = subprocess.run(args, input=data, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(len(json.loads(result.stdout)), 3)
            clean = subprocess.run(args + ["--expected", str(path)], input=data, capture_output=True, text=True)
            self.assertEqual(clean.returncode, 0, clean.stderr)
            self.assertEqual(json.loads(clean.stdout), [])
        direct = subprocess.run([sys.executable, "-S", str(ROOT / "mottainai.py"), str(SAMPLE)],
                                capture_output=True, text=True)
        self.assertEqual(direct.returncode, 1, direct.stderr)
        self.assertEqual(json.loads(direct.stdout), json.loads(result.stdout))
