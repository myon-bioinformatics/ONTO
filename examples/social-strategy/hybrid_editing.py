"""Model-independent orchestration for synthetic editing fixtures.

Model callbacks are injected; no network, model downloads or private input storage.
"""
import editing_rules

def evaluate(data, observations, conditions, *, rank=None):
    """Rank only rule-authorized candidates; never override a blocker."""
    result = editing_rules.select(data, observations, conditions)
    if result["status"] != "hypothesis" or rank is None:
        return result
    ids = [r["id"] for r in result["rules"]]
    proposed = rank(tuple(ids))
    if not isinstance(proposed, (list, tuple)) or len(proposed) != len(ids) or any(not isinstance(x, str) for x in proposed) or set(proposed) != set(ids):
        return {**result, "ranking_status": "invalid"}
    by_id = {r["id"]: r for r in result["rules"]}
    return {**result, "rules": [by_id[x] for x in proposed], "ranking_status": "model_proposed"}

def from_model(data, text, conditions, *, extract, rank=None):
    """Accept only vocabulary IDs; absence of evidence is not a safety verdict."""
    known = {r["feature"] for r in data["rules"]}
    observed = extract(text)
    if not isinstance(observed, (list, tuple)) or any(not isinstance(x, str) or x not in known for x in observed):
        return {"status": "unknown", "rules": [], "extraction_status": "invalid"}
    return {**evaluate(data, set(observed), conditions, rank=rank),
            "extraction_status": "model_proposed", "publication_status": "review_required"}
