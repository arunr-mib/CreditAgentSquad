"""What each stage of the monitoring cycle does. The order of stages and the rule that a stage
waits on its open work items live in `workflow`; this module only does each stage's work.
Importing it registers the handlers."""
from collections.abc import Callable
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents import certificate, collateral, early_warning, intake, spreading
from app.agents import covenant as covenant_agent
from app.agents.llm import LLMClient, client_for
from app.calc import template
from app.calc.periods import is_fiscal_year_end, prior_fiscal_year_end, ytd_months
from app.core import clock
from app.core.config import get_settings
from app.domain import calendar, workflow
from app.domain.cash_reconciliation import reconcile_cash
from app.domain.collateral_service import review_borrowing_base, store_line_availability
from app.domain.covenant_service import governing_terms, run_covenant_tests
from app.domain.credit import Borrower, Facility
from app.domain.documents import Document
from app.domain.facts import Fact
from app.domain.facts_service import current_fact
from app.domain.monitoring import BorrowingBaseReview, CovenantTest, Cycle, CycleStage, WorkItem
from app.domain.reviews import Action
from app.domain.signals_service import run_signals
from app.domain.terms import TermsVersion
from app.domain.terms_service import raise_unapproved_amendments
from app.domain.work_items import raise_item

# Tests replace this to supply scripted model responses.
LLM_FACTORY: Callable[[], LLMClient] = client_for
STATEMENT_TYPES = ("interim_statements", "annual_statements", "monthly_financials")


def _llm() -> LLMClient:
    return LLM_FACTORY()


def _borrower(db: Session, cycle: Cycle) -> Borrower:
    return db.get(Borrower, cycle.borrower_id)


def _documents(db: Session, cycle: Cycle, *types: str) -> list[Document]:
    """Documents for the cycle's period. One a person set aside (rejected) is not used again."""
    return list(db.execute(select(Document).where(
        Document.borrower_id == cycle.borrower_id, Document.period_end == cycle.period_end,
        Document.doc_type.in_(types), Document.status != "rejected").order_by(Document.created_at)).scalars())


def _unfiled(db: Session, cycle: Cycle) -> list[Document]:
    return list(db.execute(select(Document).where(
        Document.borrower_id == cycle.borrower_id, Document.doc_type.is_(None),
        Document.status != "rejected").order_by(Document.created_at)).scalars())


def _review_reading(db: Session, cycle: Cycle, borrower: Borrower, document: Document, stage: str, what: str,
                    run_id) -> None:
    """With autonomy set to assisted, a reading that passed every check still waits for a person.
    Checks written by the people who wrote the reader have been wrong before: three independent
    reviews each found readings that passed and were wrong. One question per document, once."""
    if get_settings().extraction_autonomy.strip().lower() == "automatic":
        return
    key = f"reading.review:{document.id}"
    if db.execute(select(WorkItem.id).where(
            WorkItem.borrower_id == borrower.id, WorkItem.item_type == "reading.review",
            WorkItem.evidence["dedupe_key"].astext == key)).first():
        return  # already asked for this document, whatever was decided
    raise_item(
        db, borrower_id=borrower.id, cycle_id=cycle.id, stage=stage, item_type="reading.review", severity="medium",
        title=f"{borrower.name}: confirm the reading of the {what}",
        question=f"The {what} were read and passed every check. Readings are confirmed by a person before they "
                 "are used. Do the figures agree with the document?",
        allowed_decisions=["reading_confirmed", "request_new_document"], required_permission="confirm_spread",
        evidence={"document_id": str(document.id), "what": what}, agent_run_id=run_id,
        actor=("system", "autonomy"), dedupe_key=key)


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
    wanted = statements_wanted(cycle, borrower)
    documents = _documents(db, cycle, wanted) or _documents(db, cycle, *STATEMENT_TYPES)
    if not documents:
        return "waiting"
    prior_end = prior_fiscal_year_end(cycle.period_end, borrower.fiscal_year_end_month)
    prior_cash = current_fact(db, borrower.id, template.cash_roll_keys(borrower.template_id)[1], prior_end, 0)
    result = spreading.spread_document(
        db, borrower=borrower, document=documents[-1], period_end=cycle.period_end, months=cycle.months,
        cycle=cycle, llm=_llm(), prior_fye_cash=prior_cash.value if prior_cash else None,
        scale_override=st.detail.get("scale_override"))
    st.detail = {**st.detail, "status": result.status, "run_id": str(result.run_id) if result.run_id else None,
                 "unverified": len(result.unverified), "failed_checks": len(result.failed_checks)}
    if result.status == "spread":
        _review_reading(db, cycle, borrower, documents[-1], "spreading", "financial statements", result.run_id)
    # an MRR report and a bank statement share no inputs with the pack: each is read in its own call, whatever
    # became of the pack, and any item it raises blocks the stage on its own. A document already read (every
    # fact on file is verified or confirmed) is not read again when the stage runs again.
    for extra in _documents(db, cycle, "mrr_report", "bank_statement"):
        if _already_read(db, extra):
            continue
        extra_result = spreading.spread_document(
            db, borrower=borrower, document=extra, period_end=cycle.period_end, months=cycle.months,
            cycle=cycle, llm=_llm(), prior_fye_cash=None, scale_override=st.detail.get("scale_override"))
        st.detail = {**st.detail, f"read_{extra.doc_type}_{extra.id}": extra_result.status}
        if extra_result.status == "spread":
            what = "MRR report" if extra.doc_type == "mrr_report" else "bank statement"
            _review_reading(db, cycle, borrower, extra, "spreading", what, extra_result.run_id)
    return "done"


def _already_read(db: Session, document: Document) -> bool:
    facts = list(db.execute(select(Fact.status).where(
        Fact.document_id == document.id, Fact.status != "rejected", Fact.status != "superseded")).scalars())
    return bool(facts) and all(status in ("verified", "confirmed") for status in facts)


@workflow.stage_handler("covenant_testing")
def covenant_stage(db: Session, cycle: Cycle, st: CycleStage) -> str:
    borrower = _borrower(db, cycle)
    facilities = list(db.execute(select(Facility).where(Facility.borrower_id == borrower.id)
                                 .order_by(Facility.code)).scalars())
    governed = {f.id: governing_terms(db, f, cycle.period_end) for f in facilities}
    untestable = loans_without_terms(db, facilities, {fid for fid, (row, _) in governed.items() if row is not None})
    tested = 0
    for facility in facilities:
        store_line_availability(db, borrower=borrower, facility=facility, period_end=cycle.period_end)
        version_row, version = governed[facility.id]
        if version_row is None:
            if facility.id in untestable:
                # nothing can be tested for this loan: a person is asked, once, and the stage waits
                retire_untestable_marker(db, facility, cycle.period_end)
                run_covenant_tests(db, borrower=borrower, facility=facility, period_end=cycle.period_end, cycle=cycle)
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
        if certificates and not already_read and reading.stored:
            _review_reading(db, cycle, borrower, certificates[-1], "covenant_testing", "compliance certificate",
                            reading.run_id)
    # the bank's own statements against the certificate's cash: once the tests (and any covenant item) exist
    reconcile_cash(db, borrower=borrower, cycle=cycle)
    # each breach gets an investigation attached for the person who will decide it. The filter is
    # in Python because the column holds JSON null, which SQL does not treat as NULL.
    investigated = 0
    for item in db.execute(select(WorkItem).where(
            WorkItem.cycle_id == cycle.id, WorkItem.status == "open",
            WorkItem.item_type.in_(covenant_agent.ITEM_TYPES))).scalars():
        if item.recommendation is None:
            covenant_agent.investigate(db, item, _llm())
            investigated += 1
    st.detail = {**st.detail, "tests": tested, "investigations": investigated,
                 "loans_without_approved_terms": len(untestable)}
    return "done"


def loans_without_terms(db: Session, facilities: list[Facility], governed: set) -> set:
    """Loans whose covenants cannot be tested because no approved terms cover the period.

    One agreement's terms are boarded on one of a borrower's loans, so a loan with no terms
    version of its own is covered when a sister loan's approved terms are in force. The gap is a
    loan that has versions on file with none in force (proposed, rejected or expired), or a
    borrower with no approved terms on any loan."""
    with_versions = set(db.execute(select(TermsVersion.facility_id).where(
        TermsVersion.facility_id.in_([f.id for f in facilities]))).scalars())
    gap = {f.id for f in facilities if f.id not in governed and f.id in with_versions}
    if not governed and not gap and facilities:
        gap.add(facilities[0].id)
    return gap


def retire_untestable_marker(db: Session, facility: Facility, period_end: date) -> None:
    """The "no terms in force" record for a loan and period is replaced, not piled up, each time
    the question is looked at again."""
    for old in db.execute(select(CovenantTest).where(
            CovenantTest.facility_id == facility.id, CovenantTest.period_end == period_end,
            CovenantTest.covenant_id == "*", CovenantTest.superseded.is_(False))).scalars():
        old.superseded = True
    db.flush()


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
            question="Some collateral figures could not be verified on the page, so the base was not recalculated. Read the certificate again, or ask the borrower for a new one?",
            allowed_decisions=["retry", "borrower_to_resubmit"],
            evidence={"document_id": str(documents[-1].id), "items": problems}, agent_run_id=reading.run_id,
            actor=("agent", "borrowing_base_reader"), dedupe_key=f"bb.unread:{documents[-1].id}")
        return "done"
    review = review_borrowing_base(
        db, borrower=borrower, facility=facility, period_end=cycle.period_end, ar_rows=reading.ar_rows,
        inventory_rows=reading.inventory_rows, certificate=reading.certificate, outstanding=outstanding.value,
        letters_of_credit=letters, cycle=cycle, require_all_lines=True,
        source={"document_id": str(documents[-1].id), "agent_run_id": str(reading.run_id), "fact_ids": reading.fact_ids})
    st.detail = {**st.detail, "outcome": review.outcome}
    _review_reading(db, cycle, borrower, documents[-1], "borrowing_base", "borrowing base certificate", reading.run_id)
    return "done"


@workflow.stage_handler("signals")
def signals_stage(db: Session, cycle: Cycle, st: CycleStage) -> str:
    fired = run_signals(db, borrower=_borrower(db, cycle), period_end=cycle.period_end, as_of=clock.today(db),
                        cycle=cycle)
    if fired:
        early_warning.explain_signals(db, _borrower(db, cycle), cycle.period_end, _llm())
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
    """Months of the fiscal year elapsed at `period_end` (12 at the year end)."""
    return ytd_months(period_end, fiscal_year_end_month)


def statements_wanted(cycle: Cycle, borrower: Borrower) -> str:
    """The statement a cycle waits for: annual at the fiscal year end (by the borrower's year end,
    not by a month count, which a monthly cycle shares with a quarterly one), monthly statements
    for a monthly cycle, interim statements otherwise."""
    if is_fiscal_year_end(cycle.period_end, borrower.fiscal_year_end_month):
        return "annual_statements"
    return "monthly_financials" if cycle.cycle_type == "monthly" else "interim_statements"


ZERO = Decimal(0)
