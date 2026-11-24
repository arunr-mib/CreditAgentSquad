"""Every scenario of design spec section 10 makes the book say what it should, and the generator checks itself."""

from __future__ import annotations

from datetime import date
from decimal import Decimal as D

import pytest

from synthetic.books.innovation import model, reports
from synthetic.books.innovation.book import verify
from synthetic.books.innovation.expected import q
from synthetic.books.innovation.roster import AS_OF, CURRENT_PERIOD, SCENARIOS

LAST = model.LAST


def exceptions(book) -> list[str]:
    return sorted(e["type"] for e in book.expected["exceptions"])


def current(book) -> dict[str, dict]:
    return {r["covenant_id"]: r for r in book.expected["covenant_tests"] if r["period_end"] == CURRENT_PERIOD}


def current_signals(book) -> list[dict]:
    return [s for s in book.expected["signals"] if s["period_end"] == CURRENT_PERIOD]


def test_every_client_has_a_known_scenario_and_every_scenario_a_client(clients):
    assert {b.spec.scenario for b in clients.values()} == set(SCENARIOS)
    assert len(clients) == 16


def test_the_generator_verifies_itself_and_fails_loudly(clients):
    for book in clients.values():
        verify(book)
    broken = clients["datamarrow"]
    original = broken.spec.min_cash
    object.__setattr__(broken.spec, "min_cash", 4_000_000)  # cash would then pass: the scenario is gone
    try:
        with pytest.raises(AssertionError, match="datamarrow"):
            verify(broken)
    finally:
        object.__setattr__(broken.spec, "min_cash", original)


def test_the_owners_figures_hold_in_the_assembled_book(clients):
    assert clients["datamarrow"].series.cash(LAST) == 4_600_000 and clients["calvere-health"].series.cash(LAST) == 4_000_000
    assert q(clients["vantrell-labs"].series.rml(LAST), 1) == D("27.5")


def test_clean_clients_raise_nothing_and_carry_no_loud_signal(clients):
    for client_id in ("mosswell-robotics", "tarnavi-ai", "orbitline-systems", "veridia-payments", "vantrell-labs",
                      "pellucid-sensors", "tavernel-grid", "kelvra-bio", "brightvane-energy", "ferrogate-cloud"):
        book = clients[client_id]
        assert exceptions(book) == [], client_id
        loud = [s["rule"] for s in current_signals(book) if s["severity"] != "low" and s["rule"] != "runway_falling"]
        assert loud == [], client_id


def test_datamarrow_certificate_counts_pledged_cash_and_claims_compliance(clients):
    book = clients["datamarrow"]
    row = current(book)["min_unrestricted_cash"]
    assert row["value"] == D(4_600_000) < row["threshold"] == D(5_000_000)
    assert row["reported_value"] == D(6_100_000) and row["reported_in_compliance"] is True
    assert row["outcome"] == "breach_reported_compliant"
    assert exceptions(book) == ["covenant.reported_mismatch", "signal.high"]
    assert book.scenario_details["definition_clause"] == {"_anchor": ("credit-agreement", "def_unrestricted_cash")}


def test_datamarrows_extension_is_a_signed_term_sheet_closing_on_12_december(clients):
    events = clients["datamarrow"].funding_events
    assert [(e["kind"], e["amount"], e["expected_close"], e["status"]) for e in events] == [
        ("extension", 8_000_000, date(2026, 12, 12), "signed")]
    assert events[0]["evidence_document_ids"] == ["datamarrow.term-sheet-2026-11-10"]


def test_calvere_october_package_is_12_days_late(clients):
    book = clients["calvere-health"]
    assert max(i["days_late"] for i in book.scenario_details["reporting"]) == 12
    assert (AS_OF - date(2026, 11, 7)).days == 12  # bank statements are due 7 days after month end
    assert exceptions(book) == ["intake.missing_document"] * 2
    assert not [d for d in book.documents if d.period_end == CURRENT_PERIOD]
    assert all(r["outcome"] == "cannot_test" and r["after_repair"]["pass"] for r in current(book).values())
    assert not current_signals(book)
    assert [d.id for d in book.documents if d.period_end == date(2026, 9, 30)][:1] == ["calvere-health.bank-2026-09-30"]


def test_brightvane_runway_falls_three_months_running_and_stays_above_the_watch_level(clients):
    book = clients["brightvane-energy"]
    points = [book.series.rml(i) for i in range(LAST - 3, LAST + 1)]
    assert all(b < a for a, b in zip(points, points[1:], strict=False)) and points[-1] >= 12
    rules = {s["rule"] for s in current_signals(book)}
    assert "runway_falling" in rules and "burn_rising" not in rules and "runway_below_watch" not in rules


def test_meridew_misses_plan_two_months_running_against_figures_in_the_terms(clients):
    book = clients["meridew-analytics"]
    rows = {(r["period_end"], r["covenant_id"]): r for r in book.expected["covenant_tests"]}
    sep, oct_ = rows[(date(2026, 9, 30), "revenue_vs_plan")], rows[(CURRENT_PERIOD, "revenue_vs_plan")]
    aug = rows[(date(2026, 8, 31), "revenue_vs_plan")]
    assert aug["outcome"] == "compliant" and sep["outcome"] == "breach" and oct_["outcome"] == "breach"
    assert exceptions(book) == ["covenant.breach"]
    covenant = book.terms.version["terms"]["covenants"][2]
    assert covenant["test"]["threshold"] == "0.80" and covenant["measurement"]["basis"] == "t3m"
    assert len(covenant["params"]["plan"]) == 18  # plan figures are terms data, 18 months


def test_nimbusfield_funding_slipped_and_runway_is_under_nine_months(clients):
    book = clients["nimbusfield-security"]
    assert book.funding_events[0]["expected_close"] < AS_OF and book.funding_events[0]["status"] == "expected"
    assert book.series.rml(LAST) < 9
    assert exceptions(book) == ["funding_slipped", "signal.high"]


def test_brackmere_certificate_counts_a_restricted_account(clients):
    book = clients["brackmere-medical"]
    assert book.series.cash(LAST) == 4_300_000
    cash = current(book)["min_unrestricted_cash"]
    assert cash["outcome"] == "compliant_variance" and cash["reported_value"] - cash["value"] == 1_000_000
    assert exceptions(book) == ["cash.statement_mismatch"]
    assert sum(a["closing"] for a in reports.bank_accounts(book.spec, book.months, LAST) if a["restricted"]) == 1_100_000


def test_ferrogate_is_cash_flow_positive_and_runway_is_not_meaningful(clients):
    book = clients["ferrogate-cloud"]
    row = current(book)["min_runway_months"]
    assert (row["value"], row["pass"], row["note"], row["outcome"]) == (
        None, True, "not_meaningful_cash_flow_positive", "compliant")
    assert row["reported_value"] is None and row["reported_in_compliance"] is True
    assert not [s for s in current_signals(book) if s["rule"].startswith("runway")]


def test_cindrel_roll_ties_and_misreading_it_changes_runway_a_lot(clients):
    book = clients["cindrel-tech"]
    details = book.scenario_details["capitalised_software"]
    roll = reports.software_roll(book.months, LAST)
    assert roll["opening"] + roll["additions"] - roll["amortisation"] == roll["closing"]
    assert details["balance"] > 10 * details["month_spend"]
    assert reports.misread_runway(book.series, LAST) < book.series.rml(LAST) * D("0.7")
    assert q(reports.misread_runway(book.series, LAST), 2) == details["misread_runway"]
    assert exceptions(book) == ["intake.unclassified", "spread.value_unverified"]
    assert book.scenario_details["new_line"]["belongs_to"] == "bs.deferred_revenue_current"
    export = next(d for d in book.documents if d.id == "cindrel-tech.mrr-export")
    assert export.extra["held"] is True and export.period_end is None and len(export.payload["rows"]) == 10


def test_funding_events_cover_datamarrow_tavernel_kelvra_and_nimbusfield(clients):
    events = {cid: b.funding_events for cid, b in clients.items() if b.funding_events}
    assert sorted(events) == ["datamarrow", "kelvra-bio", "nimbusfield-security", "tavernel-grid"]
    assert (events["tavernel-grid"][0]["kind"], events["tavernel-grid"][0]["expected_close"]) == (
        "equity_round", date(2027, 3, 31))
    assert (events["kelvra-bio"][0]["kind"], events["kelvra-bio"][0]["expected_close"]) == (
        "milestone_tranche", date(2027, 2, 26))
    for cid, rows in events.items():
        ids = {d.id for d in clients[cid].documents}
        assert all(rows_[0] for rows_ in [e["evidence_document_ids"] for e in rows]), cid
        assert all(set(e["evidence_document_ids"]) <= ids for e in rows), cid


def test_ferrogate_dscr_tests_run_from_may_2026_under_the_second_terms_version(clients):
    book = clients["ferrogate-cloud"]
    rows = [r for r in book.expected["covenant_tests"] if r["covenant_id"] == "dscr"]
    assert [r["period_end"] for r in rows] == list(model.MONTHS[16:])  # May to October 2026
    assert all(r["outcome"] == "compliant" and r["pass"] and r["threshold"] == D("1.25") for r in rows)
    assert all(r["unit"] == "ratio" and r["terms_version"] == 2 and r["terms_version_id"] == "tv-ferrogate-cloud-2"
               for r in rows)
    assert rows[-1]["value"] == q(book.series.dscr(LAST), 2)
    assert rows[-1]["reported_value"] == rows[-1]["value"] and rows[0]["reported_value"] is None
    versions = {v["id"]: v for v in book.terms.versions()}
    for r in book.expected["covenant_tests"]:  # every row cites the version in force at its period end
        assert r["period_end"] >= date.fromisoformat(versions[r["terms_version_id"]]["effective_from"])
        assert r["terms_version"] == versions[r["terms_version_id"]]["version"]
    assert {r["terms_version"] for r in book.expected["covenant_tests"] if r["period_end"] < date(2026, 5, 31)} == {1}
    printed = reports.format_actual("ratio", rows[-1]["value"])
    assert printed.endswith(" to 1.00") and printed.startswith(f"{rows[-1]['value']:.2f}")
