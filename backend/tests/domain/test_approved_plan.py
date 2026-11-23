"""The revenue plan behind `revenue_below_plan` comes from approved terms, and only from approved terms."""
from datetime import UTC, date, datetime

from app.domain.credit import Borrower, Facility
from app.domain.org import User
from app.domain.signals_service import approved_plan
from app.domain.terms import TermsVersion

OCT = date(2026, 10, 31)


def covenant(amounts: dict[str, str], metric: str = "revenue") -> dict:
    return {"id": "revenue_vs_plan", "name": "Revenue to Plan", "archetype": "revenue_vs_plan",
            "params": {"metric": metric, "plan": [{"period_end": k, "amount": v} for k, v in amounts.items()]},
            "test": {"operator": ">=", "threshold": "0.80", "steps": [], "unit": "pct"},
            "measurement": {"basis": "t3m", "frequency": "monthly"}, "rounding": {"dp": 4, "mode": "half_up"},
            "citations": []}


def setup(db, code, versions):
    """versions: [(status, covenant dict)] in version order, all effective from 2025-01-01."""
    b = Borrower(code=code, name="Meridew Analytics", template_id="vc-1")
    db.add(b)
    user = User(email=f"{code}@x.example", name="A", role="credit_officer", password_hash="x")
    db.add(user)
    db.flush()
    facility = Facility(borrower_id=b.id, code=f"{code}-VL", name="Venture Term Loan", facility_type="term_loan",
                        commitment=3_000_000)
    db.add(facility)
    db.flush()
    for number, (status, cov) in enumerate(versions, start=1):
        approved = status == "approved"
        db.add(TermsVersion(
            facility_id=facility.id, version=number, status=status, effective_from=date(2025, 1, 1),
            approved_by=user.id if approved else None, approved_at=datetime.now(UTC) if approved else None,
            terms={"definitions": {}, "covenants": [cov], "reporting_requirements": [], "borrowing_base": None}))
    db.flush()
    return b


def test_the_plan_is_read_from_the_approved_terms_as_decimals(db):
    b = setup(db, "PLAN1", [("approved", covenant({"2026-09-30": "800000", "2026-10-31": "850000"}))])
    plan = approved_plan(db, b, OCT)
    assert plan == {date(2026, 9, 30): 800000, date(2026, 10, 31): 850000}
    assert all(type(v).__name__ == "Decimal" for v in plan.values())


def test_a_proposed_version_never_supplies_a_plan(db):
    b = setup(db, "PLAN2", [("proposed", covenant({"2026-10-31": "850000"}))])
    assert approved_plan(db, b, OCT) is None


def test_an_arr_covenant_and_a_borrower_with_no_plan_give_no_revenue_plan(db):
    arr = setup(db, "PLAN3", [("approved", covenant({"2026-10-31": "9000000"}, metric="arr"))])
    assert approved_plan(db, arr, OCT) is None
    bare = Borrower(code="PLAN4", name="Ferrogate Cloud", template_id="vc-1")
    db.add(bare)
    db.flush()
    assert approved_plan(db, bare, OCT) is None
