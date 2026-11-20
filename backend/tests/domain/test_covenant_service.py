"""Covenant testing from stored facts and approved terms, with a hand-computed case."""
from datetime import UTC, date, datetime
from decimal import Decimal as D

import pytest
from app.domain.covenant_service import governing_terms, run_covenant_tests
from app.domain.credit import Borrower, Facility
from app.domain.facts import CalcRun, Fact
from app.domain.facts_service import add_fact
from app.domain.monitoring import WorkItem
from app.domain.org import User
from app.domain.terms import TermsVersion
from sqlalchemy import select

FY = date(2025, 12, 31)


def cite(section):
    return [{"document_id": "agreement", "section": section, "page": 7, "quote": "..."}]


def terms(min_fccr="1.20", cap="300000"):
    return {
        "definitions": {"ebitda": {"base": "ebitda", "addbacks": [
            {"name": "restructuring", "source_key": "is.nonrecurring_expense",
             "cap": {"type": "amount", "value": cap}, "citation": cite("1.1")[0]}]}},
        "covenants": [
            {"id": "fccr", "name": "Fixed Charge Coverage Ratio", "archetype": "coverage",
             "params": {"numerator_base": "adjusted_ebitda", "deductions": ["unfinanced_capex", "cash_taxes"],
                        "denominator": ["cash_interest", "scheduled_principal"]},
             "test": {"operator": ">=", "threshold": min_fccr, "unit": "ratio"},
             "measurement": {"basis": "ttm", "frequency": "quarterly"},
             "rounding": {"dp": 2, "mode": "half_up"}, "citations": cite("7.11")},
            {"id": "leverage", "name": "Total Leverage Ratio", "archetype": "leverage",
             "params": {"debt": "total_debt", "ebitda": "ebitda"},
             "test": {"operator": "<=", "threshold": "3.50", "unit": "ratio"},
             "measurement": {"basis": "ttm", "frequency": "quarterly"},
             "rounding": {"dp": 2, "mode": "half_up"}, "citations": cite("7.12")},
        ],
        "reporting_requirements": [], "borrowing_base": None,
    }


# fiscal year 2025, whole dollars
FLOWS = {"is.net_income": "2000000", "is.interest_expense": "900000", "is.income_tax_expense": "600000",
         "is.depreciation_amortization": "1100000", "is.nonrecurring_expense": "620000", "cf.capex": "1300000",
         "sup.financed_capex": "200000", "sup.cash_taxes_paid": "550000", "sup.cash_interest_paid": "880000",
         "sup.scheduled_principal": "1200000"}
POINTS = {"bs.revolver": "3000000", "bs.cpltd": "1200000", "bs.long_term_debt": "8300000",
          "bs.subordinated_debt": "0"}
# EBITDA = 2,000,000 + 900,000 + 600,000 + 1,100,000 = 4,600,000
# adjusted EBITDA = 4,600,000 + min(620,000, 300,000) = 4,900,000
# FCCR = (4,900,000 - (1,300,000 - 200,000) - 550,000) / (880,000 + 1,200,000) = 3,250,000 / 2,080,000 = 1.5625 -> 1.56
# leverage = (3,000,000 + 1,200,000 + 8,300,000 + 0) / 4,600,000 = 12,500,000 / 4,600,000 = 2.7174 -> 2.72


@pytest.fixture()
def world(db):
    approver = User(email="o@x.example", name="Officer", role="credit_officer", password_hash="x")
    borrower = Borrower(code="HTD", name="Harrowgate Tool & Die, Inc.")
    db.add_all([approver, borrower])
    db.flush()
    facility = Facility(borrower_id=borrower.id, code="HTD-TL", name="Term loan", facility_type="term_loan",
                        commitment=D("10000000"), origination_date=date(2024, 1, 15))
    db.add(facility)
    db.flush()
    for key, value in FLOWS.items():
        add_fact(db, borrower_id=borrower.id, key=key, period_end=FY, months=12, value=D(value), kind="seeded")
    for key, value in POINTS.items():
        add_fact(db, borrower_id=borrower.id, key=key, period_end=FY, months=0, value=D(value), kind="seeded")
    return borrower, facility, approver


def approve(db, facility, approver, body, version=1, effective=date(2024, 1, 15), status="approved"):
    row = TermsVersion(facility_id=facility.id, version=version, status=status, effective_from=effective, terms=body,
                       approved_by=approver.id if status != "proposed" else None,
                       approved_at=datetime.now(UTC) if status != "proposed" else None)
    db.add(row)
    db.flush()
    return row


def by_id(tests):
    return {t.covenant_id: t for t in tests}


def test_hand_computed_tests_with_capped_addback_and_logged_inputs(db, world):
    borrower, facility, approver = world
    approve(db, facility, approver, terms())
    tests = by_id(run_covenant_tests(db, borrower=borrower, facility=facility, period_end=FY))
    fccr, lev = tests["fccr"], tests["leverage"]
    assert (fccr.value, fccr.threshold, fccr.passed, fccr.outcome) == (D("1.56"), D("1.20"), True, "compliant")
    assert fccr.headroom == D("0.36")
    assert (lev.value, lev.passed, lev.headroom) == (D("2.72"), True, D("0.78"))

    calc = db.get(CalcRun, fccr.calc_run_id)
    used = {i["key"] for i in calc.inputs}
    assert {"is.net_income", "is.nonrecurring_expense", "cf.capex", "sup.scheduled_principal"} <= used
    assert all(i["fact_id"] for i in calc.inputs)  # every input names its fact
    addback = calc.trace["addbacks"][0]
    assert (D(addback["raw"]), D(addback["applied"]), addback["capped"]) == (D("620000"), D("300000"), True)
    value_fact = db.get(Fact, fccr.value_fact_id)
    assert value_fact.kind == "calculated" and value_fact.calc_run_id == calc.id and value_fact.key == "cov.fccr.value"
    assert db.execute(select(WorkItem)).first() is None


def test_breach_behind_a_compliant_certificate_is_critical(db, world):
    borrower, facility, approver = world
    approve(db, facility, approver, terms(min_fccr="1.60"))
    add_fact(db, borrower_id=borrower.id, key="cert.fccr.value", period_end=FY, months=0, value=D("1.71"),
             unit="ratio", kind="seeded")
    add_fact(db, borrower_id=borrower.id, key="cert.fccr.in_compliance", period_end=FY, months=0, value=D("1"),
             unit="count", kind="seeded")
    tests = by_id(run_covenant_tests(db, borrower=borrower, facility=facility, period_end=FY))
    assert tests["fccr"].outcome == "breach_reported_compliant" and tests["fccr"].reported_value == D("1.71")
    item = db.execute(select(WorkItem)).scalar_one()
    assert item.item_type == "covenant.reported_mismatch" and item.severity == "critical"
    assert item.required_permission == "decide_breach" and item.blocks_stage


def test_certificate_variance_that_passes_either_way_raises_nothing(db, world):
    borrower, facility, approver = world
    approve(db, facility, approver, terms())
    add_fact(db, borrower_id=borrower.id, key="cert.fccr.value", period_end=FY, months=0, value=D("1.71"),
             unit="ratio", kind="seeded")  # the borrower took the add-back uncapped
    add_fact(db, borrower_id=borrower.id, key="cert.fccr.in_compliance", period_end=FY, months=0, value=D("1"),
             unit="count", kind="seeded")
    tests = by_id(run_covenant_tests(db, borrower=borrower, facility=facility, period_end=FY))
    assert tests["fccr"].outcome == "compliant_variance" and db.execute(select(WorkItem)).first() is None


def test_a_pass_that_contradicts_a_certificate_reporting_a_breach_is_put_to_a_person(db, world):
    # found by the independent review: a misread figure can turn a breach into a pass, and the
    # borrower's own admission of the breach was only logged
    borrower, facility, approver = world
    approve(db, facility, approver, terms())
    add_fact(db, borrower_id=borrower.id, key="cert.fccr.value", period_end=FY, months=0, value=D("1.10"),
             unit="ratio", kind="seeded")
    add_fact(db, borrower_id=borrower.id, key="cert.fccr.in_compliance", period_end=FY, months=0, value=D("0"),
             unit="count", kind="seeded")
    tests = by_id(run_covenant_tests(db, borrower=borrower, facility=facility, period_end=FY))
    assert tests["fccr"].outcome == "compliant_variance" and tests["fccr"].reported_in_compliance is False
    item = db.execute(select(WorkItem)).scalar_one()
    assert item.item_type == "covenant.reported_breach_unconfirmed" and item.severity == "high"
    assert item.blocks_stage and item.required_permission == "decide_breach"


def test_missing_input_cannot_test_and_names_the_line(db, world):
    borrower, facility, approver = world
    approve(db, facility, approver, terms())
    fact = db.execute(select(Fact).where(Fact.key == "sup.scheduled_principal")).scalar_one()
    fact.status = "rejected"
    tests = by_id(run_covenant_tests(db, borrower=borrower, facility=facility, period_end=FY))
    assert tests["fccr"].outcome == "cannot_test" and tests["fccr"].value is None
    assert tests["leverage"].outcome == "compliant"
    item = db.execute(select(WorkItem)).scalar_one()
    assert item.item_type == "covenant.cannot_test" and "sup.scheduled_principal" in item.question


def test_proposed_terms_never_govern_and_amendment_supersedes(db, world):
    borrower, facility, approver = world
    v1 = approve(db, facility, approver, terms(cap="300000"))
    v2 = approve(db, facility, approver, terms(cap="700000"), version=2, effective=date(2025, 10, 1), status="proposed")
    row, _ = governing_terms(db, facility, FY)
    assert row.id == v1.id
    assert by_id(run_covenant_tests(db, borrower=borrower, facility=facility, period_end=FY))["fccr"].value == D("1.56")

    # a second person approves the amendment: v1 is closed the day before, v2 governs from its date
    v1.status, v1.effective_to = "superseded", date(2025, 9, 30)
    db.flush()
    v2.status, v2.approved_by, v2.approved_at = "approved", approver.id, datetime.now(UTC)
    db.flush()
    rerun = by_id(run_covenant_tests(db, borrower=borrower, facility=facility, period_end=FY))
    # adjusted EBITDA = 4,600,000 + 620,000 = 5,220,000; FCCR = 3,570,000 / 2,080,000 = 1.7163 -> 1.72
    assert rerun["fccr"].value == D("1.72") and rerun["fccr"].terms_version_id == v2.id
    history = db.execute(select(Fact).where(Fact.key == "cov.fccr.value").order_by(Fact.created_at)).scalars().all()
    assert [f.value for f in history] == [D("1.56"), D("1.72")]  # the earlier result is kept
    from app.domain.monitoring import CovenantTest
    flags = [t.superseded for t in db.execute(select(CovenantTest).where(CovenantTest.covenant_id == "fccr")
                                               .order_by(CovenantTest.created_at)).scalars()]
    assert flags == [True, False]


def test_no_terms_in_force_raises_one_item(db, world):
    borrower, facility, _ = world
    tests = run_covenant_tests(db, borrower=borrower, facility=facility, period_end=FY)
    assert [t.outcome for t in tests] == ["cannot_test"]
    assert db.execute(select(WorkItem)).scalar_one().item_type == "covenant.cannot_test"


def vc_world(db):
    approver = User(email="vc@x.example", name="Officer", role="credit_officer", password_hash="x")
    borrower = Borrower(code="VCD", name="Quillfeather Labs, Inc.", template_id="vc-1")
    db.add_all([approver, borrower])
    db.flush()
    facility = Facility(borrower_id=borrower.id, code="VCD-VD", name="Venture loan", facility_type="term_loan",
                        commitment=D("5000000"), origination_date=date(2024, 1, 15))
    db.add(facility)
    db.flush()
    return borrower, facility, approver


def dscr_terms():
    return {
        "definitions": {},
        "covenants": [
            {"id": "dscr", "name": "Debt Service Coverage", "archetype": "coverage",
             "params": {"numerator_base": "ebitda", "deductions": [],
                        "denominator": ["cash_interest", "scheduled_principal"]},
             "test": {"operator": ">=", "threshold": "1.20", "unit": "ratio"},
             "measurement": {"basis": "ttm", "frequency": "quarterly"},
             "rounding": {"dp": 2, "mode": "half_up"}, "citations": cite("7.11")}],
        "reporting_requirements": [], "borrowing_base": None,
    }


def test_vc_borrower_dscr_is_tested_with_vc_formulas(db):
    borrower, facility, approver = vc_world(db)
    approve(db, facility, approver, dscr_terms())
    # vc_ebitda = operating loss + D&A = -1,000,000 + 200,000 = -800,000; debt service 800,000 -> -1.00
    for key, value in {"is.vc_operating_loss": "-1000000", "is.vc_depreciation_amortization": "200000",
                       "sup.cash_interest_paid": "300000", "sup.scheduled_principal": "500000"}.items():
        add_fact(db, borrower_id=borrower.id, key=key, period_end=FY, months=12, value=D(value), kind="seeded")
    (test,) = run_covenant_tests(db, borrower=borrower, facility=facility, period_end=FY)
    assert test.outcome == "breach" and test.value == D("-1.00") and test.passed is False
    calc = db.get(CalcRun, test.calc_run_id)
    assert "is.vc_operating_loss" in {i["key"] for i in calc.inputs}


def test_vc_adjusted_ebitda_covenant_is_cannot_test_with_its_own_error_code(db):
    borrower, facility, approver = vc_world(db)
    body = dscr_terms()
    body["definitions"] = {"ebitda": {"base": "ebitda", "addbacks": []}}
    body["covenants"][0]["params"]["numerator_base"] = "adjusted_ebitda"
    approve(db, facility, approver, body)
    (test,) = run_covenant_tests(db, borrower=borrower, facility=facility, period_end=FY)
    assert test.outcome == "cannot_test"
    calc = db.get(CalcRun, test.calc_run_id)
    assert calc.error and "venture template" in calc.error
