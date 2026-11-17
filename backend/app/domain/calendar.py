"""The reporting calendar: dated obligations built from approved terms, and their status."""
import calendar as _cal
import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.calc.terms import Terms
from app.core import ledger
from app.domain.credit import Borrower, Facility
from app.domain.documents import Document
from app.domain.terms import ReportingObligation, TermsVersion

_MONTHS_PER = {"monthly": 1, "quarterly": 3, "semiannual": 6, "annual": 12}


def _month_end(year: int, month: int) -> date:
    return date(year, month, _cal.monthrange(year, month)[1])


def period_ends(frequency: str, start: date, through: date, fiscal_year_end_month: int = 12) -> list[date]:
    """Period ends for a frequency between two dates, aligned to the fiscal year."""
    step = _MONTHS_PER[frequency]
    ends = []
    year, month = start.year, start.month
    while True:
        end = _month_end(year, month)
        if end > through:
            break
        months_into_year = (month - fiscal_year_end_month) % 12
        if end >= start and months_into_year % step == 0:
            ends.append(end)
        month += 1
        if month > 12:
            year, month = year + 1, 1
    return ends


def generate_obligations(db: Session, facility: Facility, version: TermsVersion, *, start: date, through: date) -> int:
    """Create dated obligations from a terms version's reporting requirements. Only approved or
    superseded terms create obligations. Existing rows are left alone. Returns how many were added."""
    if version.status not in ("approved", "superseded"):
        return 0
    borrower = db.get(Borrower, facility.borrower_id)
    terms = Terms.model_validate(version.terms)
    lo = max(start, version.effective_from)
    hi = min(through, version.effective_to) if version.effective_to else through
    added = 0
    for req in terms.reporting_requirements:
        for end in period_ends(req.frequency, lo, hi, borrower.fiscal_year_end_month):
            # quarterly statements are not also due at the fiscal year end when annual ones are
            if req.frequency == "quarterly" and end.month == borrower.fiscal_year_end_month and any(
                    r.frequency == "annual" and r.document_type.startswith("annual") for r in terms.reporting_requirements
            ) and req.document_type == "interim_statements":
                continue
            exists = db.execute(select(ReportingObligation.id).where(
                ReportingObligation.facility_id == facility.id, ReportingObligation.requirement_id == req.id,
                ReportingObligation.period_end == end)).first()
            if exists:
                continue
            db.add(ReportingObligation(
                borrower_id=facility.borrower_id, facility_id=facility.id, terms_version_id=version.id,
                requirement_id=req.id, document_type=req.document_type, period_end=end,
                due_date=end + timedelta(days=req.due_days_after_period_end)))
            added += 1
    db.flush()
    return added


def refresh_statuses(db: Session, today: date) -> int:
    """Mark obligations overdue once their due date has passed. Returns how many changed."""
    changed = 0
    for ob in db.execute(select(ReportingObligation).where(
            ReportingObligation.status == "due", ReportingObligation.due_date < today)).scalars():
        ob.status = "overdue"
        changed += 1
        ledger.record(db, actor_type="system", actor_id="calendar", action="obligation.overdue",
                      entity_type="reporting_obligation", entity_id=ob.id,
                      payload={"document_type": ob.document_type, "period_end": ob.period_end, "due_date": ob.due_date})
    db.flush()
    return changed


def match_document(db: Session, document: Document) -> list[ReportingObligation]:
    """Mark the obligations this document satisfies as received. A document is matched by
    borrower, type and period end; nothing is matched without all three."""
    if document.doc_type is None or document.period_end is None:
        return []
    matched = list(db.execute(select(ReportingObligation).where(
        ReportingObligation.borrower_id == document.borrower_id,
        ReportingObligation.document_type == document.doc_type,
        ReportingObligation.period_end == document.period_end,
        ReportingObligation.status.in_(("due", "overdue")))).scalars())
    for ob in matched:
        ob.status = "received"
        ob.received_document_id = document.id
        ob.received_date = document.received_date
        ledger.record(db, actor_type="system", actor_id="calendar", action="obligation.received",
                      entity_type="reporting_obligation", entity_id=ob.id,
                      payload={"document_id": document.id, "received_date": document.received_date,
                               "days_late": (document.received_date - ob.due_date).days
                               if document.received_date and document.received_date > ob.due_date else 0})
    db.flush()
    return matched


def outstanding(db: Session, borrower_id: uuid.UUID, period_end: date) -> list[ReportingObligation]:
    return list(db.execute(select(ReportingObligation).where(
        ReportingObligation.borrower_id == borrower_id, ReportingObligation.period_end == period_end,
        ReportingObligation.status.in_(("due", "overdue"))).order_by(ReportingObligation.due_date)).scalars())
