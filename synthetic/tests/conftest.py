"""Shared fixtures: the in-memory book, and one full generation into a temporary directory."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from synthetic.book import BorrowerBook, build_book
from synthetic.generate import generate


@dataclass
class Generated:
    out: Path
    oracle: Path
    manifest: dict
    truths: dict[str, dict]


@pytest.fixture(scope="session")
def books() -> list[BorrowerBook]:
    return build_book()


@pytest.fixture(scope="session")
def generated(tmp_path_factory) -> Generated:
    root = tmp_path_factory.mktemp("book")
    out = root / "out"
    manifest = generate(out)
    truths = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted((out / "truth").glob("*.json"))}
    return Generated(out, root / "oracle.csv", manifest, truths)
