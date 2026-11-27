"""Select hypothetical editing operations from explicit observations."""
import json
from pathlib import Path

def select(data, features, conditions):
    if data.get("synthetic") is not True or data.get("evaluation_status") != "unverified":
        raise ValueError("Expected synthetic, unverified rules")
    matches = [r for r in data["rules"] if r["feature"] in features and r["condition"] in conditions]
    blockers = [r for r in matches if r["criterion"] in {"privacy", "accuracy"}]
    if blockers:
        return {"status": "blocked", "rules": blockers}
    return {"status": "hypothesis" if matches else "unknown", "rules": matches}

def load():
    return json.loads(Path(__file__).with_name("editing-rules.json").read_text(encoding="utf-8"))
