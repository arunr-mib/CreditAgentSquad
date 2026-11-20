"""Fixtures for the innovation book: clients simulated, clients built, and one full generation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from synthetic.books.innovation import model
from synthetic.books.innovation.book import ClientBook, build_clients
from synthetic.books.innovation.expected import Series
from synthetic.books.innovation.generate import generate
from synthetic.books.innovation.roster import CLIENTS, ClientSpec


@dataclass
class Sim:
    """One client simulated, with nothing else built."""

    spec: ClientSpec
    opening: model.Month
    months: list[model.Month]
    periods: list[model.Period]
    series: Series


@pytest.fixture(scope="session")
def sims() -> dict[str, Sim]:
    out = {}
    for spec in CLIENTS:
        opening, months = model.simulate(spec)
        out[spec.id] = Sim(spec, opening, months, model.build_periods(months), Series(months))
    return out


@pytest.fixture(scope="session")
def clients() -> dict[str, ClientBook]:
    return {book.spec.id: book for book in build_clients()}


@dataclass
class Generated:
    out: Path
    oracle: Path
    manifest: dict
    truths: dict[str, dict]

    def text(self, document_id: str) -> list[str]:
        from synthetic.render import common

        doc = next(d for d in self.manifest["documents"] if d["id"] == document_id)
        return common.page_texts(self.out / doc["path"])


@pytest.fixture(scope="session")
def generated(tmp_path_factory) -> Generated:
    root = tmp_path_factory.mktemp("innovation-book")
    out = root / "out"
    manifest = generate(out, oracle=root / "oracle.csv")
    truths = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted((out / "truth").glob("*.json"))}
    return Generated(out, root / "oracle.csv", manifest, truths)
