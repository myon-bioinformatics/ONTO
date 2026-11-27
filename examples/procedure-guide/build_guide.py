"""Generate an anonymized Markdown procedure guide from an ONTO vocabulary graph.

Run: python -S examples/procedure-guide/build_guide.py examples/procedure-guide/housing-contract.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import knowledgegraph
import ontology

ALLOWED = {"reported-done", "done", "reported-approved", "done-receipt-unverified", "unverified"}
SENSITIVE_KEYS = {"address", "email", "phone", "full_name", "bank_account", "raw_message", "line_id"}
SENSITIVE_TYPES = {"Person", "Address", "Account"}


def render(data):
    if data.get("privacy", {}).get("classification") != "public-synthetic":
        raise ValueError("Only explicitly public-synthetic cases are allowed")
    if data.get("privacy", {}).get("raw_records_included") is not False:
        raise ValueError("Raw records must be excluded")
    if any(SENSITIVE_KEYS.intersection(n) or n["type"] in SENSITIVE_TYPES for n in data["nodes"]):
        raise ValueError("Potential personal-data fields/types in case")
    findings = ontology.violations(data, data["vocabulary"])
    if findings:
        raise ValueError(f"Vocabulary findings: {findings}")
    tasks = {n["id"]: n for n in data["nodes"] if n["type"] == "Task"}
    if any(task.get("status") not in ALLOWED for task in tasks.values()):
        raise ValueError("Unknown task state")
    dependencies = [e for e in data["edges"] if e["relation"] == "precedes"]
    order = knowledgegraph.topological_order(dependencies)
    if order["cycle"]:
        raise ValueError("Circular task dependencies")
    if set(order["order"]) != set(tasks):
        raise ValueError("Every task must be in the documented sequence")
    lines = ["# 🏠 " + data["title"], "", "匿名化した学習用の例。個別の契約条件は必ず確認する。", "",
             "## 手続きの順番と状態", ""]
    labels = {"done":"✅ 実施済み", "reported-done":"📨 実施の連絡あり",
              "reported-approved":"✅ 通過の連絡あり",
              "done-receipt-unverified":"🟠 操作済み・受領未確認", "unverified":"❓ 未確認"}
    for i, key in enumerate(order["order"], 1):
        task = tasks[key]
        lines.append(f"{i}. {task['name']} — {labels[task['status']]}")
    lines.extend(["", "## 必要な書類", ""])
    nodes = {n["id"]: n for n in data["nodes"]}
    for edge in data["edges"]:
        if edge["relation"] == "requires":
            lines.append(f"- {nodes[edge['source']]['name']} → {nodes[edge['target']]['name']}")
    lines.extend(["", "## 知識グラフ", "", knowledgegraph.graph_mermaid(data).strip(), "",
                  "※状態の記録は契約の法的効力・受領・切替完了を証明しません。", ""])
    return "\n".join(lines)


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        raise SystemExit("Usage: build_guide.py GRAPH.json")
    data = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    print(render(data), end="")


if __name__ == "__main__":
    main()
