"""Borrowers, loans, documents, facts and the spread grid."""
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import PageNumber, current_user, require
from app.api.disposition import content_disposition
from app.api.routes_ui import _Labels, _summary
from app.api.serialize import plain, row
from app.calc import template
from app.core import ledger
from app.core.clock import today
from app.core.config import MAX_UPLOAD_BYTES
from app.core.db import get_db
from app.core.roles import Permission
from app.domain import corrections, facts_service, lessons, terms_service
from app.domain.credit import Borrower, Facility
from app.domain.documents import Document, DocumentPage
from app.domain.documents_service import DocumentRefused, ingest_document, read_file
from app.domain.facts import CalcRun, Fact
from app.domain.funding import KINDS as FUNDING_KINDS
from app.domain.funding import FundingEvent, update_funding_event, valid_evidence
from app.domain.monitoring import CovenantTest, Cycle, Signal, WorkItem
from app.domain.org import User

router = APIRouter(tags=["credit"])


def _borrower_or_404(db: Session, borrower_id: uuid.UUID) -> Borrower:
    borrower = db.get(Borrower, borrower_id)
    if borrower is None:
        raise HTTPException(404, "Borrower not found.")
    return borrower


@router.get("/borrowers")
def list_borrowers(db: Session = Depends(get_db), _: User = Depends(current_user)) -> list[dict]:
    open_items = dict(db.execute(select(WorkItem.borrower_id, func.count()).where(WorkItem.status == "open")
                                 .group_by(WorkItem.borrower_id)).all())
    open_signals = dict(db.execute(select(Signal.borrower_id, func.count()).where(Signal.status == "open")
                                   .group_by(Signal.borrower_id)).all())
    commitments = dict(db.execute(select(Facility.borrower_id, func.sum(Facility.commitment))
                                  .group_by(Facility.borrower_id)).all())
    users = {u.id: u.name for u in db.execute(select(User)).scalars()}
    latest_cycle: dict[uuid.UUID, Cycle] = {}
    for cycle in db.execute(select(Cycle).order_by(Cycle.period_end)).scalars():
        latest_cycle[cycle.borrower_id] = cycle
    worst: dict[uuid.UUID, str] = {}
    rank = {"breach_reported_compliant": 4, "breach": 3, "cannot_test": 2, "compliant_variance": 1, "compliant": 0}
    for test in db.execute(select(CovenantTest).where(CovenantTest.superseded.is_(False))).scalars():
        cycle = latest_cycle.get(test.borrower_id)
        if cycle is not None and test.period_end == cycle.period_end:
            if rank.get(test.outcome, 0) >= rank.get(worst.get(test.borrower_id, "compliant"), 0):
                worst[test.borrower_id] = test.outcome
    tightest = _tightest_headroom(db, latest_cycle)
    labels = _Labels(db)
    out = []
    for b in db.execute(select(Borrower).order_by(Borrower.name)).scalars():
        cycle = latest_cycle.get(b.id)
        headroom = tightest.get(b.id)
        out.append({
            **row(b, exclude=("profile",)),
            "relationship_manager": users.get(b.relationship_manager_id), "analyst": users.get(b.analyst_id),
            "total_commitment": plain(commitments.get(b.id)), "open_work_items": open_items.get(b.id, 0),
            "open_signals": open_signals.get(b.id, 0),
            "latest_cycle": {"id": str(cycle.id), "period_end": cycle.period_end.isoformat(), "stage": cycle.stage,
                             "status": cycle.status} if cycle else None,
            "covenant_status": worst.get(b.id),
            "tightest_headroom": _summary(headroom, labels) if headroom else None,
        })
    return out


def _tightest_headroom(db: Session, latest_cycle: dict[uuid.UUID, Cycle]) -> dict[uuid.UUID, Fact]:
    """Per borrower, the stored headroom fact with the lowest value among the covenant tests in
    force for the latest cycle's period. Nothing is calculated here: the fact is chosen, not made.
    A test with no stored headroom (it could not be tested) is left out, never read as zero."""
    stored: dict[tuple[uuid.UUID, str, date], Fact] = {}
    for fact in db.execute(select(Fact).where(Fact.key.like("cov.%.headroom_pct"),
                                              Fact.status.in_(("verified", "confirmed")))
                           .order_by(Fact.seq)).scalars():
        stored[(fact.borrower_id, fact.key, fact.period_end)] = fact
    tightest: dict[uuid.UUID, Fact] = {}
    for test in db.execute(select(CovenantTest).where(CovenantTest.superseded.is_(False))
                           .order_by(CovenantTest.covenant_id)).scalars():
        cycle = latest_cycle.get(test.borrower_id)
        if cycle is None or test.period_end != cycle.period_end:
            continue
        fact = stored.get((test.borrower_id, f"cov.{test.covenant_id}.headroom_pct", test.period_end))
        if fact is not None and (test.borrower_id not in tightest or fact.value < tightest[test.borrower_id].value):
            tightest[test.borrower_id] = fact
    return tightest


@router.get("/borrowers/{borrower_id}")
def get_borrower(borrower_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(current_user)) -> dict:
    b = _borrower_or_404(db, borrower_id)
    facilities = db.execute(select(Facility).where(Facility.borrower_id == b.id).order_by(Facility.code)).scalars()
    users = {u.id: u.name for u in db.execute(select(User)).scalars()}
    return {**row(b), "relationship_manager": users.get(b.relationship_manager_id), "analyst": users.get(b.analyst_id),
            "facilities": [row(f) for f in facilities]}


class FundingEventIn(BaseModel):
    kind: str
    amount: Decimal = Field(gt=0, max_digits=20, decimal_places=2)
    expected_close: date
    evidence_document_ids: list[str] = Field(default_factory=list)


@router.get("/borrowers/{borrower_id}/funding-events")
def list_funding_events(borrower_id: uuid.UUID, db: Session = Depends(get_db),
                        _: User = Depends(require(Permission.VIEW))) -> list[dict]:
    _borrower_or_404(db, borrower_id)
    events = db.execute(select(FundingEvent).where(FundingEvent.borrower_id == borrower_id)
                        .order_by(FundingEvent.expected_close, FundingEvent.created_at)).scalars()
    return [row(e) for e in events]


@router.post("/borrowers/{borrower_id}/funding-events", status_code=201)
def record_funding_event(borrower_id: uuid.UUID, body: FundingEventIn, db: Session = Depends(get_db),
                         user: User = Depends(require(Permission.PREPARE_TERMS))) -> dict:
    _borrower_or_404(db, borrower_id)
    if body.kind not in FUNDING_KINDS:
        raise HTTPException(422, f"Funding kind must be one of: {', '.join(FUNDING_KINDS)}.")
    try:
        evidence = valid_evidence(db, borrower_id, body.evidence_document_ids)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    event = FundingEvent(borrower_id=borrower_id, kind=body.kind, amount=body.amount,
                         expected_close=body.expected_close, status="expected",
                         evidence_document_ids=evidence)
    db.add(event)
    db.flush()
    ledger.record(db, actor_type="user", actor_id=str(user.id), action="funding_event.recorded",
                  entity_type="funding_event", entity_id=event.id,
                  payload={"borrower_id": borrower_id, "kind": event.kind, "amount": event.amount,
                           "expected_close": event.expected_close})
    db.commit()
    return row(event)


class FundingEventPatch(BaseModel):
    status: str | None = None
    expected_close: date | None = None
    evidence_document_ids: list[str] = Field(default_factory=list)  # added to what is there


@router.patch("/borrowers/{borrower_id}/funding-events/{event_id}")
def update_funding_event_route(borrower_id: uuid.UUID, event_id: uuid.UUID, body: FundingEventPatch,
                               db: Session = Depends(get_db),
                               user: User = Depends(require(Permission.PREPARE_TERMS))) -> dict:
    """Move an event along its lifecycle, change its close date, or add evidence. Closed is final."""
    _borrower_or_404(db, borrower_id)
    event = db.get(FundingEvent, event_id)
    if event is None or event.borrower_id != borrower_id:
        raise HTTPException(404, "Funding event not found.")
    try:
        update_funding_event(db, event, status=body.status, expected_close=body.expected_close,
                             add_evidence=body.evidence_document_ids, actor=("user", str(user.id)))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    return row(event)


class LessonIn(BaseModel):
    borrower_id: uuid.UUID
    topic: str = Field(min_length=1, max_length=48)
    text: str = Field(max_length=2000)
    work_item_id: uuid.UUID | None = None
    tag: str | None = Field(default=None, max_length=48)


@router.post("/lessons", status_code=201)
def record_lesson_route(body: LessonIn, db: Session = Depends(get_db),
                        user: User = Depends(require(Permission.DECIDE_WORK_ITEM))) -> dict:
    """A person teaches once: their own words become precedent for later cases. The author is the
    signed-in user, never named in the body."""
    _borrower_or_404(db, body.borrower_id)
    if body.work_item_id is not None:
        item = db.get(WorkItem, body.work_item_id)
        if item is None:
            raise HTTPException(404, "Work item not found.")
        if item.borrower_id != body.borrower_id:
            raise HTTPException(422, "That work item belongs to a different borrower.")
    try:
        lesson = lessons.record_lesson(db, borrower_id=body.borrower_id, topic=body.topic, text=body.text,
                                       written_by=user.id, work_item_id=body.work_item_id, tag=body.tag)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    return {"id": str(lesson.id)}


@router.get("/borrowers/{borrower_id}/documents")
def list_documents(borrower_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(current_user)) -> list[dict]:
    _borrower_or_404(db, borrower_id)
    docs = db.execute(select(Document).where(Document.borrower_id == borrower_id)
                      .order_by(Document.received_date.desc().nulls_last(), Document.created_at.desc())).scalars()
    return [row(d, exclude=("storage_path",)) for d in docs]


@router.post("/borrowers/{borrower_id}/documents", status_code=201)
async def upload_document(
    borrower_id: uuid.UUID, file: UploadFile = File(...), title: str | None = Form(default=None),
    db: Session = Depends(get_db), user: User = Depends(require(Permission.UPLOAD_DOCUMENT)),
) -> dict:
    _borrower_or_404(db, borrower_id)
    # read no more than the limit plus one byte: enough to know the file is too large
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"The file is larger than the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit "
                                 "for an upload.")
    try:
        doc = ingest_document(db, borrower_id=borrower_id, data=data, file_name=file.filename or "upload.pdf",
                               title=title, received_date=today(db), uploaded_by=user.id, actor=("user", str(user.id)))
    except DocumentRefused as exc:
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    return row(doc, exclude=("storage_path",))


@router.get("/documents/{document_id}")
def get_document(document_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(current_user)) -> dict:
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found.")
    cited = db.execute(select(Fact.page, func.count()).where(Fact.document_id == doc.id).group_by(Fact.page)).all()
    return {**row(doc, exclude=("storage_path",)), "facts_by_page": {str(p): n for p, n in cited if p}}


SHEET_MEDIA = {"xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "csv": "text/csv"}


@router.get("/documents/{document_id}/file")
def get_document_file(document_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(current_user)) -> Response:
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found.")
    sheet = SHEET_MEDIA.get((doc.meta or {}).get("format"))
    if sheet is not None:  # a spreadsheet is downloaded, never rendered in the browser
        return Response(read_file(doc), media_type=sheet,
                        headers={"Content-Disposition": content_disposition("attachment", doc.file_name)})
    return Response(read_file(doc), media_type="application/pdf",
                    headers={"Content-Disposition": content_disposition("inline", doc.file_name)})


@router.get("/documents/{document_id}/pages/{page_number}")
def get_document_page(document_id: uuid.UUID, page_number: PageNumber, db: Session = Depends(get_db),
                      _: User = Depends(current_user)) -> dict:
    page = db.execute(select(DocumentPage).where(
        DocumentPage.document_id == document_id, DocumentPage.page_number == page_number)).scalar_one_or_none()
    if page is None:
        raise HTTPException(404, "Page not found.")
    facts = db.execute(select(Fact).where(Fact.document_id == document_id, Fact.page == page_number)).scalars()
    return {"page_number": page.page_number, "width": page.width, "height": page.height, "has_text": page.has_text,
            "text": page.text,
            "citations": [{"fact_id": str(f.id), "key": f.key, "bbox": f.bbox, "quote": f.quote,
                           "label": f.label_text, "status": f.status, "value": plain(f.value)} for f in facts]}


def fact_out(db: Session, fact: Fact, *, with_lineage: bool = False) -> dict:
    out = row(fact)
    if fact.document_id:
        doc = db.get(Document, fact.document_id)
        out["document"] = {"id": str(doc.id), "title": doc.title, "doc_type": doc.doc_type} if doc else None
    if with_lineage and fact.calc_run_id:
        calc = db.get(CalcRun, fact.calc_run_id)
        if calc is not None:
            out["calculation"] = row(calc)
    return out


@router.get("/facts/{fact_id}")
def get_fact(fact_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(current_user)) -> dict:
    """One fact with everything behind it: the page and quote, or the calculation and its inputs."""
    fact = db.get(Fact, fact_id)
    if fact is None:
        raise HTTPException(404, "Fact not found.")
    out = fact_out(db, fact, with_lineage=True)
    history = []
    cursor = fact
    while cursor.supersedes_fact_id:
        cursor = db.get(Fact, cursor.supersedes_fact_id)
        if cursor is None:
            break
        history.append(row(cursor, only=("id", "value", "kind", "status", "created_at", "reason")))
    out["history"] = history
    return out


@router.get("/borrowers/{borrower_id}/spread")
def get_spread(borrower_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(current_user)) -> dict:
    """The spread grid: template lines down, periods across, one current fact per cell."""
    borrower = _borrower_or_404(db, borrower_id)
    facts = db.execute(select(Fact).where(
        Fact.borrower_id == borrower_id, Fact.status.in_(("verified", "confirmed", "proposed")))
        .order_by(Fact.seq)).scalars()
    cells: dict[str, dict[str, dict]] = {}
    periods: set[tuple[date, int]] = set()
    for f in facts:
        base = f.key[len(template.STATED_PREFIX):] if f.key.startswith(template.STATED_PREFIX) else f.key
        if not template.in_template(base, borrower.template_id) or f.key.startswith(template.STATED_PREFIX):
            continue
        usable = f.status in ("verified", "confirmed")
        period_key = f.period_end.isoformat()
        current = cells.setdefault(f.key, {}).get(period_key)
        if current is None or usable or not current["usable"]:
            cells[f.key][period_key] = {"fact_id": str(f.id), "value": plain(f.value), "kind": f.kind,
                                        "status": f.status, "usable": usable}
        if f.months:
            periods.add((f.period_end, f.months))
    return {
        "template": borrower.template_id,
        "periods": [{"period_end": p.isoformat(), "months": m} for p, m in sorted(periods)],
        "lines": [{"key": line.key, "label": line.label, "statement": line.statement, "computed": line.computed,
                   "cells": cells.get(line.key, {})} for line in template.template_lines(borrower.template_id)],
    }


@router.get("/borrowers/{borrower_id}/covenant-tests")
def list_covenant_tests(borrower_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(current_user)) -> list[dict]:
    _borrower_or_404(db, borrower_id)
    tests = db.execute(select(CovenantTest).where(
        CovenantTest.borrower_id == borrower_id, CovenantTest.superseded.is_(False))
        .order_by(CovenantTest.period_end.desc(), CovenantTest.covenant_name)).scalars()
    return [row(t) for t in tests]


@router.get("/covenant-tests/{test_id}")
def get_covenant_test(test_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(current_user)) -> dict:
    test = db.get(CovenantTest, test_id)
    if test is None:
        raise HTTPException(404, "Covenant test not found.")
    out = row(test)
    if test.calc_run_id:
        calc = db.get(CalcRun, test.calc_run_id)
        out["calculation"] = row(calc) if calc else None
    return out


class TermsIn(BaseModel):
    terms: dict[str, Any]
    effective_from: date
    source_document_ids: list[str] = Field(default_factory=list)


@router.post("/facilities/{facility_id}/terms", status_code=201)
def board_terms(facility_id: uuid.UUID, body: TermsIn, db: Session = Depends(get_db),
                user: User = Depends(require(Permission.PREPARE_TERMS))) -> dict:
    """A person boards a loan's terms by hand. They are stored as a proposed version, checked
    like any other, and govern a test only after a different person approves them."""
    facility = db.get(Facility, facility_id)
    if facility is None:
        raise HTTPException(404, "Loan not found.")
    # a cycle waiting on the question "board the terms by hand?" also waits for their approval
    waiting = db.execute(select(WorkItem).where(
        WorkItem.facility_id == facility.id, WorkItem.status == "open", WorkItem.cycle_id.is_not(None),
        WorkItem.evidence["dedupe_key"].astext == f"terms.extraction:{facility.id}")).scalars().first()
    try:
        version, item = terms_service.propose_terms(
            db, facility=facility, terms=body.terms, effective_from=body.effective_from,
            source_document_ids=body.source_document_ids, prepared_by=("user", str(user.id)),
            cycle_id=waiting.cycle_id if waiting is not None else None)
    except terms_service.TermsRefused as exc:
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    return {**row(version), "approval_item_id": str(item.id)}


class FactReasonIn(BaseModel):
    reason: str = ""


class FactCorrectIn(BaseModel):
    value: str
    reason: str


class ManualFactIn(BaseModel):
    key: str
    period_end: date
    months: int
    value: str
    reason: str
    read_from_fact_id: uuid.UUID | None = None  # the reading this figure was taken from; its page is cited


_LARGEST_FIGURE = Decimal(10) ** 18  # figures are stored with 18 digits before the point and 6 after


def _decimal(text: str) -> Decimal:
    """A figure typed by a person: a plain finite number that can be stored exactly as typed."""
    try:
        value = Decimal(text.replace(",", "").strip())
    except (InvalidOperation, AttributeError) as exc:
        raise HTTPException(422, "The value is not a number.") from exc
    if not value.is_finite():
        raise HTTPException(422, "The value must be a finite number; NaN and Infinity are not figures.")
    if abs(value) >= _LARGEST_FIGURE:
        raise HTTPException(422, "The value is too large to store.")
    if value != value.quantize(Decimal("0.000001")):
        raise HTTPException(422, "The value has more than six decimal places.")
    return value


def _fact_or_404(db: Session, fact_id: uuid.UUID) -> Fact:
    fact = db.get(Fact, fact_id)
    if fact is None:
        raise HTTPException(404, "Fact not found.")
    return fact


def _owns_client(db: Session, borrower_id: uuid.UUID, user: User) -> None:
    """The engine's ownership rule (`workflow.client_refusal`): another analyst's client is refused with 403."""
    from app.domain.workflow import client_refusal

    refused = client_refusal(db, borrower_id, user_id=user.id, user_role=user.role)
    if refused is not None:
        raise HTTPException(403, str(refused))


@router.post("/facts/{fact_id}/confirm")
def confirm_fact_route(fact_id: uuid.UUID, db: Session = Depends(get_db),
                       user: User = Depends(require(Permission.CONFIRM_SPREAD))) -> dict:
    """A person accepts a figure held for review exactly as it was read."""
    fact = _fact_or_404(db, fact_id)
    _owns_client(db, fact.borrower_id, user)
    try:
        facts_service.confirm_fact(db, fact, user.id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    return fact_out(db, fact)


@router.post("/facts/{fact_id}/correct")
def correct_fact_route(fact_id: uuid.UUID, body: FactCorrectIn, db: Session = Depends(get_db),
                       user: User = Depends(require(Permission.CONFIRM_SPREAD))) -> dict:
    """A person replaces a figure. The old fact is kept and marked superseded."""
    fact = _fact_or_404(db, fact_id)
    _owns_client(db, fact.borrower_id, user)
    try:
        new, recalculation = corrections.correct(db, fact, value=_decimal(body.value), user_id=user.id,
                                                 reason=body.reason)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    return {**fact_out(db, new), "recalculation": recalculation}


@router.post("/facts/{fact_id}/reject")
def reject_fact_route(fact_id: uuid.UUID, body: FactReasonIn, db: Session = Depends(get_db),
                      user: User = Depends(require(Permission.CONFIRM_SPREAD))) -> dict:
    fact = _fact_or_404(db, fact_id)
    _owns_client(db, fact.borrower_id, user)
    if not body.reason.strip():
        raise HTTPException(422, "Rejecting a figure needs a reason.")
    try:
        recalculation = corrections.reject(db, fact, user_id=user.id, reason=body.reason)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    return {**fact_out(db, fact), "recalculation": recalculation}


@router.post("/borrowers/{borrower_id}/facts", status_code=201)
def enter_fact(borrower_id: uuid.UUID, body: ManualFactIn, db: Session = Depends(get_db),
               user: User = Depends(require(Permission.CONFIRM_SPREAD))) -> dict:
    """A person keys a statement figure by hand: a template input line, with a reason."""
    borrower = _borrower_or_404(db, borrower_id)
    _owns_client(db, borrower.id, user)
    line = next((ln for ln in template.template_lines(borrower.template_id) if ln.key == body.key), None)
    if line is None or line.computed:
        raise HTTPException(422, "Only input lines of the spreading template can be entered; totals are calculated.")
    if not body.reason.strip():
        raise HTTPException(422, "Entering a figure by hand needs a reason.")
    if line.flow and body.months not in (3, 6, 9, 12):
        raise HTTPException(422, "A flow line needs the number of months in the period: 3, 6, 9 or 12.")
    read_from = None
    if body.read_from_fact_id is not None:
        read_from = db.get(Fact, body.read_from_fact_id)
        if (read_from is None or read_from.borrower_id != borrower_id or read_from.period_end != body.period_end
                or read_from.document_id is None or read_from.page is None):
            raise HTTPException(422, "The reading named as the source is not a figure read from a document page "
                                     "for this borrower and period.")
    try:
        fact, recalculation = corrections.enter(
            db, borrower_id=borrower_id, key=body.key, period_end=body.period_end,
            months=body.months if line.flow else 0, value=_decimal(body.value), user_id=user.id, reason=body.reason,
            read_from=read_from)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    return {**fact_out(db, fact), "recalculation": recalculation}
