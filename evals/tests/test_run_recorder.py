import copy

import pytest

from evals.book import BOOKS, load_book
from evals.grade import grade_borrower
from evals.run import LoadedBorrower
from evals.standin import StandInReader


def _record(engine, code):
    book = load_book(BOOKS["innovation"], [code])
    borrower = book.get(code)
    with LoadedBorrower(engine, book, borrower) as loaded:
        return borrower, loaded.run(lambda: StandInReader(book), decide=False)


def test_a_funding_item_raised_at_seed_time_reaches_the_recording(engine, file_store):
    _, recording = _record(engine, "nimbusfield-security")
    types = [w["type"] for w in recording["work_items"]]
    assert types.count("funding_slipped") == 1
    # exactly what the stand-in cycle raises today: the funding item (the product's own, at seed
    # time), the signal the book expects, and a certificate item for the Revenue to Plan row (the
    # product stores a percentage as printed and cannot cite the wrapped row: Task 9's to fix);
    # a change here is a finding
    assert set(types) == {"funding_slipped", "signal.high", "spread.value_unverified"}


@pytest.fixture(scope="module")
def ferrogate(engine, file_store):
    return _record(engine, "ferrogate-cloud")


def _with_runway(rec, **changes):
    """The recording with a runway test row added. The stand-in cannot yet get an innovation borrower
    past spreading (a Task 3 matter), so no real run records a covenant test; the row is built to match
    what the product records for a cash-flow-positive period."""
    out = copy.deepcopy(rec)
    want = next(t for t in ferrogate_truth().expected_tests(ferrogate_truth().current_period)
                if t["covenant_id"] == "min_runway_months")
    out["covenant_tests"] = [{
        "covenant_id": "min_runway_months", "period_end": rec["period_end"], "value": None, "threshold": want["threshold"],
        "operator": ">=", "unit": "months", "passed": True, "outcome": "compliant", "note": want["note"],
        "reported_value": None, "reported_in_compliance": True, "error": None,
        "terms_version": want["terms_version"], "terms_status": "approved",
        "value_fact_id": None, "reported_fact_id": None, **changes}]
    return out


def ferrogate_truth():
    return load_book(BOOKS["innovation"], ["ferrogate-cloud"]).get("ferrogate-cloud")


def _failures(borrower, rec):
    return {f["name"] for f in grade_borrower(borrower, rec)["failures"] if f["item"].startswith("min_runway_months")}


def test_a_not_meaningful_runway_with_its_note_grades_clean(ferrogate):
    borrower, rec = ferrogate
    assert _failures(borrower, _with_runway(rec)) == set()


def test_a_figure_recorded_for_a_not_meaningful_runway_is_an_invented_number(ferrogate):
    borrower, rec = ferrogate
    for changes in ({"value": "9.5"}, {"reported_value": "9.5"}):
        assert "invented-number" in _failures(borrower, _with_runway(rec, **changes)), changes
    tampered = _with_runway(rec)
    tampered["facts"] = [*tampered["facts"], {"key": "cert.min_runway_months.value", "value": "9.5",
                                              "period_end": rec["period_end"], "status": "verified",
                                              "kind": "computed", "document": None, "page": None,
                                              "quote": None, "label": None, "id": "f-x"}]
    assert "invented-number" in _failures(borrower, tampered)


def test_a_wrong_note_is_a_covenant_outcome_disagreement(ferrogate):
    borrower, rec = ferrogate
    graded = grade_borrower(borrower, _with_runway(rec, note=None))
    assert any(d["kind"] == "covenant-outcome" and d["item"].startswith("min_runway_months")
               for d in graded["disagreements"])
