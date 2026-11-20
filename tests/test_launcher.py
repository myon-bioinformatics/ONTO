import contextlib
import io
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import onto_cli


class Launcher(unittest.TestCase):
    def test_help_and_versions_do_not_load_rdf_or_uv(self):
        for args, name in [([], "onto"), (["--help"], "onto"), (["exchange", "--help"], "onto exchange")]:
            result = subprocess.run(
                [sys.executable, "-S", str(Path(__file__).resolve().parents[1] / "onto_cli.py"), *args], capture_output=True, text=True, check=True
            )
            self.assertIn(f"usage: {name}", result.stdout)
        with patch.object(onto_cli.shutil, "which", side_effect=AssertionError), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(onto_cli.main(["versions", "--json"]), 0)
        self.assertEqual(json.loads(out.getvalue())["otl"]["commit"], onto_cli._OTL_COMMIT)

    def test_exchange_forwards_args_and_keeps_stdout(self):
        args = ["export", "neo4j", "trial", "--format", "json"]
        def run(received, *, prog):
            self.assertEqual(received, args)
            self.assertEqual(prog, "onto exchange")
            print('{"nodes":[],"rels":[]}')
            return 7
        with patch("ontology.main", side_effect=run), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(onto_cli.main(["exchange", *args]), 7)
        self.assertEqual(json.loads(out.getvalue()), {"nodes": [], "rels": []})

    def test_exact_child_dispatch_inherits_offline_and_streams(self):
        pin = "git+https://github.com/myon-bioinformatics/OnTautoLogy.git@a4173e778ffe6fed7ed216b7b0044ca42e589fc7"
        for args, source in [(["--help"], pin), (["entails", "-"], pin),
                             (["entails", "-", "--ttl"], "ontautology[exchange] @ " + pin),
                             (["exchange", "export", "neo4j", "space scope", "out.json"], "ontautology[exchange] @ " + pin)]:
            def run(argv, **kwargs):
                self.assertEqual(argv, ["/bin/uv", "tool", "run", "--from", source, "ontautology", *args])
                self.assertEqual(kwargs, {"check": False})
                self.assertEqual(os.environ["UV_OFFLINE"], "1")
                return subprocess.CompletedProcess(argv, 9)
            with self.subTest(args=args), patch.dict(os.environ, UV_OFFLINE="1"), patch.object(
                onto_cli.shutil, "which", return_value="/bin/uv"
            ), patch.object(onto_cli.subprocess, "run", side_effect=run):
                self.assertEqual(onto_cli.main(["otl", *args]), 9)

    def test_missing_uv_is_reported_on_stderr(self):
        with patch.object(onto_cli.shutil, "which", return_value=None), contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(onto_cli.main(["otl", "--help"]), 127)
        self.assertIn("requires uv", err.getvalue())


if __name__ == "__main__":
    unittest.main()
