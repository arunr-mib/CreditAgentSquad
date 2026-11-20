"""Endpoints for the Squad experience. Read models and thin writes; every rule lives in the domain."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import current_user, require
from app.api.routes_work import _item
from app.core.db import get_db
from app.core.roles import Permission, SecondPersonRequired
from app.domain.credit import Borrower
from app.domain.monitoring import WorkItem
from app.domain.org import User
from app.squad import drafts
from app.squad.briefing import build_briefing
from app.squad.questions import answer_question
from app.squad.threads import build_thread

router = APIRouter(tags=["squad"])


@router.get("/threads/{borrower_id}")
def get_thread(borrower_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(require(Permission.VIEW))) -> dict:
    try:
        return build_thread(db, borrower_id)
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
    to: str
    subject: str
    body: str
    kind: str = "message"
    work_item_id: uuid.UUID | None = None


class DraftEditIn(BaseModel):
    subject: str | None = None
    body: str | None = None


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
