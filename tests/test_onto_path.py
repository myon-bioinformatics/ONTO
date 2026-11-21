"""Resolution order, markers, and errors for the canonical onto_path.py."""
import os
import sys
import tempfile
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


if __name__ == "__main__":
    unittest.main()
