"""Endpoints for the Squad experience. Read models and thin writes; every rule lives in the domain."""
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import current_user, require
from app.api.routes_work import _item
from app.core.db import get_db
from app.core.roles import Permission, SecondPersonRequired
from app.domain import routing
from app.domain.credit import Borrower
from app.domain.monitoring import WorkItem
from app.domain.org import User
from app.squad import drafts
from app.squad.briefing import build_briefing
from app.squad.cases import build_approvals, build_case
from app.squad.client_file import measure_series
from app.squad.questions import answer_question
from app.squad.threads import build_thread
from app.squad.track_record import track_record
from app.squad.trail import case_trail
from app.squad.words import DOCUMENT_TYPE_WORDS, NOTE_WORDS, document_type_words

router = APIRouter(tags=["squad"])


@router.get("/threads/{borrower_id}")
def get_thread(borrower_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(require(Permission.VIEW))) -> dict:
    try:
        return build_thread(db, borrower_id, user)
    except LookupError as exc:
        raise HTTPException(404, "Client not found.") from exc


@router.get("/me/briefing")
def my_briefing(db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    return build_briefing(db, user)


class AnswerIn(BaseModel):
    option_id: str
    remember: bool = False
    note: str = ""


@router.post("/work-items/{item_id}/answer")
def answer(item_id: uuid.UUID, body: AnswerIn, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    item = db.get(WorkItem, item_id)
    if item is None:
        raise HTTPException(404, "Question not found.")
    try:
        answer_question(db, item, user, body.option_id, remember=body.remember, note=body.note)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except SecondPersonRequired as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    return {**_item(item), "lesson_id": item.evidence.get("lesson_id")}


class DraftIn(BaseModel):
    to: str = Field(max_length=320)
    subject: str = Field(max_length=200)
    body: str = Field(max_length=8000)
    kind: Literal["message", "reminder", "demo_reminder"] = "message"
    work_item_id: uuid.UUID | None = None


class DraftEditIn(BaseModel):
    subject: str | None = Field(default=None, max_length=200)
    body: str | None = Field(default=None, max_length=8000)


def _draft_call(db: Session, fn, *args, **kwargs) -> dict:
    try:
        out = fn(db, *args, **kwargs)
    except LookupError as exc:
        raise HTTPException(404, "Draft not found.") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    return out


@router.post("/borrowers/{borrower_id}/drafts", status_code=201)
def new_draft(borrower_id: uuid.UUID, body: DraftIn, db: Session = Depends(get_db),
              user: User = Depends(require(Permission.EDIT_COMMENTARY))) -> dict:
    if db.get(Borrower, borrower_id) is None:
        raise HTTPException(404, "Client not found.")
    return _draft_call(db, drafts.create_draft, borrower_id=borrower_id, to=body.to, subject=body.subject,
                       body=body.body, kind=body.kind, work_item_id=body.work_item_id, actor=("user", str(user.id)))


@router.post("/drafts/{draft_id}/edit")
def edit_draft_route(draft_id: uuid.UUID, body: DraftEditIn, db: Session = Depends(get_db),
                     user: User = Depends(require(Permission.EDIT_COMMENTARY))) -> dict:
    return _draft_call(db, drafts.edit_draft, draft_id, user, subject=body.subject, body=body.body)


@router.post("/drafts/{draft_id}/send")
def send_draft_route(draft_id: uuid.UUID, db: Session = Depends(get_db),
                     user: User = Depends(require(Permission.EDIT_COMMENTARY))) -> dict:
    return {**_draft_call(db, drafts.send_draft, draft_id, user), "delivered": False}


@router.get("/cases/{work_item_id}/trail")
def trail(work_item_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(require(Permission.VIEW))) -> dict:
    item = db.get(WorkItem, work_item_id)
    if item is None:
        raise HTTPException(404, "Case not found.")
    return case_trail(db, item)


@router.get("/borrowers/{borrower_id}/track-record")
def borrower_track_record(borrower_id: uuid.UUID, db: Session = Depends(get_db),
                          _: User = Depends(require(Permission.VIEW))) -> list[dict]:
    if db.get(Borrower, borrower_id) is None:
        raise HTTPException(404, "Client not found.")
    return track_record(db, borrower_id)


def _open_item(db: Session, item_id: uuid.UUID) -> WorkItem:
    item = db.get(WorkItem, item_id)
    if item is None:
        raise HTTPException(404, "Case not found.")
    return item


def _engine(db: Session, fn, *args, **kwargs) -> None:
    try:
        fn(db, *args, **kwargs)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except SecondPersonRequired as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    db.commit()


@router.get("/cases/{work_item_id}")
def get_case(work_item_id: uuid.UUID, db: Session = Depends(get_db),
             user: User = Depends(require(Permission.VIEW))) -> dict:
    return build_case(db, _open_item(db, work_item_id), user)


@router.get("/me/approvals")
def my_approvals(db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[dict]:
    return build_approvals(db, user)


class RouteIn(BaseModel):
    to: uuid.UUID
    view: str = Field(max_length=4000)


class ReturnIn(BaseModel):
    reason: str = Field(max_length=4000)


class AttachIn(BaseModel):
    document_id: uuid.UUID
    note: str = Field(default="", max_length=500)


@router.post("/work-items/{item_id}/route")
def route_case(item_id: uuid.UUID, body: RouteIn, db: Session = Depends(get_db),
               user: User = Depends(require(Permission.MANAGE_ACTIONS))) -> dict:
    item = _open_item(db, item_id)
    _engine(db, routing.route_work_item, item, user=user, to_user_id=body.to, view=body.view)
    return build_case(db, item, user)


@router.post("/work-items/{item_id}/return")
def return_case(item_id: uuid.UUID, body: ReturnIn, db: Session = Depends(get_db),
                user: User = Depends(current_user)) -> dict:
    item = _open_item(db, item_id)
    _engine(db, routing.return_work_item, item, user=user, reason=body.reason)
    return build_case(db, item, user)


@router.post("/work-items/{item_id}/attach")
def attach_to_case(item_id: uuid.UUID, body: AttachIn, db: Session = Depends(get_db),
                   user: User = Depends(current_user)) -> dict:
    item = _open_item(db, item_id)
    _engine(db, routing.attach_evidence, item, user=user, document_id=body.document_id, note=body.note)
    return build_case(db, item, user)


@router.get("/words/document-types")
def document_type_words_table(_: User = Depends(current_user)) -> dict:
    """The plain words for every document type, and the words for an unclassified document; the browser has no list."""
    return {"types": DOCUMENT_TYPE_WORDS, "unclassified": document_type_words(None), "notes": NOTE_WORDS}


@router.get("/borrowers/{borrower_id}/measure")
def borrower_measure(borrower_id: uuid.UUID, db: Session = Depends(get_db),
                     _: User = Depends(require(Permission.VIEW))) -> dict:
    borrower = db.get(Borrower, borrower_id)
    if borrower is None:
        raise HTTPException(404, "Client not found.")
    return measure_series(db, borrower)
