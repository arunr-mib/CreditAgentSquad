"""Monthly cycles for the venture template, quarterly for the commercial one, and spreading that
knows which template's lines a borrower has."""
import json
from datetime import UTC, date, datetime

import pytest
from app.agents.llm import LLMResponse, ScriptedClient
from app.agents.spreading import spread_document
from app.calc.periods import ytd_months
from app.core.config import get_settings
from app.domain.credit import Borrower, Facility
from app.domain.documents_service import ingest_pdf
from app.domain.facts import Fact
from app.domain.monitoring import Cycle, WorkItem
from app.domain.org import User
from app.domain.periods_service import period_ends_for, reporting_frequency
from app.domain.signals_service import _series
from app.domain.stages import quarter_months, statements_wanted
from app.domain.terms import TermsVersion
from sqlalchemy import select
from support.statement_pdf import build_pdf, perfect_answer

AUG, SEP, OCT = date(2026, 8, 31), date(2026, 9, 30), date(2026, 10, 31)


def borrower(db, code, template_id="ci-1", fye=12) -> Borrower:
    b = Borrower(code=code, name="Harrowgate Tool & Die, Inc.", template_id=template_id, fiscal_year_end_month=fye)
    db.add(b)
    db.flush()
    return b


def approve_reporting(db, b, frequency, document_type="monthly_financials"):
    user = User(email=f"{b.code}@x.example", name="A", role="credit_officer", password_hash="x")
    db.add(user)
    db.flush()
    facility = Facility(borrower_id=b.id, code=f"{b.code}-TL", name="Loan", facility_type="term_loan",
                        commitment=1_000_000)
    db.add(facility)
    db.flush()
    db.add(TermsVersion(
        facility_id=facility.id, version=1, status="approved", effective_from=date(2025, 1, 1),
        approved_by=user.id, approved_at=datetime.now(UTC),
        terms={"definitions": {}, "covenants": [], "borrowing_base": None, "reporting_requirements": [
            {"id": "fin", "document_type": document_type, "frequency": frequency,
             "due_days_after_period_end": 30}]}))
    db.flush()


def test_a_venture_borrower_gets_monthly_periods_by_default(db):
    b = borrower(db, "VC1", "vc-1")
    assert reporting_frequency(db, b, OCT) == "monthly"
    assert period_ends_for(db, b, AUG, OCT) == [AUG, SEP, OCT]


def test_a_commercial_borrower_gets_quarterly_periods_by_default(db):
    b = borrower(db, "CI1")
    assert period_ends_for(db, b, date(2026, 1, 1), SEP) == [date(2026, 3, 31), date(2026, 6, 30), SEP]
    assert ytd_months(SEP, b.fiscal_year_end_month) == 9


def test_approved_reporting_requirements_set_the_frequency(db):
    b = borrower(db, "CI2")
    approve_reporting(db, b, "monthly")
    assert period_ends_for(db, b, AUG, OCT) == [AUG, SEP, OCT]
    v = borrower(db, "VC2", "vc-1")
    approve_reporting(db, v, "quarterly", "interim_statements")
    assert period_ends_for(db, v, date(2026, 1, 1), SEP) == [date(2026, 3, 31), date(2026, 6, 30), SEP]


def test_months_come_from_the_fiscal_year_not_from_nine():
    assert ytd_months(SEP, 12) == 9 and ytd_months(OCT, 12) == 10 and ytd_months(AUG, 6) == 2
    assert quarter_months(date(2026, 12, 31), 6) == 6


def test_signal_history_steps_by_month_for_venture_and_quarter_for_commercial(db):
    vc = _series(db, borrower(db, "VC3", "vc-1"), OCT)
    ends = [p.period_end for p in vc]
    assert ends[-3:] == [AUG, SEP, OCT] and all(p.months == ytd_months(p.period_end, 12) for p in vc)
    ci = _series(db, borrower(db, "CI3"), SEP)
    assert [p.period_end for p in ci][-3:] == [date(2026, 3, 31), date(2026, 6, 30), SEP]
    assert len(ci) == 8


def test_the_statement_a_cycle_waits_for_follows_the_fiscal_year_end(db):
    def cycle(b, end, months, cycle_type):
        return Cycle(borrower_id=b.id, period_end=end, months=months, cycle_type=cycle_type)
    vc = borrower(db, "VC4", "vc-1")
    assert statements_wanted(cycle(vc, OCT, 10, "monthly"), vc) == "monthly_financials"
    assert statements_wanted(cycle(vc, date(2026, 12, 31), 12, "monthly"), vc) == "annual_statements"
    ci = borrower(db, "CI4", fye=6)
    assert statements_wanted(cycle(ci, date(2026, 6, 30), 12, "quarterly"), ci) == "annual_statements"
    # twelve months of a year, but not the year end: a twelve-month cycle is not annual by count alone
    assert statements_wanted(cycle(ci, date(2026, 12, 31), 12, "quarterly"), ci) == "interim_statements"


@pytest.fixture()
def files(tmp_path, monkeypatch):
    monkeypatch.setenv("FILE_STORE_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def spread(db, b, answer):
    doc = ingest_pdf(db, borrower_id=b.id, data=build_pdf(), file_name="q3-2026.pdf",
                     doc_type="interim_statements", doc_type_source="system", period_end=SEP)
    llm = ScriptedClient([LLMResponse(content=[{"type": "text", "text": json.dumps(answer)}], stop_reason="end_turn")])
    return spread_document(db, borrower=b, document=doc, period_end=SEP, months=9, cycle=None, llm=llm), llm


def refusals(db):
    return [w for w in db.execute(select(WorkItem)).scalars() if w.evidence.get("template")]


def test_spreading_refuses_a_commercial_line_for_a_venture_borrower(db, files):
    b = borrower(db, "VC5", "vc-1")
    result, llm = spread(db, b, perfect_answer())
    assert "is.revenue" in refusals(db)[0].evidence["lines"] and len(refusals(db)) == 1
    assert "is.revenue" not in result.facts and result.status == "needs_person"
    assert db.execute(select(Fact).where(Fact.borrower_id == b.id, Fact.key == "is.revenue")).first() is None
    listing = llm.requests[0].messages[0]["content"][-1]["text"]
    assert "is.subscription_revenue" in listing and "is.revenue |" not in listing


def test_spreading_refuses_a_venture_line_for_a_commercial_borrower(db, files):
    b = borrower(db, "CI5")
    answer = perfect_answer()
    answer["cells"] = [*answer["cells"], {**answer["cells"][0], "key": "bs.cash_unrestricted"}]
    result, llm = spread(db, b, answer)
    assert refusals(db)[0].evidence["lines"] == ["bs.cash_unrestricted"]
    assert db.execute(select(Fact).where(Fact.borrower_id == b.id, Fact.key == "bs.cash_unrestricted")).first() is None
    listing = llm.requests[0].messages[0]["content"][-1]["text"]
    assert "is.revenue" in listing and "bs.cash_unrestricted" not in listing


def test_a_commercial_borrower_with_approved_monthly_reporting_gets_monthly_signal_history(db):
    b = borrower(db, "CI6")
    approve_reporting(db, b, "monthly")
    ends = [p.period_end for p in _series(db, b, OCT)]
    assert len(ends) == 14 and ends[-3:] == [AUG, SEP, OCT]
    assert all(p.months == ytd_months(p.period_end, 12) for p in _series(db, b, OCT))


def test_fourteen_monthly_period_ends_cross_the_year_boundary(db):
    b = borrower(db, "VC6", "vc-1")
    assert period_ends_for(db, b, date(2025, 9, 1), OCT) == [
        date(2025, 9, 30), date(2025, 10, 31), date(2025, 11, 30), date(2025, 12, 31), date(2026, 1, 31),
        date(2026, 2, 28), date(2026, 3, 31), date(2026, 4, 30), date(2026, 5, 31), date(2026, 6, 30),
        date(2026, 7, 31), AUG, SEP, OCT]


def _truth(code, template_id, tested, period):
    info = {"id": code, "name": "Harrowgate Tool & Die, Inc.", "industry": "Software", "fiscal_year_end_month": 12,
            "risk_rating": 4, "relationship_manager": "Rae Manager", "analyst": "Ana Lyst"}
    if template_id:
        info["template_id"] = template_id
    return {"borrower": info, "as_of": period, "current_period": period, "facilities": [], "documents": [],
            "terms_versions": [], "periods": [], "system_of_record": [], "certificates": [], "borrowing_base": [],
            "expected": {"covenant_tests": [{"period_end": d} for d in tested], "exceptions": []}}


def _seed(db, truth, tmp_path):
    from app.seed_book import SeedReport, seed_borrower
    return seed_borrower(db, truth, docs_root=tmp_path, current="seeded", password_hash="x", report=SeedReport())


def test_seeding_a_venture_borrower_opens_monthly_cycles(db, tmp_path):
    b = _seed(db, _truth("VCS", "vc-1", ["2026-08-31", "2026-09-30", "2026-10-31"], "2026-10-31"), tmp_path)
    cycles = db.execute(select(Cycle).where(Cycle.borrower_id == b.id)).scalars().all()
    assert b.template_id == "vc-1"
    assert {c.cycle_type for c in cycles} == {"monthly"} and len(cycles) == 3


def test_seeding_a_commercial_borrower_at_30_september_opens_a_nine_month_cycle(db, tmp_path):
    b = _seed(db, _truth("CIS", None, ["2026-09-30"], "2026-09-30"), tmp_path)
    cycles = db.execute(select(Cycle).where(Cycle.borrower_id == b.id)).scalars().all()
    assert [(c.cycle_type, c.months) for c in cycles] == [("quarterly", 9)]
