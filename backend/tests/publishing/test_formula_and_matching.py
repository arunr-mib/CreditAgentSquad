"""The workbook formula evaluator and the rule that matches a printed figure to a fact. Each rule
has a test for what it must accept and what it must refuse."""
from decimal import Decimal as D

import pytest
from app.guardrails.numbers import extract_figures
from app.publishing.formula import FormulaError, evaluate, references
from app.publishing.style import display
from app.publishing.verify import figure_matches, figures_in

CELLS = {("S", "B5"): D(10), ("S", "B6"): D(4), ("Income statement", "AB12"): D(3), ("S", "C1"): D("2.125"),
         ("S", "C2"): D("-2.125")}


def cell(sheet, address):
    return CELLS.get((sheet, address))


def test_arithmetic_references_and_functions():
    assert evaluate("=B5-B6", "S", cell) == D(6)
    assert evaluate("=(B5-B6)/'Income statement'!AB12", "S", cell) == D(2)
    assert evaluate("=SUM(B5:B6,1)*-2", "S", cell) == D(-30)
    assert evaluate("=ABS(B6-B5)+365*B5/B6", "S", cell) == D("918.5")
    assert references("=B5+'Income statement'!$AB$12", "S") == [("S", "B5"), ("Income statement", "AB12")]


def test_round_is_half_up_like_the_calculation_engine():
    assert evaluate("=ROUND(C1,2)", "S", cell) == D("2.13")
    assert evaluate("=ROUND(C2,2)", "S", cell) == D("-2.13")
    assert evaluate("=ROUND(B5/'Income statement'!AB12,4)", "S", cell) == D("3.3333")


def test_an_empty_cell_is_an_error_never_zero():
    with pytest.raises(FormulaError, match="is empty"):
        evaluate("=B5+B7", "S", cell)
    with pytest.raises(FormulaError):
        evaluate("=B5/(B6-B6)", "S", cell)
    with pytest.raises(FormulaError):
        evaluate("=VLOOKUP(B5,B5:B6,1)", "S", cell)


def record(value, unit):
    return {"id": "f", "value": value, "unit": unit, "label": "x"}


def one(text):
    (figure,) = extract_figures(text)
    return figure


@pytest.mark.parametrize("value,unit,fmt", [
    ("33114000", "usd", None), ("-81949", "usd", None), ("33114000", "usd", "plain_usd"), ("-81949", "usd", "plain_usd"),
    ("2.60", "ratio", None), ("0.0719", "pct", None), ("-0.04", "pct", None), ("0.0275", "pct", "pct2"),
    ("47.4", "days", "days1"), ("128060000", "usd", "usd_m"), ("6", "count", None),
])
def test_a_figure_printed_from_a_fact_matches_that_fact(value, unit, fmt):
    assert figure_matches(one(display(record(value, unit), fmt)), record(value, unit))


@pytest.mark.parametrize("printed,value", [
    ("2.40x", "2.60"), ("33,114,001", "33114000"), ("(81,949)", "81949"), ("7.3%", "0.0719"), ("$129.1 million", "128060000"),
    ("7", "6"),
])
def test_a_changed_figure_does_not_match(printed, value):
    assert not figure_matches(one(printed), record(value, "usd"))


def test_dates_ids_and_hashes_are_not_figures_but_a_bare_number_is():
    assert figures_in("Period ended 30 Sep 2026. Snapshot sha256 " + "5a" * 32) == []
    assert figures_in("fact 3f9a2b10-0000-4000-8000-000000000009, as of 2026-09-30") == []
    assert [f.raw for f in figures_in("Leverage improved to 1.90x")] == ["1.90x"]
