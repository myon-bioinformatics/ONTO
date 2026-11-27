"""Find available evidence whose expected link is missing."""
import argparse
import json
import sys
from pathlib import Path


def link_gaps(graph, expected_links):
    """Audit explicitly expected direct, directed links against a graph.

    Existing endpoints without their exact edge are unlinked. Missing nodes and
    explicitly unavailable nodes are different findings. No claim is made about
    paths not listed in expected_links, and no new facts are inferred.
    """
    nodes = {node["id"]: node for node in graph["nodes"]}

    def key(edge):
        return edge["source"], edge["relation"], edge["target"]

    actual = {key(edge) for edge in graph["edges"]}
    findings = []
    for source, relation, target in sorted({key(edge) for edge in expected_links}):
        subject = {"source": source, "relation": relation, "target": target}
        endpoints = tuple(dict.fromkeys((source, target)))
        missing = [id_ for id_ in endpoints if id_ not in nodes]
        unavailable = [id_ for id_ in endpoints if id_ in nodes and nodes[id_].get("available") is False]
        if missing:
            findings.append({"kind": "missing-endpoint", **subject, "endpoints": missing})
        if unavailable:
            findings.append({"kind": "unavailable-endpoint", **subject, "endpoints": unavailable})
        if not missing and not unavailable and (source, relation, target) not in actual:
            findings.append({"kind": "unlinked", **subject})
    return findings


def main(argv=None, *, prog=None):
    parser = argparse.ArgumentParser(prog=prog, description=__doc__)
    parser.add_argument("graph", type=Path, help="JSON graph with expected_links, or - for stdin")
    parser.add_argument("--expected", type=Path, help="override expected_links with a JSON list")
    args = parser.parse_args(argv)
    try:
        graph = json.load(sys.stdin) if args.graph == Path("-") else json.loads(args.graph.read_text(encoding="utf-8"))
        expected = (json.loads(args.expected.read_text(encoding="utf-8")) if args.expected else graph["expected_links"])
        if not all(isinstance(items, list) for items in (graph["nodes"], graph["edges"], expected)):
            raise ValueError("nodes, edges and expected links must be JSON arrays")
        findings = link_gaps(graph, expected)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, f"{parser.prog}: {exc}\n")
    print(json.dumps(findings, indent=2, ensure_ascii=False))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
