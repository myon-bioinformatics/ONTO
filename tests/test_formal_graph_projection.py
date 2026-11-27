"""Connect the Lean graph projection to real JSON output and optional RDF I/O.

The stdlib tests isolate the already-encoded statement boundary. The optional
tests exercise rdflib and the real exchange decoder with a local transport stub.
"""

import copy
import itertools
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import ontology

try:
    from rdflib import BNode, Graph, Literal, URIRef, XSD
except ModuleNotFoundError:
    Graph = None


TRIPLES = (
    ("<urn:a>", "<urn:related>", "<urn:b>"),
    ("<urn:a>", "<urn:opposed>", "<urn:b>"),
    ("<urn:b>", "<urn:related>", "<urn:a>"),
    ("<urn:a>", "<urn:related>", "<urn:a>"),
    ("<urn:a>", "<urn:value>", '"urn:b"'),
    ("<urn:a>", "<urn:value>", '"label"@en'),
    ("<urn:a>", "<urn:value>", '"label"@ja'),
    ("<urn:a>", "<urn:value>", '"7"^^<http://www.w3.org/2001/XMLSchema#integer>'),
)


def relationship_triples(view):
    """Read only the fields that graph_json uses for directed RDF statements."""
    return [(rel["start"]["id"], rel["properties"]["predicate"], rel["end"]["id"])
            for rel in view["rels"]]


class GraphProjectionBridge(unittest.TestCase):
    def test_all_subgraphs_preserve_statements_and_exact_endpoints(self):
        # 2^8 subgraphs × 2 input orders. statements() owns RDF/N3 conversion;
        # this stdlib layer supplies its rows and invokes the real graph_json.
        for chosen in itertools.product((False, True), repeat=len(TRIPLES)):
            source = [triple for triple, include in zip(TRIPLES, chosen) if include]
            for reverse in (False, True):
                triples = list(reversed(source)) if reverse else source
                with self.subTest(chosen=chosen, reverse=reverse):
                    rows = [dict(zip(("subject", "predicate", "object"), triple)) for triple in triples]
                    graph = object()
                    with patch.object(ontology, "statements", return_value=rows) as statements:
                        view = ontology.graph_json(graph)
                    statements.assert_called_once_with(graph)
                    encoded = json.loads(json.dumps(view, ensure_ascii=False))
                    self.assertEqual(relationship_triples(encoded), triples)
                    expected_nodes = sorted({term for s, _, o in triples for term in (s, o)})
                    self.assertEqual(encoded["nodes"], [
                        {"id": term, "labels": ["OtlTerm"], "properties": {"term": term}}
                        for term in expected_nodes
                    ])
                    for rel in encoded["rels"]:
                        self.assertEqual(rel["label"], "OtlStatement")
                        self.assertIn(rel["start"]["id"], expected_nodes)
                        self.assertIn(rel["end"]["id"], expected_nodes)

    def test_projection_keeps_the_statement_snapshot_unchanged(self):
        rows = [dict(zip(("subject", "predicate", "object"), triple)) for triple in TRIPLES]
        snapshot = copy.deepcopy(rows)
        with patch.object(ontology, "statements", return_value=rows):
            ontology.graph_json(object())
        self.assertEqual(rows, snapshot)


@unittest.skipUnless(Graph is not None, "optional exchange dependency rdflib is not installed")
class RDFProjectionBridge(unittest.TestCase):
    def graph(self):
        # Canonical literal spellings: lexical normalization by rdflib is a
        # separate boundary from the exact N3-token projection proved in Lean.
        triples = [
            (URIRef("urn:a"), URIRef("urn:related"), URIRef("urn:b")),
            (URIRef("urn:a"), URIRef("urn:opposed"), URIRef("urn:b")),
            (URIRef("urn:b"), URIRef("urn:related"), URIRef("urn:a")),
            (URIRef("urn:a"), URIRef("urn:related"), URIRef("urn:a")),
            (URIRef("urn:a"), URIRef("urn:value"), Literal("urn:b")),
            (URIRef("urn:a"), URIRef("urn:value"), Literal("label", lang="en")),
            (URIRef("urn:a"), URIRef("urn:value"), Literal("label", lang="ja")),
            (URIRef("urn:a"), URIRef("urn:value"), Literal(7, datatype=XSD.integer)),
            (URIRef("urn:a"), URIRef("urn:value"), Literal("7", datatype=XSD.string)),
            (URIRef("urn:a"), URIRef("urn:value"), Literal('line\n"quoted" \\ text')),
        ]
        graph = Graph()
        for triple in triples:
            graph.add(triple)
        return graph

    def test_turtle_and_json_keep_typed_directed_statements(self):
        graph = self.graph()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic.ttl"
            graph.serialize(destination=path, format="turtle")
            restored = ontology.read_graph(path)
        self.assertEqual(set(restored), set(graph))
        expected = sorted(tuple(term.n3() for term in triple) for triple in graph)
        view = json.loads(json.dumps(ontology.graph_json(restored), ensure_ascii=False))
        self.assertEqual(relationship_triples(view), expected)
        self.assertEqual(len(view["rels"]), len(graph))
        reordered = Graph()
        for triple in reversed(list(graph)):
            reordered.add(triple)
        self.assertEqual(ontology.graph_json(reordered), view)

    def test_canonical_terms_survive_real_exchange_encoder_and_decoder(self):
        graph = self.graph()
        rows = ontology.statements(graph)
        with patch.object(ontology, "arcade", return_value=rows) as transport:
            ontology.transfer("arcade", "synthetic-projection", graph)
            exported = ontology.transfer("arcade", "synthetic-projection")
        self.assertEqual(transport.call_count, 2)
        self.assertEqual(transport.call_args_list[0].args[2],
                         {"scope": "synthetic-projection", "rows": rows})
        self.assertEqual(transport.call_args_list[1].args[2], {"scope": "synthetic-projection"})
        self.assertEqual(set(exported), set(graph))
        self.assertEqual(ontology.graph_json(exported), ontology.graph_json(graph))

    def test_unnamed_resources_are_rejected_before_projection(self):
        for triple in (
            (BNode("source"), URIRef("urn:p"), URIRef("urn:o")),
            (URIRef("urn:s"), URIRef("urn:p"), BNode("object")),
        ):
            with self.subTest(triple=triple):
                graph = Graph()
                graph.add(triple)
                with self.assertRaisesRegex(ValueError, "stable IRIs"):
                    ontology.graph_json(graph)

    def test_duplicate_database_relationship_is_rejected(self):
        rows = ontology.statements(self.graph())
        with patch.object(ontology, "arcade", return_value=rows + rows[:1]):
            with self.assertRaisesRegex(ValueError, "Duplicate database relationship"):
                ontology.transfer("arcade", "synthetic-projection")


if __name__ == "__main__":
    unittest.main()
