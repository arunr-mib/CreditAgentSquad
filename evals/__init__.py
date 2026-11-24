"""Evaluation harness for Credit Agent Squad: run the live monitoring cycle over the synthetic
book, grade the outcome with deterministic code, and gate on the failures that must never happen."""
import sys
from pathlib import Path

# `python -m evals.run` is started from the repository root, where the product package (`app`)
# is not on the path; pytest adds it through pyproject.toml.
_BACKEND = str(Path(__file__).resolve().parents[1] / "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)
