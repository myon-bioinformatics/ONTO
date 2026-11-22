import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import BytesIO, StringIO, TextIOWrapper
from types import SimpleNamespace
from unittest.mock import Mock, patch

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
        value = json.loads(output.getvalue())["results"]["bindings"][0]["x"]
        self.assertEqual((value["value"], value["xml:lang"]), ("日本語", "ja"))
        with patch("sys.stdin", TextIOWrapper(BytesIO(raw))), patch.object(exchange, "transfer") as send:
            self.assertEqual(exchange.main(["import", "neo4j", "demo", "-"]), 0)
        self.assertEqual(set(send.call_args.args[2]), set(Graph().parse(data=raw, format="turtle")))

    def test_empty_turtle_stdin_is_a_valid_empty_graph(self):
        query = ["query", "-", "SELECT ?x WHERE { <urn:a> <urn:p> ?x }"]
        output = StringIO()
        with patch("sys.stdin", TextIOWrapper(BytesIO(b""))), redirect_stdout(output):
            self.assertEqual(exchange.main(query), 0)
        self.assertEqual(json.loads(output.getvalue())["results"]["bindings"], [])
        with patch("sys.stdin", TextIOWrapper(BytesIO(b""))), patch.object(exchange, "transfer") as send:
            self.assertEqual(exchange.main(["import", "neo4j", "demo", "-"]), 0)
        self.assertEqual(len(send.call_args.args[2]), 0)

    def test_turtle_stdin_errors_stop_before_query_or_transfer(self):
        for args in (
            ["query", "-", "SELECT * WHERE { ?s ?p ?o }"],
            ["import", "neo4j", "demo", "-"],
        ):
            for source, message in (
                (TextIOWrapper(BytesIO(b"<urn:a> <urn:p> [")), "Invalid Turtle on stdin"),
                (TextIOWrapper(BytesIO(b'<urn:a> <urn:p> "\xff" .')), "must be valid UTF-8"),
                (None, "Turtle stdin is unavailable"),
                (StringIO(""), "Turtle stdin is unavailable"),
                (SimpleNamespace(buffer=Mock(**{"read.side_effect": OSError("read failed")})),
                 "Could not read Turtle from stdin"),
            ):
                with self.subTest(action=args[0], error=message):
                    stdout, stderr = StringIO(), StringIO()
                    with (patch("sys.stdin", source), patch.object(exchange, "transfer") as send,
                          redirect_stdout(stdout), redirect_stderr(stderr), self.assertRaises(SystemExit) as stop):
                        exchange.main(args)
                    self.assertEqual(stop.exception.code, 2)
                    self.assertEqual(stdout.getvalue(), "")
                    self.assertIn(message, stderr.getvalue())
                    self.assertNotIn("Traceback", stderr.getvalue())
                    send.assert_not_called()
