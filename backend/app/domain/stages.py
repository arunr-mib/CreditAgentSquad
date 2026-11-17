"""What each stage of the monitoring cycle does. The order of stages and the rule that a stage
waits on its open work items live in `workflow`; this module only does each stage's work.
Importing it registers the handlers."""
from collections.abc import Callable
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents import certificate, collateral, intake, spreading
from app.agents.llm import LLMClient, client_for
from app.calc.periods import prior_fiscal_year_end
from app.core import clock
from app.domain import calendar, workflow
from app.domain.collateral_service import review_borrowing_base, store_line_availability
from app.domain.covenant_service import governing_terms, run_covenant_tests
from app.domain.credit import Borrower, Facility
from app.domain.documents import Document
from app.domain.facts_service import current_fact
from app.domain.monitoring import BorrowingBaseReview, Cycle, CycleStage
from app.domain.reviews import Action
from app.domain.signals_service import run_signals
from app.domain.terms_service import raise_unapproved_amendments
from app.domain.work_items import raise_item

# Tests replace this to supply scripted model responses.
LLM_FACTORY: Callable[[], LLMClient] = client_for
STATEMENT_TYPES = ("interim_statements", "annual_statements")


def _llm() -> LLMClient:
    return LLM_FACTORY()


def _borrower(db: Session, cycle: Cycle) -> Borrower:
    return db.get(Borrower, cycle.borrower_id)


def _documents(db: Session, cycle: Cycle, *types: str) -> list[Document]:
    return list(db.execute(select(Document).where(
        Document.borrower_id == cycle.borrower_id, Document.period_end == cycle.period_end,
        Document.doc_type.in_(types)).order_by(Document.created_at)).scalars())


def _unfiled(db: Session, cycle: Cycle) -> list[Document]:
    return list(db.execute(select(Document).where(
        Document.borrower_id == cycle.borrower_id, Document.doc_type.is_(None),
        Document.status != "rejected").order_by(Document.created_at)).scalars())


@workflow.stage_handler("awaiting_package")
def awaiting_package(db: Session, cycle: Cycle, st: CycleStage) -> str:
    """The package has arrived when any document for the period, or any unfiled document, is on
    file. Until then the stage waits; once reporting is past due a chaser item is raised."""
    if _unfiled(db, cycle) or _documents(db, cycle, *STATEMENT_TYPES, "compliance_certificate"):
        return "done"
    today = clock.today(db)
    calendar.refresh_statuses(db, today)
    if intake.chase_missing(db, borrower=_borrower(db, cycle), cycle=cycle, today=today) is not None:
        # the cycle stops here, but lateness is itself an early warning: fire it now
        run_signals(db, borrower=_borrower(db, cycle), period_end=cycle.period_end, as_of=today, cycle=cycle)
        return "needs_person"
    return "waiting"


@workflow.stage_handler("intake")
def intake_stage(db: Session, cycle: Cycle, st: CycleStage) -> str:
    borrower = _borrower(db, cycle)
    pending = _unfiled(db, cycle)
    if pending:
        result = intake.classify_documents(db, borrower=borrower, documents=pending, llm=_llm(), cycle=cycle,
                                           batch_key=f"{cycle.period_end}")
        st.detail = {**st.detail, "filed": len(result.filed), "run_id": str(result.run_id)}
    today = clock.today(db)
    calendar.refresh_statuses(db, today)
    intake.chase_missing(db, borrower=borrower, cycle=cycle, today=today)
    return "done"


@workflow.stage_handler("spreading")
def spreading_stage(db: Session, cycle: Cycle, st: CycleStage) -> str:
    borrower = _borrower(db, cycle)
    wanted = "annual_statements" if cycle.months == 12 else "interim_statements"
    documents = _documents(db, cycle, wanted) or _documents(db, cycle, *STATEMENT_TYPES)
    if not documents:
        return "waiting"
    prior_end = prior_fiscal_year_end(cycle.period_end, borrower.fiscal_year_end_month)
    prior_cash = current_fact(db, borrower.id, "bs.cash", prior_end, 0)
    result = spreading.spread_document(
        db, borrower=borrower, document=documents[-1], period_end=cycle.period_end, months=cycle.months,
        cycle=cycle, llm=_llm(), prior_fye_cash=prior_cash.value if prior_cash else None)
    st.detail = {**st.detail, "status": result.status, "run_id": str(result.run_id) if result.run_id else None,
                 "unverified": len(result.unverified), "failed_checks": len(result.failed_checks)}
    return "done"


@workflow.stage_handler("covenant_testing")
def covenant_stage(db: Session, cycle: Cycle, st: CycleStage) -> str:
    borrower = _borrower(db, cycle)
    facilities = list(db.execute(select(Facility).where(Facility.borrower_id == borrower.id)).scalars())
    tested = 0
    for facility in facilities:
        store_line_availability(db, borrower=borrower, facility=facility, period_end=cycle.period_end)
        version_row, version = governing_terms(db, facility, cycle.period_end)
        if version_row is None:
            continue
        raise_unapproved_amendments(db, facility, cycle_id=cycle.id)
        certificates = _documents(db, cycle, "compliance_certificate")
        already_read = any(current_fact(db, borrower.id, f"cert.{c.id}.value", cycle.period_end, 0)
                           for c in version.terms.covenants)
        if certificates and not already_read:
            reading = certificate.read_certificate(db, borrower=borrower, document=certificates[-1],
                                                   period_end=cycle.period_end, terms=version.terms, cycle=cycle,
                                                   llm=_llm())
            if reading.unverified:
                raise_item(
                    db, borrower_id=borrower.id, facility_id=facility.id, cycle_id=cycle.id, stage="covenant_testing",
                    item_type="spread.value_unverified", severity="medium", blocks_stage=False,
                    title=f"{borrower.name}: parts of the compliance certificate could not be verified",
                    question="Some reported covenant figures could not be found on the certificate as read. Confirm what the borrower reported?",
                    allowed_decisions=["values_confirmed", "request_new_document"], required_permission="confirm_spread",
                    evidence={"document_id": str(certificates[-1].id), "items": reading.unverified},
                    agent_run_id=reading.run_id, actor=("agent", "certificate_reader"),
                    dedupe_key=f"certificate.unverified:{certificates[-1].id}")
        tested += len(run_covenant_tests(db, borrower=borrower, facility=facility, period_end=cycle.period_end,
                                         cycle=cycle))
    st.detail = {**st.detail, "tests": tested}
    return "done"


@workflow.stage_handler("borrowing_base")
def borrowing_base_stage(db: Session, cycle: Cycle, st: CycleStage) -> str:
    borrower = _borrower(db, cycle)
    facility = db.execute(select(Facility).where(
        Facility.borrower_id == borrower.id, Facility.has_borrowing_base.is_(True))).scalars().first()
    if facility is None:
        return "skipped"
    if db.execute(select(BorrowingBaseReview.id).where(
            BorrowingBaseReview.facility_id == facility.id, BorrowingBaseReview.period_end == cycle.period_end,
            BorrowingBaseReview.origin == "live")).first():
        return "done"
    documents = _documents(db, cycle, "borrowing_base_certificate")
    if not documents:
        return "waiting"
    reading = collateral.read_collateral(db, borrower=borrower, document=documents[-1], period_end=cycle.period_end,
                                         cycle=cycle, llm=_llm())
    outstanding = current_fact(db, borrower.id, "sys.revolver_outstanding", cycle.period_end, 0)
    letters = reading.certificate.get("letters_of_credit")
    problems = list(reading.unverified)
    if outstanding is None:
        problems.append({"what": "outstanding", "reason": "no balance in the system of record for this date"})
    if letters is None:
        problems.append({"what": "letters_of_credit", "reason": "not verified on the certificate"})
    if problems or not reading.usable:
        raise_item(
            db, borrower_id=borrower.id, facility_id=facility.id, cycle_id=cycle.id, stage="borrowing_base",
            item_type="bb.certificate_mismatch", severity="medium",
            title=f"{borrower.name}: the borrowing base certificate could not be read in full",
            question="Some collateral figures could not be verified on the page, so the base was not recalculated. Correct them, or request a new certificate?",
            allowed_decisions=["listing_corrected", "borrower_to_resubmit"],
            evidence={"document_id": str(documents[-1].id), "items": problems}, agent_run_id=reading.run_id,
            actor=("agent", "borrowing_base_reader"), dedupe_key=f"bb.unread:{documents[-1].id}")
        return "done"
    review = review_borrowing_base(
        db, borrower=borrower, facility=facility, period_end=cycle.period_end, ar_rows=reading.ar_rows,
        inventory_rows=reading.inventory_rows, certificate=reading.certificate, outstanding=outstanding.value,
        letters_of_credit=letters, cycle=cycle,
        source={"document_id": str(documents[-1].id), "agent_run_id": str(reading.run_id), "fact_ids": reading.fact_ids})
    st.detail = {**st.detail, "outcome": review.outcome}
    return "done"


@workflow.stage_handler("signals")
def signals_stage(db: Session, cycle: Cycle, st: CycleStage) -> str:
    fired = run_signals(db, borrower=_borrower(db, cycle), period_end=cycle.period_end, as_of=clock.today(db),
                        cycle=cycle)
    st.detail = {**st.detail, "signals": len(fired)}
    return "done"


@workflow.stage_handler("review_prep")
def review_prep_stage(db: Session, cycle: Cycle, st: CycleStage) -> str:
    from app.domain.review_service import prepare_review

    prepare_review(db, cycle=cycle, llm=_llm())
    return "done"


@workflow.stage_handler("in_review")
def in_review_stage(db: Session, cycle: Cycle, st: CycleStage) -> str:
    return "done"  # the review sheet was approved by a person to leave review preparation


@workflow.stage_handler("actions_open")
def actions_stage(db: Session, cycle: Cycle, st: CycleStage) -> str:
    open_actions = db.execute(select(Action.id).where(
        Action.cycle_id == cycle.id, Action.status.in_(("open", "in_progress")))).all()
    st.detail = {**st.detail, "open_actions": len(open_actions)}
    return "waiting" if open_actions else "done"


@workflow.stage_handler("closed")
def closed_stage(db: Session, cycle: Cycle, st: CycleStage) -> str:
    return "done"


def quarter_months(period_end: date, fiscal_year_end_month: int) -> int:
    return ((period_end.month - fiscal_year_end_month) % 12) or 12


ZERO = Decimal(0)
