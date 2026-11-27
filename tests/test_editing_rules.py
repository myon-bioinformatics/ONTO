import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("editing_rules", Path(__file__).resolve().parents[1] / "examples/social-strategy/editing_rules.py")
rules = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rules)

class EditingRulesTest(unittest.TestCase):
    def test_audience_changes_operation(self):
        for audience, expected in [("general_audience", "simplify_terms"), ("expert_audience", "preserve_terms")]:
            result = rules.select(rules.load(), {"technical_terms"}, {audience})
            self.assertEqual(result["rules"][0]["operation"], expected)

    def test_privacy_blocks_humor(self):
        result = rules.select(rules.load(), {"identifying_detail", "flat_ending"}, {"public", "humor"})
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["rules"][0]["criterion"], "privacy")

    def test_unknown(self):
        self.assertEqual(rules.select(rules.load(), {"unknown"}, {"humor"})["status"], "unknown")

    def test_unmeasured(self):
        data = rules.load()
        data["evaluation_status"] = "confirmed"
        with self.assertRaises(ValueError):
            rules.select(data, set(), set())

    def test_examples_chain(self):
        examples = rules.load()["examples"]
        for left, right in zip(examples, examples[1:]):
            self.assertEqual(left["output"], right["input"])
