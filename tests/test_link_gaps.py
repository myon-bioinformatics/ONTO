import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ontology import link_gaps


def edge(source, target, relation="supported_by"):
    return {"source": source, "relation": relation, "target": target}


def fixture():
    nodes = [{"id": "assessment"}, {"id": "stored"}, {"id": "retained"}, {"id": "old", "available": False}]
    expected = [edge("assessment", x) for x in ("stored", "retained", "old", "unknown")]
    # An arrow backwards or an unrelated association does not meet the requirement.
    actual = [edge("stored", "assessment"), edge("assessment", "stored", "near"), edge("assessment", "retained")]
    return {"nodes": nodes, "edges": actual, "expected_links": expected}


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
