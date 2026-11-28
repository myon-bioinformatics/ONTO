"""Regression tests for independently fictional social strategy fixture."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples" / "social-strategy"))
import build_guide

DATA = Path(build_guide.__file__).with_name("case.json")

class TestSocialStrategy(unittest.TestCase):
    def fixture(self):
        return json.loads(DATA.read_text(encoding="utf-8"))

    def test_valid_graph_and_unverified_claim(self):
        rendered = build_guide.build(self.fixture())
        self.assertIn("評価：未実測", rendered)
        self.assertIn("Goal:", rendered)

    def test_reject_source_linkage(self):
        data = self.fixture()
        data["source"] = "real-user-post"
        with self.assertRaises(ValueError):
            build_guide.build(data)

    def test_reject_false_measurement(self):
        data = self.fixture()
        data["evaluation_status"] = "confirmed"
        with self.assertRaises(ValueError):
            build_guide.build(data)

    def test_reject_broken_edge(self):
        data = self.fixture()
        data["edges"][0]["target"] = "missing"
        with self.assertRaises(ValueError):
            build_guide.build(data)

    def test_fixture_has_no_identity_or_location_keys(self):
        data = self.fixture()
        forbidden = {"name", "username", "handle", "address", "location", "residence", "city", "prefecture", "region", "country", "postcode", "latitude", "longitude", "coordinates", "timezone", "employer", "company", "project", "contract", "timestamp", "date", "quote", "url", "screenshot", "source_text", "source_id", "ip"}
        def walk(obj):
            if isinstance(obj, dict):
                self.assertFalse(forbidden.intersection(k.lower() for k in obj))
                for value in obj.values():
                    walk(value)
            elif isinstance(obj, list):
                for value in obj:
                    walk(value)
        walk(data)

if __name__ == "__main__":
    unittest.main()
