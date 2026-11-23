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
    # time) and the signal the book expects. The certificate item for the Revenue to Plan row is
    # gone now that percentages are stored as fractions and the wrapped row is cited by its own label;
    # a change here is a finding
    assert set(types) == {"funding_slipped", "signal.high"}


@pytest.fixture(scope="module")
def ferrogate(engine, file_store):
    return _record(engine, "ferrogate-cloud")


def _with_runway(rec, **changes):
    """The recording with a runway test row added. Built to match what the product records for a
    cash-flow-positive period, so the runway grading is exercised without a second full cycle."""
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


def test_a_wrong_certificate_figure_stored_for_a_held_figure_borrower_is_an_invented_number(engine, file_store):
    """Cindrel rests at spreading, so no certificate fact is expected; one stored anyway is still graded."""
    book = load_book(BOOKS["innovation"], ["cindrel-tech"])
    borrower = book.get("cindrel-tech")
    with LoadedBorrower(engine, book, borrower) as loaded:
        recording = loaded.run(lambda: StandInReader(book), decide=True)
    clean = grade_borrower(borrower, recording)
    assert clean["failures"] == [] and clean["disagreements"] == []
    tampered = copy.deepcopy(recording)
    donor = next(f for f in tampered["facts"] if f["status"] == "verified" and f["kind"] == "extracted")
    from evals.grade import Truth
    truth = Truth(borrower)
    key = next(k for k in truth.expected_facts(every_figure=True) if k.endswith(".value") and k.startswith("cert."))
    tampered["facts"].append({**donor, "key": key, "period_end": truth.end.isoformat(), "value": "123456789.000000"})
    graded = grade_borrower(borrower, tampered)
    assert [f["name"] for f in graded["failures"]] == ["invented-number"] and graded["failures"][0]["item"].startswith("cert.")
