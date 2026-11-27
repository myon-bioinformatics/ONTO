"""Build a guide from independent fictional ontology data (stdlib + ONTO)."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import ontology
import knowledgegraph

DATA = Path(__file__).with_name("case.json")

def build(data):
    if data.get("synthetic") is not True or data.get("source") != "independent-fiction":
        raise ValueError("Only independent fictional fixtures are allowed")
    if data.get("evaluation_status") != "unverified":
        raise ValueError("Unmeasured effects must remain unverified")
    vocabulary = {key: (value[0], value[1]) for key, value in data["vocabulary"].items()}
    graph = {"nodes": data["nodes"], "edges": data["edges"]}
    findings = ontology.violations(graph, vocabulary)
    if findings:
        raise ValueError(findings)
    if knowledgegraph.relation_cycles(graph["edges"]):
        raise ValueError("Unexpected relation cycle")
    labels = {node["id"]: node["label"] for node in data["nodes"]}
    items = [f"- {node['type']}: {node['label']}" for node in data["nodes"]]
    return "# 架空のSNS短文攻略事例\n\n" + "\n".join(items) + "\n\n評価：未実測\n"

def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    print(build(data), end="")

if __name__ == "__main__":
    main()
