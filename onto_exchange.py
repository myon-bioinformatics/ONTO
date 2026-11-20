"""Compatibility entry for the exchange commands now provided by ontology."""
from ontology import READ, WRITE, arcade, graph_json, main, read_graph, statements, transfer


if __name__ == "__main__":
    raise SystemExit(main(prog="python -m onto_exchange"))
