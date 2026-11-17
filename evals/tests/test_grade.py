"""The grader is not asleep: tamper with a recording of a real run and each named failure is
raised by name. The recordings come from four borrowers run through the live cycle with the
stand-in reader (about 25 seconds, once per session)."""
import copy

import pytest

from evals.grade import FAILURES, _ratio, evaluate_gate, grade_borrower, grade_pass, typed_figures


def names(graded):
    return {f["name"] for f in graded["failures"]}


def graded_after(small, code, change):
    book, recordings = small
    recording = copy.deepcopy(recordings[code])
    change(recording)
    return grade_borrower(book.get(code), recording)


def fact(recording, key):
    return next(f for f in recording["facts"] if f["key"] == key and f["status"] == "verified")


def test_of(recording, covenant_id):
    return next(t for t in recording["covenant_tests"] if t["covenant_id"] == covenant_id)


def test_untampered_recordings_grade_clean(small):
    book, recordings = small
    for code, recording in recordings.items():
        graded = grade_borrower(book.get(code), recording)
        assert graded["failures"] == [] and graded["disagreements"] == [], code
        assert graded["extraction"]["correct"] == graded["extraction"]["expected"], code
    clean = grade_borrower(book.get("harrowgate-precision"), recordings["harrowgate-precision"])
    assert clean["needs_no_person"] is True and clean["cycle_status"] == "closed"
    assert clean["routine_approvals"] == ["review.commentary_approval"] and clean["raised_exceptions"] == []


def test_invented_number_a_stored_fact_that_differs_from_the_truth(small):
    def change(rec):
        fact(rec, "is.revenue")["value"] = "74119000.000000"
    graded = graded_after(small, "harrowgate-precision", change)
    assert [(f["name"], f["item"]) for f in graded["failures"]] == [("invented-number", "is.revenue @ 2026-09-30")]
    assert graded["extraction"]["wrong"] == 1 and graded["extraction"]["accuracy"] < 1


def test_invented_number_a_covenant_value_with_no_fact_behind_it(small):
    def change(rec):
        test_of(rec, "fccr")["value_fact_id"] = None
    assert "invented-number" in names(graded_after(small, "harrowgate-precision", change))


def test_invented_number_a_calculated_fact_that_differs_from_the_truth(small):
    def change(rec):
        fact(rec, "cov.total_leverage.value")["value"] = "1.790000"
    assert "invented-number" in names(graded_after(small, "harrowgate-precision", change))


def test_invented_number_commentary_that_types_a_figure_or_cites_a_fact_that_does_not_exist(small):
    def typed(rec):
        rec["review"]["commentary"][0]["body"] += " Net sales were 74,118."

    def unknown(rec):
        rec["review"]["commentary"][0]["body"] += " See {{fact:00000000-0000-4000-8000-000000000000}}."

    for change in (typed, unknown):
        graded = graded_after(small, "harrowgate-precision", change)
        assert names(graded) == {"invented-number"}, graded["failures"]


def test_false_compliant(small):
    def change(rec):
        test = test_of(rec, "total_leverage")
        test["outcome"], test["passed"] = "compliant", True
    graded = graded_after(small, "kestrel-bay-packaging", change)
    assert "false-compliant" in names(graded)


def test_false_breach(small):
    def change(rec):
        test = test_of(rec, "fccr")
        test["outcome"], test["passed"] = "breach", False
    assert "false-breach" in names(graded_after(small, "harrowgate-precision", change))


def test_missed_exception(small):
    def change(rec):
        rec["work_items"] = [w for w in rec["work_items"] if w["type"] != "covenant.reported_mismatch"]
    graded = graded_after(small, "kestrel-bay-packaging", change)
    assert [(f["name"], f["item"]) for f in graded["failures"]] == [("missed-exception", "covenant.reported_mismatch")]


def test_false_exception(small):
    def change(rec):
        extra = copy.deepcopy(rec["work_items"][0])
        extra.update({"type": "spread.value_unverified", "title": "a figure could not be verified"})
        rec["work_items"].append(extra)
    graded = graded_after(small, "harrowgate-precision", change)
    assert [(f["name"], f["item"]) for f in graded["failures"]] == [("false-exception", "spread.value_unverified")]
    assert graded["needs_no_person"] is False


def test_wrong_citation(small):
    def wrong_page(rec):
        fact(rec, "is.revenue")["page"] = 2  # the balance sheet page does not print net sales

    def wrong_quote(rec):
        fact(rec, "bs.cash")["quote"] = "3,028"

    for change in (wrong_page, wrong_quote):
        assert names(graded_after(small, "harrowgate-precision", change)) == {"wrong-citation"}


def test_wrong_abstain(small):
    def cannot(rec):
        test = test_of(rec, "fccr")
        test.update({"outcome": "cannot_test", "value": None, "passed": None, "error": "missing input"})

    def no_test(rec):
        rec["covenant_tests"] = [t for t in rec["covenant_tests"] if t["covenant_id"] != "fccr"]

    def failed_run(rec):
        rec["agent_runs"][0].update({"status": "failed", "error": "RecordingMissing"})

    for change in (cannot, no_test, failed_run):
        assert "wrong-abstain" in names(graded_after(small, "harrowgate-precision", change))


def test_missed_abstain(small):
    book, recordings = small

    def tested_anyway(rec):
        donor = copy.deepcopy(recordings["harrowgate-precision"]["covenant_tests"][0])
        donor["covenant_id"] = next(iter(t["covenant_id"] for t in book.get("ashgrove-fleet").expected_tests(
            book.get("ashgrove-fleet").current_period)))
        rec["covenant_tests"].append(donor)

    def read_the_missing_page(rec):
        donor = copy.deepcopy(fact(rec, "bs.cash"))
        truth = book.get("ashgrove-fleet").period(book.get("ashgrove-fleet").current_period)["values"]
        donor.update({"key": "bs.accounts_payable", "value": truth["bs.accounts_payable"]})
        rec["facts"].append(donor)

    for change in (tested_anyway, read_the_missing_page):
        assert "missed-abstain" in names(graded_after(small, "ashgrove-fleet", change))


def test_stale_terms(small):
    def version(rec):
        test_of(rec, "fccr")["terms_version"] = 2

    def proposed(rec):
        test_of(rec, "fccr")["terms_status"] = "proposed"

    def threshold(rec):
        test_of(rec, "fccr")["threshold"] = "1.250000"

    for change in (version, proposed, threshold):
        assert "stale-terms" in names(graded_after(small, "harrowgate-precision", change))


def test_disagreements_without_a_name_are_still_reported(small):
    def signal(rec):
        rec["signals"].append({"rule_id": "net_loss", "severity": "high", "basis": {}, "explanation": None})

    def base_line(rec):
        rec["borrowing_base"][0]["computed"]["ar_eligible"] = "1"

    def filing(rec):
        rec["documents"][0]["quality"] = "audited" if "ifs" in rec["documents"][0]["file_name"] else rec["documents"][0]["quality"]
        rec["documents"][0]["period_end"] = "2026-06-30"

    for change, kind in ((signal, "signal-unexpected"), (base_line, "borrowing-base-line"), (filing, "document-filing")):
        graded = graded_after(small, "harrowgate-precision", change)
        assert kind in {d["kind"] for d in graded["disagreements"]} and graded["failures"] == []


def test_a_crashed_run_is_never_a_pass(small):
    book, _ = small
    graded = grade_borrower(book.get("harrowgate-precision"), {"borrower": "harrowgate-precision", "error": "boom"})
    assert graded["disagreements"][0]["kind"] == "run-error" and graded["needs_no_person"] is None
    assert graded["extraction"]["correct"] == 0 and graded["extraction"]["expected"] > 100


def test_the_gate_checks_every_pass_separately(small):
    book, recordings = small
    clean = grade_pass(book, recordings)
    bad = copy.deepcopy(recordings)
    test = test_of(bad["kestrel-bay-packaging"], "total_leverage")
    test["outcome"], test["passed"] = "compliant", True
    failing = grade_pass(book, bad)
    assert evaluate_gate([clean], mode="standin", complete_book=False)["passed"]
    for mode in ("standin", "recorded", "live"):
        # a failure in the second pass must not hide behind a clean first pass
        gate = evaluate_gate([clean, failing], mode=mode, complete_book=False)
        assert not gate["passed"] and any("pass 2" in r and "false-compliant" in r for r in gate["reasons"])


def test_a_live_run_is_gated_on_the_two_failures_only_and_its_accuracy_is_reported_not_gated(small):
    book, recordings = small
    worse = copy.deepcopy(recordings)
    worse["harrowgate-precision"]["facts"] = [f for f in worse["harrowgate-precision"]["facts"] if f["key"] != "bs.cash"]
    graded = grade_pass(book, worse)
    assert graded["metrics"]["extraction_accuracy"] < 1
    assert evaluate_gate([graded], mode="live")["passed"]
    assert not evaluate_gate([graded], mode="standin", complete_book=False)["passed"]


def test_a_known_finding_excuses_only_itself_and_never_a_gated_failure(small):
    book, recordings = small
    tampered = copy.deepcopy(recordings)
    extra = copy.deepcopy(tampered["harrowgate-precision"]["work_items"][0])
    extra["type"] = "spread.value_unverified"
    tampered["harrowgate-precision"]["work_items"].append(extra)
    graded = grade_pass(book, tampered)
    listed = [{"borrower": "harrowgate-precision", "name": "false-exception", "item": "spread.value_unverified",
               "cause": "test"}]
    assert not evaluate_gate([graded], mode="standin", complete_book=False)["passed"]
    assert evaluate_gate([graded], mode="standin", known=listed, complete_book=False)["passed"]
    # a listed finding that no longer occurs fails the gate until it is removed
    stale = evaluate_gate([grade_pass(book, recordings)], mode="standin", known=listed)
    assert not stale["passed"] and stale["stale_known_findings"]
    # the two gated failures cannot be listed away
    fact(tampered["harrowgate-precision"], "is.revenue")["value"] = "1.000000"
    invented = [{"borrower": "harrowgate-precision", "name": "invented-number", "item": "is.revenue @ 2026-09-30"}]
    assert not evaluate_gate([grade_pass(book, tampered)], mode="standin", known=listed + invented,
                             complete_book=False)["passed"]


def test_metrics_cover_every_named_failure_and_leave_the_unmeasured_null(small):
    book, recordings = small
    graded = grade_pass(book, recordings)
    assert set(graded["failure_counts"]) == set(FAILURES) and not any(graded["failure_counts"].values())
    metrics = graded["metrics"]
    assert metrics["extraction_accuracy"] == 1 and metrics["covenant_outcome_accuracy"] == 1
    assert metrics["exception_precision"] == 1 and metrics["exception_recall"] == 1
    assert metrics["cycles_needing_no_person"] == 0.25  # only the clean borrower of the four
    assert metrics["input_tokens"] is None and metrics["output_tokens"] is None
    assert _ratio(0, 0) is None and _ratio(0, 4) == 0


@pytest.mark.parametrize("text", [
    "Net sales were 74,118 for the period.", "Leverage is 3.25x.", "Margin fell 4%.", "Past due 12 days.",
    "A charge of (1,200) was taken.", "Availability of $2.9m remains."])
def test_a_typed_figure_is_seen(text):
    assert typed_figures(text)


@pytest.mark.parametrize("text", [
    "Leverage was {{fact:0197da74-ad1e-436b-b68a-ca9c3f6e3133}} against {{fact:299c3f0e-a248-4898-83e0-146c76749b3f|ratio}}.",
    "For the period ended September 30, 2026, compared with 2025.", "Results for Q3 2026 and FY2025 are set out below.",
    "See Section 6.1 of the agreement dated 2022-03-18.", "No figures here."])
def test_dates_quarters_references_and_fact_ids_are_not_figures(text):
    assert typed_figures(text) == []
