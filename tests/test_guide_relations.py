import json
from pathlib import Path
import unittest

class GuideRelationsTest(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((Path(__file__).resolve().parents[1] / "examples/social-strategy/relation-candidates.json").read_text(encoding="utf-8"))

    def test_unique_vocabulary(self):
        ids = [r["id"] for r in self.data["relations"]]
        self.assertEqual(len(ids), 13)
        self.assertEqual(len(set(ids)), len(ids))
        for alias, canonical in self.data["aliases"].items():
            self.assertNotIn(alias, ids)
            self.assertIn(canonical, ids)

    def test_hypotheses_not_measured(self):
        ids = {r["id"] for r in self.data["relations"]}
        for edge in self.data["edges"]:
            self.assertIn(edge["relation"], ids)
            self.assertEqual(edge["status"], "hypothesis")
            self.assertIsNone(edge["confidence"])
            self.assertEqual(edge["evidence"], [])
            self.assertEqual(edge["counterexamples"], [])
            self.assertTrue(edge["conditions"])

    def test_tradeoff(self):
        self.assertEqual({e["relation"] for e in self.data["edges"]}, {"improves", "degrades"})
        self.assertEqual(len({tuple(e["conditions"]) for e in self.data["edges"]}), 2)
