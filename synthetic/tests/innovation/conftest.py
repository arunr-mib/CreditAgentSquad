"""Fixtures for the innovation book: every client simulated, and every client built."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from synthetic.books.innovation import model
from synthetic.books.innovation.book import ClientBook, build_clients
from synthetic.books.innovation.expected import Series
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
