"""Mutation checks with the product in the loop: tamper with the stand-in reader's answer, run
the live cycle, and record who caught it. About one minute (six borrowers loaded once each,
50 runs of the cycle). Deselect with: -m "not slow".

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
    "bb-aging-note-dropped": "recovered",  # since 2026-11-18 code reads a row's note from the page itself
    "bb-aging-figure-misread": "product",
    "bb-aging-row-dropped": "product and grader",
    "bb-lines-misnamed": "product and grader",
    "intake-misclassified": "product",
    "intake-wrong-period": "product and grader",
    "review-types-a-figure": "product",
    "review-cites-unknown-fact": "product",
    # These seven were accepted silently when the harness was first run (2026-11-17) and named only
    # by the grader. The product now refuses each: a printed label that clearly reads as another
    # line holds the figure for a person, the certificate reader cross-checks units and covenant
    # names, and "audited" needs an auditor's report in the document.
    "spread-rows-swapped-within-a-total": "product",
    "spread-debt-mapped-to-payables": "product",
    "spread-debt-mapped-to-payables-on-a-breach": "product and grader",
    "spread-term-debt-mapped-to-other-liabilities-on-a-breach": "product and grader",
    "cert-units-omitted": "product",
    "cert-rows-swapped": "product",
    "intake-statements-called-audited": "product",
    # Found by the independent review on 2026-11-17: each of these was accepted, and the first
    # four turned a real breach into a pass with nothing raised. The row label is now read from
    # the page by code and must be a known name for the line; a column header must name one
    # period; and a statement's printed totals must be read.
    "spread-term-debt-swapped-with-label-fragments": "product and grader",
    "spread-term-debt-folded-into-other-liabilities": "product and grader",
    "spread-principal-read-from-another-supplemental-row": "product and grader",
    "spread-cash-taxes-read-from-another-supplemental-row": "product and grader",
    "spread-prior-year-under-a-spanning-header": "product",
    "spread-printed-totals-not-read": "product",
    # Found by the second independent review on 2026-11-17 (the page-layout attacks from that
    # review need their own PDFs and live in backend/tests/agents/test_spreading_layouts.py).
    "spread-supplemental-row-reported-twice": "product",
    "cert-flag-from-the-next-row": "product",
    "review-figure-dressed-as-a-date": "product",
    "review-figure-as-a-list-marker": "product",
    "review-quantity-in-words": "product",
    "review-figure-as-an-identifier": "product",
    "review-figure-as-a-note-number": "product",
    # Found by the third independent review on 2026-11-18: the borrowing base reader took a row's
    # category, its notes and which certificate line it was from the reader, and compared only
    # the certificate lines the reader chose to report.
    "bb-ineligible-inventory-named-by-a-fragment": "product",
    "bb-receivable-filed-as-inventory": "product and grader",
    "bb-affiliate-note-and-lines-dropped": "product",
    "bb-contra-note-and-lines-dropped": "product",
    "bb-letters-of-credit-from-an-empty-row": "product",
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
    assert outcomes["spread-wrong-figure"]["new_work_items"] == ["spread.value_unverified"]  # footing is asked once the held figure is cleared
    assert "spread.value_unverified" in outcomes["spread-prior-year-figure"]["new_work_items"]
    assert outcomes["spread-dropped-line"]["new_work_items"] == ["spread.does_not_foot"]
    assert ["spreading", "scale_conflict", "person"] in outcomes["spread-units-omitted"]["new_guardrail_notes"]
    assert outcomes["cert-claims-compliance"]["new_work_items"] == ["spread.value_unverified"]
    assert outcomes["cert-misread-threshold"]["new_work_items"] == ["spread.value_unverified"]
    # and none of them left a wrong number behind as a usable fact
    for name in ("spread-wrong-figure", "spread-prior-year-figure", "spread-dropped-line", "spread-units-omitted",
                 "cert-claims-compliance", "cert-misread-threshold"):
        assert "invented-number" not in outcomes[name]["grader_names"], name


def test_nothing_is_left_for_the_grader_alone(outcomes):
    """A tampering that only the grader names is a gap in the product. There are none today."""
    assert [n for n, o in outcomes.items() if o["caught_by"] == "grader"] == []


def test_a_mis_mapped_debt_row_can_no_longer_hide_a_breach(outcomes):
    """Long-term debt reported under 'other liabilities' foots and verifies on the page, and used
    to lower leverage below its limit so the breach vanished. The label now reads as another
    line, so the figure is held for a person, no total is computed and no covenant is recorded
    compliant. The grader still notes that the expected breach item was not reached: the cycle
    rests at spreading until a person clears the figure."""
    outcome = outcomes["spread-term-debt-mapped-to-other-liabilities-on-a-breach"]
    assert "spread.value_unverified" in outcome["new_work_items"] and outcome["product"] is True
    assert "false-compliant" not in outcome["grader_names"]
    assert "invented-number" not in outcome["grader_names"]
