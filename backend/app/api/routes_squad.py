"""Endpoints for the Squad experience. Read models and thin writes; every rule lives in the domain."""
import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, not_, or_, select
from sqlalchemy.orm import Session

from app.api.deps import current_user, require
from app.api.routes_evals import latest_eval
from app.api.routes_work import _item, get_agent_run, list_agent_runs, list_agents
from app.api.serialize import row
from app.core.db import get_db
from app.core.ledger import LedgerEvent
from app.core.roles import Permission, SecondPersonRequired
from app.domain import routing
from app.domain.credit import Borrower
from app.domain.monitoring import WorkItem
from app.domain.org import User
from app.publishing.content import SIGNAL_LABELS
from app.squad import drafts
from app.squad.briefing import build_briefing
from app.squad.cases import build_approvals, build_case
from app.squad.client_file import measure_series
from app.squad.oversight import OVERSIGHT_ROLES, evaluation_rows, run_words
from app.squad.portfolio import build_portfolio, lessons_for
from app.squad.questions import answer_question
from app.squad.threads import build_thread
from app.squad.track_record import track_record
from app.squad.trail import case_trail
from app.squad.words import (
    DOCUMENT_TYPE_WORDS,
    NOTE_WORDS,
    action_words,
    actor_words,
    agent_words,
    describe_event,
    document_type_words,
    label_tables,
    ledger_family_words,
)

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


@router.get("/me/portfolio")
def my_portfolio(db: Session = Depends(get_db), user: User = Depends(require(Permission.VIEW))) -> dict:
    return build_portfolio(db, user)


@router.get("/borrowers/{borrower_id}/lessons")
def borrower_lessons(borrower_id: uuid.UUID, db: Session = Depends(get_db),
                     _: User = Depends(require(Permission.VIEW))) -> list[dict]:
    if db.get(Borrower, borrower_id) is None:
        raise HTTPException(404, "Client not found.")
    return lessons_for(db, borrower_id)


class AnswerIn(BaseModel):
    option_id: str
    remember: bool = False
    note: str = Field(default="", max_length=4000)


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
    except (SecondPersonRequired, routing.RouteBlocked) as exc:
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


class NeedIn(BaseModel):
    doc_type: str
    period_end: date


class ReturnIn(BaseModel):
    reason: str = Field(max_length=4000)
    needs: list[NeedIn] = Field(default_factory=list, max_length=5)  # the engine says so in words as well


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
    _engine(db, routing.return_work_item, item, user=user, reason=body.reason,
            needs=[n.model_dump() for n in body.needs])
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
    return {"types": DOCUMENT_TYPE_WORDS, "unclassified": document_type_words(None), "notes": NOTE_WORDS,
            "needable": list(routing.NEEDABLE_TYPES)}


@router.get("/words/labels")
def label_words_table() -> dict:
    """Every other table of words a screen shows (severities, stages, roles, covenant outcomes, funding kinds, ...). Open
    before sign-in: the sign-in list names each person's role, and the words are not secret."""
    return label_tables()


@router.get("/words/signals")
def signal_words_table(_: User = Depends(current_user)) -> dict:
    """The plain words for every signal rule; the browser has no list."""
    return {"rules": SIGNAL_LABELS}


@router.get("/borrowers/{borrower_id}/measure")
def borrower_measure(borrower_id: uuid.UUID, db: Session = Depends(get_db),
                     _: User = Depends(require(Permission.VIEW))) -> dict:
    borrower = db.get(Borrower, borrower_id)
    if borrower is None:
        raise HTTPException(404, "Client not found.")
    return measure_series(db, borrower)


_ERROR_WORDS = "The run stopped on an error; administrators can see the detail in Oversight."
_STEP_KIND_WORDS = {"model": "Model", "tool": "Tool", "guardrail": "Guardrail", "note": "Note"}


def _plain_run(run: dict) -> dict:
    """A run for people who may see the client, not the whole record: words for who, what and how it ended. The model's
    output, its raw text, a step's inputs and outputs (they carry figures) and an exception's text stay in Oversight."""
    keep = ("id", "agent_name", "task", "status", "created_at", "finished_at", "borrower_id", "borrower_code", "borrower_name",
            "guardrail_notes", "duration_ms")
    out = run_words({k: v for k, v in run.items() if k in keep})
    out["guardrail_notes"] = [{"words": n["words"]} for n in out["guardrail_notes"]]  # the check and what it did; its detail can quote a figure
    out["error_words"] = _ERROR_WORDS if run.get("error") else None
    return out


@router.get("/borrowers/{borrower_id}/runs")
def borrower_runs(borrower_id: uuid.UUID, limit: int = 50, db: Session = Depends(get_db),
                  user: User = Depends(require(Permission.VIEW))) -> list[dict]:
    """What the agents did for this client, newest first, in words. Anyone who may see the client may read it."""
    if db.get(Borrower, borrower_id) is None:
        raise HTTPException(404, "Client not found.")
    return [_plain_run(r) for r in list_agent_runs(borrower_id=borrower_id, limit=max(1, min(limit, 200)), db=db, _=user)]


@router.get("/runs/{run_id}")
def run_detail(run_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(require(Permission.VIEW))) -> dict:
    """One run with its steps in words (what kind of step, which tool or check, whether it was refused)."""
    run = get_agent_run(run_id=run_id, db=db, _=user)
    out = _plain_run(run)
    out["steps"] = [{"id": s["id"], "n": s["n"], "words": f"{_STEP_KIND_WORDS.get(s['kind'], s['kind'].capitalize())}: "
                     f"{str(s['name']).replace('_', ' ')}{', refused' if s.get('refused') else ''}"} for s in run["steps"]]
    return out


def _oversight_only(user: User) -> None:
    if user.role not in OVERSIGHT_ROLES:
        raise HTTPException(403, "Oversight is for administrators, credit administration and credit review.")


@router.get("/oversight/runs")
def oversight_runs(limit: int = 100, offset: int = Query(default=0, ge=0, le=10**6), db: Session = Depends(get_db),
                   user: User = Depends(current_user)) -> list[dict]:
    """Agent runs, newest first, with the words for agent, task, outcome and each guardrail note. Read only."""
    _oversight_only(user)
    return [run_words(r) for r in list_agent_runs(limit=limit, offset=offset, db=db, _=user)]


@router.get("/oversight/agents")
def oversight_agents(db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[dict]:
    _oversight_only(user)
    return [{**a, "label": agent_words(a["name"])} for a in list_agents(db=db, _=user)]


@router.get("/oversight/ledger-actions")
def oversight_ledger_actions(db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[dict]:
    """The families of event the ledger holds (the part of an action before its first dot), in words."""
    _oversight_only(user)
    families = db.execute(select(func.split_part(LedgerEvent.action, ".", 1)).distinct()).scalars()
    return sorted(({"key": f, "words": ledger_family_words(f)} for f in families), key=lambda x: x["words"])


@router.get("/oversight/ledger")
def oversight_ledger(action: str | None = None, before_seq: int | None = Query(default=None, ge=1, le=2**63 - 1),
                     hide_sign_ins: bool = False, limit: int = 100, db: Session = Depends(get_db),
                     user: User = Depends(current_user)) -> list[dict]:
    """Newest first. `action` is a family; sign-ins can be left out here so a page is still a page. Read only."""
    _oversight_only(user)
    query = select(LedgerEvent).order_by(LedgerEvent.seq.desc()).limit(max(1, min(limit, 500)))
    if action:
        query = query.where(or_(LedgerEvent.action == action, LedgerEvent.action.startswith(action + ".", autoescape=True)))
    if hide_sign_ins and not (action or "").startswith("auth"):  # asked for sign-ins by name: show them
        query = query.where(not_(LedgerEvent.action.startswith("auth.", autoescape=True)))
    if before_seq:
        query = query.where(LedgerEvent.seq < before_seq)
    names = {str(u.id): u.name for u in db.execute(select(User)).scalars()}
    return [{**row(e, exclude=("prev_hash",)), "actor_name": names.get(e.actor_id),
             "actor_label": actor_words(e.actor_type, e.actor_id, names),
             "summary": describe_event(e.action, e.payload), "action_label": action_words(e.action)} for e in db.execute(query).scalars()]


@router.get("/oversight/evaluation")
def oversight_evaluation(db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    """The latest scorecard and where it came from: a run in this database, or the repository's results file."""
    _oversight_only(user)
    envelope = latest_eval(db=db, _=user)  # raises 404 when no evaluation has been run
    results = envelope.pop("results") or {}
    return {**{k: envelope[k] for k in ("source", "id", "suite", "commit", "mode", "standin", "notice", "gate_passed", "created_at")},
            "borrowers": (results.get("meta") or {}).get("borrowers"),
            "rows": evaluation_rows(results.get("metrics") or {})}
