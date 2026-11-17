"""Mutation checks with the product in the loop: tamper with the stand-in reader's answer, run
the live cycle, and record who caught it. About one minute (three borrowers loaded once each,
28 runs of the cycle). Deselect with: -m "not slow".

EXPECTED is what each mutation was seen to do on 2026-11-17. `product` means the product refused
the tampered item into a work item or a guardrail note. `grader` means the product accepted it
and only the grader named the failure: those are findings about the product (see
evals/README.md). Nothing slips through both.
"""
import pytest

from evals.book import load_book
from evals.mutations import MUTATIONS, run_mutations

pytestmark = pytest.mark.slow

EXPECTED = {
    # the brief's six: a wrong figure that still parses, a figure from the prior-year column, a
    # dropped line, a wrong units phrase, a certificate that claims compliance, a misread threshold
    "spread-wrong-figure": "product",
    "spread-prior-year-figure": "product",
    "spread-dropped-line": "product",
    "spread-units-omitted": "product",
    "cert-claims-compliance": "product",
    "cert-misread-threshold": "product",
    # further ways to be wrong
    "spread-figure-from-another-row": "product",
    "spread-whole-prior-year-column": "product",
    "spread-dropped-line-and-totals": "product",
    "spread-dropped-supplemental-line": "product",
    "spread-units-invented": "product",
    "spread-note-types-a-figure": "product",
    "cert-breach-read-as-passing-value": "product",
    "cert-threshold-from-another-row": "product",
    "bb-aging-note-dropped": "product and grader",
    "bb-aging-figure-misread": "product",
    "bb-aging-row-dropped": "product and grader",
    "bb-lines-misnamed": "product and grader",
    "intake-misclassified": "product",
    "intake-wrong-period": "product and grader",
    "review-types-a-figure": "product",
    "review-cites-unknown-fact": "product",
    # accepted by the product, named only by the grader: findings about the product
    "spread-rows-swapped-within-a-total": "grader",
    "spread-debt-mapped-to-payables": "grader",
    "spread-debt-mapped-to-payables-on-a-breach": "grader",
    "cert-units-omitted": "grader",
    "cert-rows-swapped": "grader",
    "intake-statements-called-audited": "grader",
}


@pytest.fixture(scope="module")
def outcomes(engine, book_root, file_store):
    book = load_book(book_root, sorted({m.borrower for m in MUTATIONS}))
    return {o["name"]: o for o in run_mutations(engine, book)}


def test_every_mutation_has_a_recorded_expectation():
    assert {m.name for m in MUTATIONS} == set(EXPECTED)


def test_every_tampered_answer_reached_the_product(outcomes):
    assert [n for n, o in outcomes.items() if not o["applied"] or o["error"]] == []


def test_nothing_slips_through_both_the_product_and_the_grader(outcomes):
    assert [n for n, o in outcomes.items() if o["caught_by"] == "SLIPPED"] == []


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_mutation_is_caught_where_expected(outcomes, name):
    assert outcomes[name]["caught_by"] == EXPECTED[name], outcomes[name]["evidence"]


def test_the_six_named_in_the_brief_are_refused_by_the_product_itself(outcomes):
    assert outcomes["spread-wrong-figure"]["new_work_items"] == ["spread.does_not_foot", "spread.value_unverified"]
    assert "spread.value_unverified" in outcomes["spread-prior-year-figure"]["new_work_items"]
    assert outcomes["spread-dropped-line"]["new_work_items"] == ["spread.does_not_foot"]
    assert ["spreading", "scale_conflict", "person"] in outcomes["spread-units-omitted"]["new_guardrail_notes"]
    assert outcomes["cert-claims-compliance"]["new_work_items"] == ["spread.value_unverified"]
    assert outcomes["cert-misread-threshold"]["new_work_items"] == ["spread.value_unverified"]
    # and none of them left a wrong number behind as a usable fact
    for name in ("spread-wrong-figure", "spread-prior-year-figure", "spread-dropped-line", "spread-units-omitted",
                 "cert-claims-compliance", "cert-misread-threshold"):
        assert "invented-number" not in outcomes[name]["grader_names"], name


def test_what_only_the_grader_catches_is_caught_by_name(outcomes):
    for name in ("spread-rows-swapped-within-a-total", "spread-debt-mapped-to-payables", "cert-units-omitted",
                 "cert-rows-swapped"):
        assert "invented-number" in outcomes[name]["grader_names"], name
        assert outcomes[name]["new_work_items"] == [], name
    assert outcomes["intake-statements-called-audited"]["grader_names"] == ["document-filing"]
