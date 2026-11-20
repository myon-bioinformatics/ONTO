"""Compatibility imports for the two top-level ONTO modules."""
import sys

import knowledgegraph
import ontology

__all__ = ["knowledgegraph", "ontology"]
sys.modules[__name__ + ".knowledgegraph"] = knowledgegraph
sys.modules[__name__ + ".ontology"] = ontology
