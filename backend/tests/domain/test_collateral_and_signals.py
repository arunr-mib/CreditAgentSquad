"""Borrowing base review and early warning signals over stored facts, with hand-computed cases."""
from datetime import UTC, date, datetime
from decimal import Decimal as D

import pytest
from app.domain.collateral_service import review_borrowing_base
from app.domain.credit import Borrower, Facility
from app.domain.facts_service import add_fact, current_fact
from app.domain.monitoring import WorkItem
from app.domain.org import User
from app.domain.signals_service import quarter_ends, run_signals
from app.domain.terms import ReportingObligation, TermsVersion
from sqlalchemy import select

PERIOD = date(2026, 9, 30)
TERMS = {
    "definitions": {}, "covenants": [], "reporting_requirements": [],
    "borrowing_base": {
        "commitment": "5000000", "frequency": "monthly", "reserves": [{"name": "rent", "amount": "100000"}],
        "components": [
            {"collateral": "accounts_receivable", "advance_rate": "0.85",
             "eligibility": {"max_age_days": 90, "exclude": ["intercompany"]}},
            {"collateral": "inventory", "advance_rate": "0.50", "sublimit": "1500000",
             "eligibility": {"exclude": ["work_in_process"]}}]},
}
ZERO = {"days_1_30": "0", "days_31_60": "0", "days_61_90": "0", "over_90": "0"}
AR = [{"customer": "Albion Hardware", "current": "1000000", **ZERO},
      {"customer": "Brant Supply", "current": "300000", **{**ZERO, "over_90": "100000"}},
      {"customer": "Harrowgate Holdings", "current": "400000", **ZERO, "flags": ["intercompany"]}]
INVENTORY = [{"category": "raw_materials", "amount": "800000"}, {"category": "finished_goods", "amount": "1200000"},
             {"category": "work_in_process", "amount": "300000"}]
# receivables 1,800,000; excluded 400,000; aged 100,000; eligible 1,300,000; x 0.85 = 1,105,000
# inventory 2,300,000; ineligible 300,000; eligible 2,000,000; x 0.50 = 1,000,000 (under the sublimit)
# base = 1,105,000 + 1,000,000 - 100,000 reserves = 2,005,000
GOOD_CERT = {"ar_eligible": D("1300000"), "inventory_eligible": D("2000000"), "borrowing_base": D("2005000")}


@pytest.fixture()
def world(db):
    officer = User(email="o@x.example", name="Officer", role="credit_officer", password_hash="x")
    borrower = Borrower(code="HTD", name="Harrowgate Tool & Die, Inc.")
    db.add_all([officer, borrower])
    db.flush()
    facility = Facility(borrower_id=borrower.id, code="HTD-RLOC", name="Revolver", facility_type="revolver",
                        commitment=D("5000000"), has_borrowing_base=True)
    db.add(facility)
    db.flush()
    db.add(TermsVersion(facility_id=facility.id, version=1, status="approved", effective_from=date(2024, 1, 1),
                        terms=TERMS, approved_by=officer.id, approved_at=datetime.now(UTC)))
    db.flush()
    return borrower, facility


def review(db, world, certificate=GOOD_CERT, outstanding="1500000"):
    borrower, facility = world
    return review_borrowing_base(db, borrower=borrower, facility=facility, period_end=PERIOD, ar_rows=AR,
                                 inventory_rows=INVENTORY, certificate=certificate, outstanding=D(outstanding),
                                 letters_of_credit=D("100000"))


def items(db):
    return sorted((w.item_type, w.severity) for w in db.execute(select(WorkItem)).scalars())


def test_recalculation_agrees_and_availability_is_stored_as_a_calculated_fact(db, world):
    r = review(db, world)
    assert r.outcome == "agrees" and items(db) == []
    assert (D(r.computed["ar_eligible"]), D(r.computed["borrowing_base"]), r.availability) == (
        D("1300000"), D("2005000"), D("405000"))
    fact = current_fact(db, world[0].id, "bb.availability", PERIOD, 0)
    assert fact.kind == "calculated" and fact.value == D("405000") and fact.calc_run_id == r.calc_run_id


def test_certificate_that_kept_aged_receivables_is_a_mismatch(db, world):
    r = review(db, world, certificate={**GOOD_CERT, "ar_eligible": D("1400000"), "borrowing_base": D("2090000")})
    assert r.outcome == "mismatch" and items(db) == [("bb.certificate_mismatch", "high")]
    lines = {d["line"]: d for d in r.differences if d["status"] == "mismatch"}
    assert D(lines["ar_eligible"]["difference"]) == D("-100000") and set(lines) == {"ar_eligible", "borrowing_base"}


def test_over_advance_is_critical_and_needs_a_credit_officer(db, world):
    r = review(db, world, outstanding="2200000")
    assert r.outcome == "over_advance" and r.over_advance == D("295000") and r.availability == D("-295000")
    item = db.execute(select(WorkItem)).scalar_one()
    assert (item.item_type, item.severity, item.required_permission) == ("bb.over_advance", "critical", "decide_breach")


def test_bad_listing_is_refused_not_guessed(db, world):
    borrower, facility = world
    r = review_borrowing_base(db, borrower=borrower, facility=facility, period_end=PERIOD, ar_rows=AR + [AR[0]],
                              inventory_rows=INVENTORY, certificate=GOOD_CERT, outstanding=D("1"), letters_of_credit=D("0"))
    assert r.outcome == "cannot_compute" and r.availability is None
    assert current_fact(db, borrower.id, "bb.availability", PERIOD, 0) is None


def test_quarter_ends():
    assert quarter_ends(date(2026, 3, 31), 3) == [date(2025, 9, 30), date(2025, 12, 31), date(2026, 3, 31)]


def test_signals_fire_from_facts_and_high_severity_asks_a_person(db, world):
    borrower, facility = world
    # trailing twelve months at Q3 2026 = YTD 2026 + FY 2025 - YTD Q3 2025 = -300,000 + 400,000 - 500,000 = -400,000
    for end, months, value in [(PERIOD, 9, "-300000"), (date(2025, 12, 31), 12, "400000"), (date(2025, 9, 30), 9, "500000")]:
        add_fact(db, borrower_id=borrower.id, key="is.net_income", period_end=end, months=months, value=D(value), kind="seeded")
    add_fact(db, borrower_id=borrower.id, key="sys.revolver_outstanding", period_end=PERIOD, months=0,
             value=D("4700000"), kind="system", connector="core", record_ref="RLOC-1", as_of=datetime.now(UTC))
    add_fact(db, borrower_id=borrower.id, key="sys.commitment", period_end=PERIOD, months=0, value=D("5000000"),
             kind="system", connector="core", record_ref="RLOC-1", as_of=datetime.now(UTC))
    db.add(ReportingObligation(borrower_id=borrower.id, facility_id=facility.id, requirement_id="quarterly_statements",
                               document_type="interim_statements", period_end=PERIOD, due_date=date(2026, 10, 30)))
    db.flush()
    signals = run_signals(db, borrower=borrower, period_end=PERIOD, as_of=date(2026, 11, 17))
    fired = {s.rule_id: s for s in signals}
    assert {"net_loss", "line_usage_high", "reporting_late"} <= set(fired)
    assert fired["net_loss"].severity == "high" and fired["net_loss"].rule_version == "signals-1"
    # a net loss and late reporting are both high severity, so each asks a person
    assert items(db) == [("signal.high", "high")] * 2
    # running again does not duplicate signals or items
    again = run_signals(db, borrower=borrower, period_end=PERIOD, as_of=date(2026, 11, 17))
    assert len(again) == len(signals) and items(db) == [("signal.high", "high")] * 2


def test_printed_inventory_categories_map_to_the_names_used_in_terms():
    from app.agents.collateral import inventory_category
    assert inventory_category("Inventory held on consignment") == "consigned"
    assert inventory_category("Work in process") == "work_in_process"
    assert inventory_category("Work-in-progress (WIP)") == "work_in_process"
    assert inventory_category("Raw materials") == "raw_materials"
    assert inventory_category("Finished goods") == "finished_goods"
    assert inventory_category("Spare parts") == "spare_parts"  # unknown categories keep their own name
