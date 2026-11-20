import json
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from rdflib import Graph
import onto_exchange as exchange


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
