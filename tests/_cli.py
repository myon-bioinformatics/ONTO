"""Load the test-only CLI runner without changing the installed package's import path."""
import importlib.util
import sys
from pathlib import Path

_path = Path(__file__).resolve().parents[1] / "vendor" / "cli_args.py"
_spec = importlib.util.spec_from_file_location("_onto_test_cli_args", _path)
_module = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _module
_spec.loader.exec_module(_module)
run_cli = _module.run_cli
