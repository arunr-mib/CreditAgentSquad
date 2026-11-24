"""The intake rules classify the first page of every generated document, in both books, as the truth says.

The PDFs are generated into a session fixture, so the test never depends on a folder that may be absent."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from app.agents.intake import rule_type

from synthetic.render import common

REPO = Path(__file__).resolve().parents[3]
RULE_NAME = {"annual_financial_statements": "annual_statements", "interim_financial_statements": "interim_statements"}
GENERATORS = (("legacy", "synthetic.generate"), ("innovation", "synthetic.books.innovation.generate"))


@pytest.fixture(scope="session")
def books(tmp_path_factory):
    roots = {}
    for name, module in GENERATORS:
        out = tmp_path_factory.mktemp(name) / "out"
        subprocess.run([sys.executable, "-m", module, "--out", str(out), "--oracle", str(out.parent / "oracle.csv")]
                       if name == "innovation" else [sys.executable, "-m", module, "--out", str(out)],
                       cwd=REPO, check=True, capture_output=True)
        roots[name] = out
    return roots


@pytest.mark.parametrize("name", [n for n, _ in GENERATORS])
def test_rule_type_agrees_with_the_truth_on_every_first_page(books, name):
    out = books[name]
    manifest = json.loads((out / "manifest.json").read_text())
    docs = [(d, out / d["path"]) for d in manifest["documents"] if d["path"].endswith(".pdf")]
    assert docs and all(p.exists() for _, p in docs), f"{name} generated no PDFs"
    wrong = []
    for doc, path in docs:
        expected = None if doc["type"] == "unclassified" else RULE_NAME.get(doc["type"], doc["type"])
        got = rule_type(common.page_texts(path)[0])
        if got != expected:
            wrong.append((doc["id"], doc["type"], got))
    assert not wrong, wrong[:10]
