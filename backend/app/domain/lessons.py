"""Lessons: a person's written reasoning, kept as precedent. Only people write them."""
import uuid

from sqlalchemy.orm import Session

from app.core import ledger
from app.domain.agents import Lesson
from app.domain.org import User


def record_lesson(session: Session, *, borrower_id: uuid.UUID, topic: str, text: str, written_by: uuid.UUID,
                  work_item_id: uuid.UUID | None = None, tag: str | None = None) -> Lesson:
    body = (text or "").strip()
    if not body:
        raise ValueError("a lesson is a person's own words")
    if session.get(User, written_by) is None:
        raise ValueError("a lesson is written by a person: no such user")
    lesson = Lesson(borrower_id=borrower_id, work_item_id=work_item_id, topic=topic, tag=tag, text=body,
                    written_by=written_by)
    session.add(lesson)
    session.flush()
    ledger.record(session, actor_type="user", actor_id=written_by, action="lesson.recorded",
                  entity_type="lesson", entity_id=lesson.id,
                  payload={"borrower_id": borrower_id, "topic": topic, "tag": tag, "work_item_id": work_item_id})
    return lesson
