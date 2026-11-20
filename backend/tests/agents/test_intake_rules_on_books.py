"""The intake rules classify the first page of every generated document, in both books, as the truth says."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.agents.intake import rule_type

from synthetic.render import common

ROOT = Path(__file__).resolve().parents[3] / "synthetic"
BOOKS = (ROOT / "out", ROOT / "books" / "innovation" / "out")
RULE_NAME = {"annual_financial_statements": "annual_statements", "interim_financial_statements": "interim_statements"}


def _docs():
    for out in BOOKS:
        manifest = json.loads((out / "manifest.json").read_text())
        for doc in manifest["documents"]:
            path = out / doc["path"]
            if path.suffix == ".pdf" and path.exists():
                yield out, doc, path


@pytest.mark.parametrize("out", BOOKS, ids=lambda p: str(p.relative_to(ROOT)))
def test_rule_type_agrees_with_the_truth_on_every_first_page(out):
    docs = [(d, p) for o, d, p in _docs() if o == out]
    if not docs:
        pytest.skip(f"{out} has no generated PDFs; run the generator")
    wrong = []
    for doc, path in docs:
        expected = None if doc["type"] == "unclassified" else RULE_NAME.get(doc["type"], doc["type"])
        got = rule_type(common.page_texts(path)[0])
        if got != expected:
            wrong.append((doc["id"], doc["type"], got))
    assert not wrong, wrong[:10]
