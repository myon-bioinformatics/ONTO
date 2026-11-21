"""Resolution order, markers, and errors for the canonical onto_path.py."""
import importlib.util
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import onto_path


def _touch(path, text="marker\n"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class PathTests(unittest.TestCase):
    def setUp(self):
        self._environ = patch.dict(os.environ, {}, clear=False)
        self._environ.start()
        os.environ.pop(onto_path.ONTO_ENV, None)
        os.environ.pop(onto_path.TAXONTOY_ENV, None)
        self.addCleanup(self._environ.stop)

    def test_explicit_beats_env_beats_sibling_beats_walk_up(self):
        marker = onto_path.ONTO_MARKER
        dirname = onto_path.ONTO_DIRNAME
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            explicit = base / "explicit"
            via_env = base / "from-env"
            tree = base / "tree"
            # Neighbor check is anchor.parent / dirname; walk-up is a higher hit.
            anchor = tree / "proj" / "nested" / "tool.py"
            sibling = anchor.parent / dirname
            walked = tree / dirname
            _touch(explicit / marker, "explicit\n")
            _touch(via_env / marker, "env\n")
            _touch(sibling / marker, "sibling\n")
            _touch(walked / marker, "walk\n")
            _touch(anchor, "")
            with patch.dict(os.environ, {onto_path.ONTO_ENV: str(via_env)}):
                self.assertEqual(
                    onto_path.resolve_root("ONTO", explicit, anchor=anchor),
                    explicit.resolve(),
                    "explicit",
                )
                self.assertEqual(onto_path.resolve_root("ONTO", anchor=anchor), via_env.resolve(), "env")
            os.environ.pop(onto_path.ONTO_ENV, None)
            self.assertEqual(onto_path.resolve_root("ONTO", anchor=anchor), sibling.resolve(), "sibling")
            (sibling / marker).unlink()
            self.assertEqual(onto_path.resolve_root("ONTO", anchor=anchor), walked.resolve(), "walk-up")

    def test_onto_resolves_to_its_own_root(self):
        marker = onto_path.ONTO_MARKER
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            own = base / "this-checkout"
            _touch(base / "ONTO" / marker, "named-sibling\n")
            _touch(own / marker, "own\n")
            anchor = _touch(own / "pkg" / "tool.py", "")
            self.assertEqual(onto_path.resolve_root("ONTO", anchor=anchor), own.resolve())
            self.assertEqual(onto_path.resolve_root("ONTO", anchor=own), own.resolve())
            self.assertEqual(onto_path.marker_file("ONTO", anchor=anchor), (own / marker).resolve())
        self.assertEqual(Path(onto_path.__file__).resolve(), (_REPO / "onto_path.py").resolve())
        self.assertEqual(onto_path.resolve_root("ONTO"), _REPO)
        self.assertEqual(onto_path.marker_file("ONTO", anchor=_REPO / "tests" / "test_onto_path.py"), _REPO / marker)

    def test_sibling_directory_beats_a_nested_copy_and_walks_up(self):
        marker = onto_path.TAXONTOY_MARKER
        name = onto_path.TAXONTOY_DIRNAME
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            project = base / "proj"
            _touch(base / name / marker, "sibling\n")
            _touch(project / name / marker, "nested\n")
            anchor = _touch(project / "tool.py", "")
            self.assertEqual(onto_path.resolve_root("TaxOntOy", anchor=anchor), (base / name).resolve())
            (base / name / marker).unlink()
            nested = base / "parent" / "vendor" / "app"
            _touch(base / "parent" / name / marker, "ancestor\n")
            deep = _touch(nested / "tool.py", "")
            self.assertEqual(onto_path.resolve_root("TaxOntOy", anchor=deep), (base / "parent" / name).resolve())

    def test_marker_must_be_a_file(self):
        marker = onto_path.ONTO_MARKER
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            directory = base / "decoy" / marker
            directory.mkdir(parents=True)
            anchor = _touch(base / "decoy" / "app" / "tool.py", "")
            with self.assertRaises(onto_path.RootError) as raised:
                onto_path.resolve_root("ONTO", anchor=anchor)
            self.assertEqual(
                str(raised.exception),
                f"ONTO が見つからない。ONTO_ROOT= を渡す（{marker} がある checkout）",
            )
            unmarked = base / "empty"
            unmarked.mkdir()
            with self.assertRaises(onto_path.RootError) as raised:
                onto_path.resolve_root("ONTO", unmarked, anchor=anchor)
            self.assertEqual(
                str(raised.exception),
                f"ONTO が見つからない（{unmarked.resolve()} に {marker} がない）。ONTO_ROOT= を渡す",
            )

    def test_error_messages_name_the_env_var(self):
        marker = onto_path.ONTO_MARKER
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            anchor = _touch(base / "alone" / "tool.py", "")
            with self.assertRaises(onto_path.RootError) as raised:
                onto_path.resolve_root("ONTO", anchor=anchor)
            self.assertEqual(
                str(raised.exception),
                f"ONTO が見つからない。ONTO_ROOT= を渡す（{marker} がある checkout）",
            )
            with self.assertRaises(onto_path.RootError) as raised:
                onto_path.resolve_root("TaxOntOy", anchor=anchor)
            self.assertEqual(
                str(raised.exception),
                f"TaxOntOy が見つからない。TAXONTOY_ROOT= を渡す（{onto_path.TAXONTOY_MARKER} がある checkout）",
            )
            with self.assertRaises(onto_path.RootError) as raised:
                onto_path.resolve_root("missing", anchor=anchor)
            self.assertEqual(str(raised.exception), "未知の checkout 名: missing（ONTO, TaxOntOy）")
            via_env = base / "from-env"
            _touch(via_env / marker, "env\n")
            bad = base / "not-a-checkout"
            bad.mkdir()
            _touch(base / "ONTO" / marker, "would-infer\n")
            with patch.dict(os.environ, {onto_path.ONTO_ENV: str(bad)}):
                with self.assertRaises(onto_path.RootError) as raised:
                    onto_path.resolve_root("ONTO", anchor=anchor)
            self.assertEqual(
                str(raised.exception),
                f"ONTO が見つからない（{bad.resolve()} に {marker} がない）。ONTO_ROOT= を渡す",
            )
            with patch.dict(os.environ, {onto_path.ONTO_ENV: str(via_env)}):
                with self.assertRaises(onto_path.RootError) as raised:
                    onto_path.resolve_root("ONTO", "   ", anchor=anchor)
            self.assertEqual(
                str(raised.exception),
                f"ONTO が見つからない。ONTO_ROOT= を渡す（{marker} がある checkout）",
            )
            self.assertNotIn(str(via_env), str(raised.exception))
        with self.assertRaises(onto_path.RootError) as raised:
            onto_path.explicit_from_argv(["--onto-root"])
        self.assertEqual(str(raised.exception), "--onto-root の値が無い。ONTO_ROOT= を渡す")
        with self.assertRaises(onto_path.RootError) as raised:
            onto_path.explicit_from_argv(["--taxontoy-root"])
        self.assertEqual(str(raised.exception), "--taxontoy-root の値が無い。TAXONTOY_ROOT= を渡す")
        blank = {"ONTO": None, "TaxOntOy": None}
        self.assertEqual(onto_path.explicit_from_argv([]), blank)
        self.assertEqual(
            onto_path.explicit_from_argv(["graph", "--onto-root", "/onto", "--taxontoy-root", "/tax"]),
            {"ONTO": "/onto", "TaxOntOy": "/tax"},
        )
        self.assertEqual(
            onto_path.explicit_from_argv(["--onto-root=/onto", "--taxontoy-root=/tax", "audit"]),
            {"ONTO": "/onto", "TaxOntOy": "/tax"},
        )
        self.assertEqual(
            onto_path.explicit_from_argv(["--onto-root", "/first", "--onto-root", "/second"]),
            {"ONTO": "/second", "TaxOntOy": None},
        )
        self.assertEqual(onto_path.explicit_from_argv(["--", "--onto-root", "/ignored"]), blank)
        self.assertEqual(
            onto_path.explicit_from_argv(["--onto-root", "/onto", "--", "--taxontoy-root", "/tax"]),
            {"ONTO": "/onto", "TaxOntOy": None},
        )
        self.assertEqual(onto_path.explicit_from_argv(["--onto-root-extra", "/nope"]), blank)
        self.assertEqual(onto_path.explicit_from_argv(["--onto-root="]), {"ONTO": "", "TaxOntOy": None})

    def test_dot_dirname_prefers_the_anchor_directory_over_a_parent_decoy(self):
        marker = onto_path.ONTO_MARKER
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _touch(base / marker, "decoy\n")
            checkout = base / "checkout"
            anchor = _touch(checkout / "onto_path.py", (_REPO / "onto_path.py").read_text(encoding="utf-8"))
            _touch(checkout / marker, "own\n")
            self.assertEqual(onto_path.infer_checkout(".", marker, anchor), checkout.resolve())
            self.assertEqual(onto_path.resolve_root("ONTO", anchor=anchor), checkout.resolve())
            spec = importlib.util.spec_from_file_location("onto_path_default_anchor", anchor)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(module.infer_checkout(".", marker), checkout.resolve())
            self.assertEqual(module.resolve_root("ONTO"), checkout.resolve())

    def test_named_dirname_still_prefers_a_sibling_then_walks_up(self):
        marker = onto_path.ONTO_MARKER
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            project = base / "child"
            _touch(base / "ONTO" / marker, "sibling\n")
            _touch(project / "ONTO" / marker, "nested\n")
            anchor = _touch(project / "tool.py", "")
            self.assertEqual(onto_path.infer_checkout("ONTO", marker, anchor), (base / "ONTO").resolve())
            (base / "ONTO" / marker).unlink()
            self.assertEqual(onto_path.infer_checkout("ONTO", marker, anchor), (project / "ONTO").resolve())
            _touch(base / "parent" / "ONTO" / marker, "ancestor\n")
            deep = _touch(base / "parent" / "vendor" / "app" / "tool.py", "")
            self.assertEqual(
                onto_path.infer_checkout("ONTO", marker, deep),
                (base / "parent" / "ONTO").resolve(),
            )

    def test_blank_env_falls_through_and_tilde_explicit_expands(self):
        marker = onto_path.ONTO_MARKER
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            checkout = home / "checkout"
            _touch(checkout / marker, "home\n")
            anchor = _touch(base / "empty" / "tool.py", "")
            _touch(base / "inferred" / marker, "inferred\n")
            with patch.dict(os.environ, {onto_path.ONTO_ENV: "  \t "}):
                self.assertEqual(
                    onto_path.resolve_root("ONTO", anchor=base / "inferred" / "tool.py"),
                    (base / "inferred").resolve(),
                )
            with patch.dict(os.environ, {"HOME": str(home), onto_path.ONTO_ENV: ""}):
                os.environ.pop(onto_path.ONTO_ENV, None)
                self.assertEqual(
                    onto_path.resolve_root("ONTO", "~/checkout", anchor=anchor),
                    checkout.resolve(),
                )
                self.assertEqual(
                    onto_path.resolve_root("ONTO", Path("~/checkout"), anchor=anchor),
                    checkout.resolve(),
                )

    def test_bind_installs_onto_and_checks_origin(self):
        marker = onto_path.ONTO_MARKER
        table = onto_path.TAXONTOY_MARKER
        name = onto_path.TAXONTOY_DIRNAME
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            checkout = base / "checkout"
            tax = base / name
            _touch(checkout / marker, "marker = True\n")
            _touch(tax / table, "{}\n")
            anchor = _touch(checkout / "tool.py", "")
            saved_module = sys.modules.get("knowledgegraph")
            saved_path = list(sys.path)
            saved_resolved = dict(onto_path.RESOLVED)
            sys.modules.pop("knowledgegraph", None)
            try:
                found = onto_path.bind(anchor, {"ONTO": checkout, "TaxOntOy": tax})
                self.assertEqual(found["ONTO"], checkout.resolve())
                self.assertEqual(found["TaxOntOy"], tax.resolve())
                self.assertEqual(os.environ[onto_path.ONTO_ENV], str(checkout.resolve()))
                self.assertEqual(os.environ[onto_path.TAXONTOY_ENV], str(tax.resolve()))
                self.assertEqual(onto_path.RESOLVED["ONTO"], checkout.resolve())
                self.assertEqual(onto_path.import_roots(), ("ONTO",))
                entry = str(checkout.resolve())
                self.assertEqual(sys.path[0], entry)
                onto_path.install_root(checkout)
                self.assertEqual(sys.path[0], entry)
                self.assertEqual(sys.path.count(entry), 1)
                sys.modules.pop("knowledgegraph", None)
                self.assertEqual(
                    onto_path.verify_origin(checkout, onto_path.ONTO_MODULES, onto_path.ONTO_ENV),
                    checkout.resolve(),
                )
                self.assertEqual(
                    onto_path.verify_origin(checkout, (), onto_path.ONTO_ENV),
                    checkout.resolve(),
                )
                with patch.dict(os.environ, {onto_path.ONTO_ENV: "keep-onto", onto_path.TAXONTOY_ENV: "keep-tax"}):
                    kept = onto_path.bind(anchor, {"ONTO": checkout, "TaxOntOy": tax})
                    self.assertEqual(kept["ONTO"], checkout.resolve())
                    self.assertEqual(os.environ[onto_path.ONTO_ENV], "keep-onto")
                    self.assertEqual(os.environ[onto_path.TAXONTOY_ENV], "keep-tax")
                sys.modules.pop("knowledgegraph", None)
                only_tax = onto_path.bind(anchor, names=("TaxOntOy",))
                self.assertEqual(set(only_tax), {"TaxOntOy"})
                self.assertEqual(only_tax["TaxOntOy"], tax.resolve())
                self.assertNotIn("knowledgegraph", sys.modules)
            finally:
                sys.path[:] = saved_path
                onto_path.RESOLVED.clear()
                onto_path.RESOLVED.update(saved_resolved)
                if saved_module is None:
                    sys.modules.pop("knowledgegraph", None)
                else:
                    sys.modules["knowledgegraph"] = saved_module

    def test_verify_origin_names_a_missing_or_foreign_module(self):
        marker = onto_path.ONTO_MARKER
        with tempfile.TemporaryDirectory() as tmp:
            checkout = Path(tmp) / "checkout"
            _touch(checkout / marker, "marker = True\n")
            saved_module = sys.modules.get("knowledgegraph")
            saved_other = sys.modules.get("other_mod")
            try:
                missing = types.ModuleType("knowledgegraph")
                missing.__file__ = None
                sys.modules["knowledgegraph"] = missing
                with self.assertRaises(onto_path.RootError) as raised:
                    onto_path.verify_origin(checkout, ("knowledgegraph",), onto_path.ONTO_ENV)
                self.assertEqual(
                    str(raised.exception),
                    "モジュールの出どころが不正（knowledgegraph=(なし)）。ONTO_ROOT= を渡す",
                )
                wrong = types.ModuleType("knowledgegraph")
                wrong.__file__ = str(checkout.parent / marker)
                other = types.ModuleType("other_mod")
                other.__file__ = None
                sys.modules["knowledgegraph"] = wrong
                sys.modules["other_mod"] = other
                with self.assertRaises(onto_path.RootError) as raised:
                    onto_path.verify_origin(checkout, ("knowledgegraph", "other_mod"), onto_path.ONTO_ENV)
                message = str(raised.exception)
                self.assertIn(f"knowledgegraph={checkout.parent / marker}", message)
                self.assertIn("other_mod=(なし)", message)
                self.assertIn("ONTO_ROOT= を渡す", message)
            finally:
                if saved_module is None:
                    sys.modules.pop("knowledgegraph", None)
                else:
                    sys.modules["knowledgegraph"] = saved_module
                if saved_other is None:
                    sys.modules.pop("other_mod", None)
                else:
                    sys.modules["other_mod"] = saved_other


if __name__ == "__main__":
    unittest.main()
