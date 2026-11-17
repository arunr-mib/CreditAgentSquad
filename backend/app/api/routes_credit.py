"""Borrowers, loans, documents, facts and the spread grid."""
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import current_user, require
from app.api.serialize import plain, row
from app.calc import template
from app.core.clock import today
from app.core.db import get_db
from app.core.roles import Permission
from app.domain import corrections, facts_service
from app.domain.credit import Borrower, Facility
from app.domain.documents import Document, DocumentPage
from app.domain.documents_service import DocumentRefused, ingest_pdf, read_file
from app.domain.facts import CalcRun, Fact
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
    out = []
    for b in db.execute(select(Borrower).order_by(Borrower.name)).scalars():
        cycle = latest_cycle.get(b.id)
        out.append({
            **row(b, exclude=("profile",)),
            "relationship_manager": users.get(b.relationship_manager_id), "analyst": users.get(b.analyst_id),
            "total_commitment": plain(commitments.get(b.id)), "open_work_items": open_items.get(b.id, 0),
            "open_signals": open_signals.get(b.id, 0),
            "latest_cycle": {"id": str(cycle.id), "period_end": cycle.period_end.isoformat(), "stage": cycle.stage,
                             "status": cycle.status} if cycle else None,
            "covenant_status": worst.get(b.id),
        })
    return out


@router.get("/borrowers/{borrower_id}")
def get_borrower(borrower_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(current_user)) -> dict:
    b = _borrower_or_404(db, borrower_id)
    facilities = db.execute(select(Facility).where(Facility.borrower_id == b.id).order_by(Facility.code)).scalars()
    users = {u.id: u.name for u in db.execute(select(User)).scalars()}
    return {**row(b), "relationship_manager": users.get(b.relationship_manager_id), "analyst": users.get(b.analyst_id),
            "facilities": [row(f) for f in facilities]}


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
    data = await file.read()
    try:
        doc = ingest_pdf(db, borrower_id=borrower_id, data=data, file_name=file.filename or "upload.pdf",
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


@router.get("/documents/{document_id}/file")
def get_document_file(document_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(current_user)) -> Response:
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found.")
    return Response(read_file(doc), media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{doc.file_name}"'})


@router.get("/documents/{document_id}/pages/{page_number}")
def get_document_page(document_id: uuid.UUID, page_number: int, db: Session = Depends(get_db),
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
    _borrower_or_404(db, borrower_id)
    facts = db.execute(select(Fact).where(
        Fact.borrower_id == borrower_id, Fact.status.in_(("verified", "confirmed", "proposed")))
        .order_by(Fact.seq)).scalars()
    cells: dict[str, dict[str, dict]] = {}
    periods: set[tuple[date, int]] = set()
    for f in facts:
        base = f.key[len(template.STATED_PREFIX):] if f.key.startswith(template.STATED_PREFIX) else f.key
        if base not in template.LINE_BY_KEY or f.key.startswith(template.STATED_PREFIX):
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
        "template": template.TEMPLATE_ID,
        "periods": [{"period_end": p.isoformat(), "months": m} for p, m in sorted(periods)],
        "lines": [{"key": line.key, "label": line.label, "statement": line.statement, "computed": line.computed,
                   "cells": cells.get(line.key, {})} for line in template.LINES],
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


def _decimal(text: str) -> Decimal:
    try:
        return Decimal(text.replace(",", ""))
    except (InvalidOperation, AttributeError) as exc:
        raise HTTPException(422, "The value is not a number.") from exc


def _fact_or_404(db: Session, fact_id: uuid.UUID) -> Fact:
    fact = db.get(Fact, fact_id)
    if fact is None:
        raise HTTPException(404, "Fact not found.")
    return fact


@router.post("/facts/{fact_id}/confirm")
def confirm_fact_route(fact_id: uuid.UUID, db: Session = Depends(get_db),
                       user: User = Depends(require(Permission.CONFIRM_SPREAD))) -> dict:
    """A person accepts a figure held for review exactly as it was read."""
    fact = _fact_or_404(db, fact_id)
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
    _borrower_or_404(db, borrower_id)
    line = template.LINE_BY_KEY.get(body.key)
    if line is None or line.computed:
        raise HTTPException(422, "Only input lines of the spreading template can be entered; totals are calculated.")
    if not body.reason.strip():
        raise HTTPException(422, "Entering a figure by hand needs a reason.")
    if line.flow and body.months not in (3, 6, 9, 12):
        raise HTTPException(422, "A flow line needs the number of months in the period: 3, 6, 9 or 12.")
    try:
        fact, recalculation = corrections.enter(
            db, borrower_id=borrower_id, key=body.key, period_end=body.period_end,
            months=body.months if line.flow else 0, value=_decimal(body.value), user_id=user.id, reason=body.reason)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    return {**fact_out(db, fact), "recalculation": recalculation}
