"""Squad asks: a work item whose allowed decisions are the options the agent proposes (spec 8).
Answering goes through the engine's own `decide_work_item`, so permissions, the ledger record and
the actor's name are the engine's. "Remember" additionally writes one lesson in the person's name,
from the person's own written note: only a person's reasoning becomes precedent."""
import re
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.domain import workflow
from app.domain.lessons import record_lesson
from app.domain.monitoring import WorkItem
from app.domain.org import User
from app.domain.work_items import raise_item

QUESTION = "question"
LESSON_MAX = 2000  # the same cap the lessons route puts on a lesson's text
TOPIC_MAX = 48
_SLUG = re.compile(r"^[a-z0-9_]+$")


def _check_options(options: list[dict[str, Any]]) -> list[dict[str, str]]:
    if not 2 <= len(options) <= 6:
        raise ValueError("a question offers two to six options")
    seen: set[str] = set()
    clean = []
    for option in options:
        oid, label = str(option.get("id", "")), str(option.get("label", "")).strip()
        if not _SLUG.match(oid) or not label:
            raise ValueError("each option needs a lowercase id and a label")
        if oid in seen:
            raise ValueError(f"option {oid!r} is offered twice")
        seen.add(oid)
        clean.append({"id": oid, "label": label, "evidence": str(option.get("evidence", ""))})
    return clean


def raise_question(db: Session, *, borrower_id: uuid.UUID, title: str, question: str, options: list[dict[str, Any]],
                   evidence: dict[str, Any] | None = None, topic: str = "question", cycle_id: uuid.UUID | None = None,
                   severity: str = "medium", actor: tuple[str, str] = ("agent", "squad")) -> WorkItem:
    clean = _check_options(options)
    if not 1 <= len(topic) <= TOPIC_MAX:
        raise ValueError(f"a topic is 1 to {TOPIC_MAX} characters")
    return raise_item(
        db, borrower_id=borrower_id, item_type=QUESTION, title=title, question=question,
        allowed_decisions=[o["id"] for o in clean], severity=severity, cycle_id=cycle_id, blocks_stage=False,
        evidence={**(evidence or {}), "options": clean, "topic": topic}, actor=actor)


def answer_question(db: Session, item: WorkItem, user: User, option_id: str, *, remember: bool = False,
                    note: str = "") -> WorkItem:
    if item.item_type != QUESTION:
        raise ValueError("this item is not a question from Squad")
    text = ""
    if remember:  # checked before the decision, so a refused request records nothing at all
        label = next((o["label"] for o in item.evidence.get("options", []) if o["id"] == option_id), option_id)
        words = note.strip()
        if not words:
            raise ValueError("to remember an answer, say why in your own words")
        text = f"{user.name} chose “{label}” when asked: {item.question} Reason: {words}"
        if len(text) > LESSON_MAX:
            raise ValueError(f"a lesson is at most {LESSON_MAX} characters")
    workflow.decide_work_item(db, item, user_id=user.id, user_role=user.role, decision=option_id, reason=note)
    if remember:
        lesson = record_lesson(db, borrower_id=item.borrower_id, topic=item.evidence.get("topic", QUESTION),
                               text=text, written_by=user.id, work_item_id=item.id, tag=option_id)
        item.evidence = {**item.evidence, "lesson_id": str(lesson.id)}
    return item
