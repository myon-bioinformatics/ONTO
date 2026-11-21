import json
import unittest
from contextlib import redirect_stdout
from io import BytesIO, StringIO, TextIOWrapper
from unittest.mock import patch

try:
    from rdflib import Graph
except ModuleNotFoundError:
    Graph = None
import ontology as exchange


@unittest.skipUnless(Graph is not None, "rdflib is not installed")
class ExportStreams(unittest.TestCase):
    def test_stdout_can_be_read_as_turtle_and_json(self):
        graph = Graph().parse(data='<urn:a> <urn:p> "日本語"@ja .', format="nt")
        with patch.object(exchange, "transfer", return_value=graph):
            turtle = StringIO()
            with redirect_stdout(turtle):
                self.assertEqual(exchange.main(["export", "neo4j", "demo"]), 0)
            self.assertEqual(set(Graph().parse(data=turtle.getvalue(), format="turtle")), set(graph))
            result = StringIO()
            with redirect_stdout(result):
                self.assertEqual(exchange.main(["export", "arcade", "demo", "-", "--format", "json"]), 0)
            self.assertEqual(json.loads(result.getvalue()), exchange.graph_json(graph))

    def test_turtle_stdin_for_query_and_import(self):
        raw = '<urn:a> <urn:p> "日本語"@ja .'.encode()
        output = StringIO()
        with patch("sys.stdin", TextIOWrapper(BytesIO(raw))), redirect_stdout(output):
            self.assertEqual(exchange.main(["query", "-", "SELECT ?x WHERE { <urn:a> <urn:p> ?x }"]), 0)
        self.assertEqual(json.loads(output.getvalue())["results"]["bindings"][0]["x"]["value"], "日本語")
        with patch("sys.stdin", TextIOWrapper(BytesIO(raw))), patch.object(exchange, "transfer") as send:
            self.assertEqual(exchange.main(["import", "neo4j", "demo", "-"]), 0)
        self.assertEqual(set(send.call_args.args[2]), set(Graph().parse(data=raw, format="turtle")))
