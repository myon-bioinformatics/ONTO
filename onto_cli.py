"""Console launcher for ONTO and its explicitly versioned tool routes."""

import argparse
import json
import shutil
import subprocess
import sys


_OTL_URL = "https://github.com/myon-bioinformatics/OnTautoLogy.git"
_OTL_COMMIT = "2c0d12bdcb80258c261bf13849728b9a6891bde3"


def _otl(args):
    uv = shutil.which("uv")
    if uv is None:
        print("onto otl requires uv: https://docs.astral.sh/uv/", file=sys.stderr)
        return 127
    source = f"git+{_OTL_URL}@{_OTL_COMMIT}"
    if args[:1] == ["exchange"] or (args[:1] == ["entails"] and "--ttl" in args):
        source = f"ontautology[exchange] @ {source}"
    # Keep the process environment, including UV_OFFLINE, and leave all
    # standard streams attached to the caller.
    return subprocess.run(
        [uv, "tool", "run", "--from", source, "ontautology", *args], check=False
    ).returncode


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["exchange"]:
        import ontology

        try:
            return ontology.main(args[1:], prog="onto exchange")
        except ModuleNotFoundError as exc:
            if exc.name not in {"rdflib", "neo4j"}:
                raise
            print(f"Install onto-shared[exchange] to use this route (missing {exc.name}).", file=sys.stderr)
            return 1
    if args[:1] == ["otl"]:
        return _otl(args[1:])
    parser = argparse.ArgumentParser(prog="onto", description="Run ONTO graph tools and its pinned OTL route.")
    routes = parser.add_subparsers(dest="route", required=True)
    routes.add_parser("exchange", help="import, export, or query RDF")
    routes.add_parser("otl", help="run the standalone OnTautoLogy CLI")
    versions = routes.add_parser("versions", help="report the standalone child source pin")
    versions.add_argument("--json", action="store_true",help="print JSON instead of text")
    if not args:
        parser.print_help()
        return 0
    result = parser.parse_args(args)
    if result.json:
        print(json.dumps({"otl": {"repository": _OTL_URL, "commit": _OTL_COMMIT}}))
    else:
        print(f"otl {_OTL_URL}@{_OTL_COMMIT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
