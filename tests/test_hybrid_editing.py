import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples/social-strategy"))
import editing_rules
import hybrid_editing

class HybridEditingTest(unittest.TestCase):
    def test_blocker_precedes_ranker(self):
        def forbidden(_):
            self.fail("ranker must not run")
        result = hybrid_editing.evaluate(editing_rules.load(), {"identifying_detail", "flat_ending"}, {"public", "humor"}, rank=forbidden)
        self.assertEqual(result["status"], "blocked")

    def test_ranker_cannot_invent_rules(self):
        result = hybrid_editing.evaluate(editing_rules.load(), {"flat_ending"}, {"humor"}, rank=lambda ids: ["invented"])
        self.assertEqual(result["ranking_status"], "invalid")
        self.assertEqual(result["rules"][0]["operation"], "add_punchline")

    def test_model_unknown_feature(self):
        result = hybrid_editing.from_model(editing_rules.load(), "架空の文章", {"humor"}, extract=lambda text: ["invented"])
        self.assertEqual(result["status"], "unknown")

    def test_valid_ranking_requires_review(self):
        result = hybrid_editing.from_model(editing_rules.load(), "冷蔵庫をリロードする。", {"humor"}, extract=lambda text: ["flat_ending", "weak_contrast"], rank=lambda ids: list(reversed(ids)))
        self.assertEqual(result["ranking_status"], "model_proposed")
        self.assertEqual(result["publication_status"], "review_required")
        self.assertEqual(result["rules"][0]["operation"], "add_punchline")
