"""Review sheets, commentary, review meetings and credit actions."""
import uuid
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user, require
from app.api.serialize import plain, row
from app.core import ledger
from app.core.db import get_db
from app.core.roles import Permission
from app.domain import review_service
from app.domain.credit import Borrower
from app.domain.facts import Fact
from app.domain.monitoring import Cycle
from app.domain.org import User
from app.domain.reviews import Action, ReviewMeeting, ReviewSheet

router = APIRouter(tags=["reviews"])


def _sheet_out(db: Session, sheet: ReviewSheet) -> dict:
    commentary = review_service.current_commentary(db, sheet)
    users = {u.id: u.name for u in db.execute(select(User)).scalars()}
    fact_ids = set(sheet.content.get("fact_labels", {}))
    for c in commentary:
        fact_ids.update(c.fact_ids)
    facts = {}
    for fid in fact_ids:
        fact = db.get(Fact, uuid.UUID(fid))
        if fact is not None:
            facts[fid] = {"value": plain(fact.value), "unit": fact.unit, "kind": fact.kind, "status": fact.status,
                          "key": fact.key, "period_end": fact.period_end.isoformat()}
    borrower = db.get(Borrower, sheet.borrower_id)
    cycle = db.get(Cycle, sheet.cycle_id)
    return {
        **row(sheet), "borrower_name": borrower.name, "period_end": cycle.period_end.isoformat(),
        "approved_by_name": users.get(sheet.approved_by), "facts": facts,
        # sections the agent drafted that a check withheld, so the approver sees what is not there
        "withheld_sections": (sheet.content or {}).get("withheld_sections", []),
        "commentary": [{**row(c), "rendered": review_service.rendered(db, c),
                        "author_name": users.get(uuid.UUID(c.author_id)) if c.author_type == "user" else "Review Agent",
                        "written_by_agent": c.author_type == "agent"} for c in commentary],
    }


@router.get("/review-sheets")
def list_sheets(borrower_id: uuid.UUID | None = None, period_end: date | None = None, db: Session = Depends(get_db),
                _: User = Depends(current_user)) -> list[dict]:
    query = select(ReviewSheet, Cycle, Borrower).join(Cycle, Cycle.id == ReviewSheet.cycle_id).join(
        Borrower, Borrower.id == ReviewSheet.borrower_id).order_by(Cycle.period_end.desc(), Borrower.name)
    if borrower_id:
        query = query.where(ReviewSheet.borrower_id == borrower_id)
    if period_end:
        query = query.where(Cycle.period_end == period_end)
    return [{**row(s, exclude=("content", "changes_since_last")), "borrower_name": b.name,
             "period_end": c.period_end.isoformat()} for s, c, b in db.execute(query).all()]


@router.get("/review-sheets/{sheet_id}")
def get_sheet(sheet_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(current_user)) -> dict:
    sheet = db.get(ReviewSheet, sheet_id)
    if sheet is None:
        raise HTTPException(404, "Review sheet not found.")
    return _sheet_out(db, sheet)


class SectionIn(BaseModel):
    section: str
    body: str


@router.post("/review-sheets/{sheet_id}/commentary")
def write_commentary(sheet_id: uuid.UUID, body: SectionIn, db: Session = Depends(get_db),
                     user: User = Depends(require(Permission.EDIT_COMMENTARY))) -> dict:
    sheet = db.get(ReviewSheet, sheet_id)
    if sheet is None:
        raise HTTPException(404, "Review sheet not found.")
    try:
        _, warnings = review_service.write_section(db, sheet, section=body.section, body=body.body, user=user)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    return {**_sheet_out(db, sheet), "warnings": warnings}


class MeetingIn(BaseModel):
    title: str
    meeting_date: date
    period_end: date


@router.get("/review-meetings")
def list_meetings(db: Session = Depends(get_db), _: User = Depends(current_user)) -> list[dict]:
    meetings = db.execute(select(ReviewMeeting).order_by(ReviewMeeting.meeting_date.desc())).scalars()
    out = []
    for m in meetings:
        sheets = db.execute(select(ReviewSheet, Borrower).join(Borrower, Borrower.id == ReviewSheet.borrower_id)
                            .where(ReviewSheet.meeting_id == m.id).order_by(Borrower.name)).all()
        out.append({**row(m), "sheets": [{"id": str(s.id), "borrower_name": b.name, "status": s.status}
                                          for s, b in sheets]})
    return out


@router.post("/review-meetings", status_code=201)
def create_meeting(body: MeetingIn, db: Session = Depends(get_db),
                   user: User = Depends(require(Permission.MANAGE_ACTIONS))) -> dict:
    """Create a meeting and attach every review sheet for the period that has no meeting yet."""
    meeting = ReviewMeeting(title=body.title, meeting_date=body.meeting_date, period_end=body.period_end,
                            chair_id=user.id)
    db.add(meeting)
    db.flush()
    attached = 0
    for sheet, _cycle in db.execute(select(ReviewSheet, Cycle).join(Cycle, Cycle.id == ReviewSheet.cycle_id).where(
            Cycle.period_end == body.period_end, ReviewSheet.meeting_id.is_(None))).all():
        sheet.meeting_id = meeting.id
        attached += 1
    ledger.record(db, actor_type="user", actor_id=user.id, action="review_meeting.created",
                  entity_type="review_meeting", entity_id=meeting.id,
                  payload={"title": body.title, "period_end": body.period_end, "sheets": attached})
    db.commit()
    return {**row(meeting), "sheets_attached": attached}


class PhaseIn(BaseModel):
    phase: str
    notes: str | None = None


@router.post("/review-meetings/{meeting_id}/phase")
def set_phase(meeting_id: uuid.UUID, body: PhaseIn, db: Session = Depends(get_db),
              user: User = Depends(require(Permission.MANAGE_ACTIONS))) -> dict:
    meeting = db.get(ReviewMeeting, meeting_id)
    if meeting is None:
        raise HTTPException(404, "Meeting not found.")
    order = ["before", "during", "after", "closed"]
    if body.phase not in order or order.index(body.phase) < order.index(meeting.phase):
        raise HTTPException(422, "A meeting moves forward only: before, during, after, closed.")
    previous, meeting.phase = meeting.phase, body.phase
    if body.notes is not None:
        meeting.notes = body.notes
    ledger.record(db, actor_type="user", actor_id=user.id, action="review_meeting.phase_changed",
                  entity_type="review_meeting", entity_id=meeting.id, payload={"from": previous, "to": body.phase})
    db.commit()
    return row(meeting)


class ActionIn(BaseModel):
    borrower_id: uuid.UUID
    title: str
    detail: str = ""
    owner_id: uuid.UUID | None = None
    due_date: date | None = None
    cycle_id: uuid.UUID | None = None
    meeting_id: uuid.UUID | None = None
    work_item_id: uuid.UUID | None = None


@router.get("/actions")
def list_actions(status: str = "open", borrower_id: uuid.UUID | None = None, db: Session = Depends(get_db),
                 _: User = Depends(current_user)) -> list[dict]:
    from app.core import clock

    query = select(Action).order_by(Action.due_date.nulls_last(), Action.created_at)
    if status == "open":
        query = query.where(Action.status.in_(("open", "in_progress")))
    elif status != "all":
        query = query.where(Action.status == status)
    if borrower_id:
        query = query.where(Action.borrower_id == borrower_id)
    today = clock.today(db)
    names = {b.id: b.name for b in db.execute(select(Borrower)).scalars()}
    users = {u.id: u.name for u in db.execute(select(User)).scalars()}
    return [{**row(a), "borrower_name": names.get(a.borrower_id), "owner_name": users.get(a.owner_id),
             "overdue": bool(a.due_date and a.due_date < today and a.status in ("open", "in_progress"))}
            for a in db.execute(query).scalars()]


@router.post("/actions", status_code=201)
def create_action(body: ActionIn, db: Session = Depends(get_db),
                  user: User = Depends(require(Permission.MANAGE_ACTIONS))) -> dict:
    if db.get(Borrower, body.borrower_id) is None:
        raise HTTPException(404, "Borrower not found.")
    if not body.title.strip():
        raise HTTPException(422, "An action needs a title.")
    action = Action(**body.model_dump(), raised_by=user.id)
    db.add(action)
    db.flush()
    ledger.record(db, actor_type="user", actor_id=user.id, action="action.raised", entity_type="action",
                  entity_id=action.id, payload={"title": body.title, "owner_id": body.owner_id, "due_date": body.due_date})
    db.commit()
    return row(action)


class ActionStatusIn(BaseModel):
    status: str
    note: str = ""
    escalate: bool = False


@router.post("/actions/{action_id}/status")
def set_action_status(action_id: uuid.UUID, body: ActionStatusIn, db: Session = Depends(get_db),
                      user: User = Depends(require(Permission.MANAGE_ACTIONS))) -> dict:
    from app.domain import workflow

    action = db.get(Action, action_id)
    if action is None:
        raise HTTPException(404, "Action not found.")
    if body.status not in ("open", "in_progress", "done", "cancelled"):
        raise HTTPException(422, "Unknown status.")
    if body.status in ("done", "cancelled") and not body.note.strip():
        raise HTTPException(422, "Closing an action needs a note saying what was done or why it was dropped.")
    previous, action.status = action.status, body.status
    action.escalated = action.escalated or body.escalate
    if body.status in ("done", "cancelled"):
        action.closed_at = datetime.now(UTC)
        action.closing_note = body.note
    ledger.record(db, actor_type="user", actor_id=user.id, action="action.status_changed", entity_type="action",
                  entity_id=action.id, payload={"from": previous, "to": body.status, "note": body.note,
                                                "escalated": action.escalated})
    db.flush()
    if action.cycle_id is not None:
        cycle = db.get(Cycle, action.cycle_id)
        if cycle is not None:
            workflow.advance(db, cycle)
    db.commit()
    return row(action)
