"""How often a borrower reports, and the period ends that follow from it."""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.calc.terms import Terms
from app.domain.calendar import period_ends
from app.domain.credit import Borrower, Facility
from app.domain.terms import TermsVersion

TEMPLATE_DEFAULT = {"vc-1": "monthly", "ci-1": "quarterly"}
# the financial statements that set the pace of a cycle; annual statements alone do not: the
# year end is always a period end, and the cycle for it is the quarter or month that ends there
_PACE_TYPES = {"monthly_financials", "interim_statements"}
_STEPS = {"monthly": 1, "quarterly": 3, "semiannual": 6, "annual": 12}


def reporting_frequency(db: Session, borrower: Borrower, as_of: date) -> str:
    """The finest frequency of financial statements in the borrower's approved reporting
    requirements in force on `as_of`; the template's default when none are approved."""
    found: list[str] = []
    for facility in db.execute(select(Facility).where(Facility.borrower_id == borrower.id)).scalars():
        version = db.execute(select(TermsVersion).where(
            TermsVersion.facility_id == facility.id, TermsVersion.status.in_(("approved", "superseded")),
            TermsVersion.effective_from <= as_of).order_by(TermsVersion.effective_from.desc(),
                                                           TermsVersion.version.desc())).scalars().first()
        if version is None:
            continue
        for req in Terms.model_validate(version.terms).reporting_requirements:
            if req.document_type in _PACE_TYPES:
                found.append(req.frequency)
    if found:
        return min(found, key=_STEPS.__getitem__)
    return TEMPLATE_DEFAULT[borrower.template_id]


def step_months(db: Session, borrower: Borrower, as_of: date) -> int:
    return _STEPS[reporting_frequency(db, borrower, as_of)]


def period_ends_for(db: Session, borrower: Borrower, from_date: date, to_date: date) -> list[date]:
    """Period ends from `from_date` to `to_date` (inclusive), aligned to the borrower's fiscal year."""
    frequency = reporting_frequency(db, borrower, to_date)
    return period_ends(frequency, from_date, to_date, borrower.fiscal_year_end_month)
