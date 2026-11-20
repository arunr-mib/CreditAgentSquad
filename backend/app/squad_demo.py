"""Squad's own demonstration data for the end-to-end journeys: one question and one draft reminder.
Run after the book is seeded: `uv run python -m app.squad_demo`. Idempotent. A separate file so the
seeded book (seed_book.py, changed by other phases) stays untouched."""
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_engine
from app.domain.credit import Borrower
from app.domain.monitoring import WorkItem
from app.squad import drafts
from app.squad.questions import raise_question

DEMO_KEY = "squad_demo:line_mapping"
OPTIONS = [
    {"id": "map_to_arr", "label": "Map it to ARR", "evidence": "The statement labels the line annual recurring revenue."},
    {"id": "map_to_mrr", "label": "Map it to MRR", "evidence": "The same page also shows a monthly column."},
]


def seed_squad_demo(db: Session) -> dict:
    names = db.execute(select(Borrower).order_by(Borrower.name)).scalars().all()
    if len(names) < 2:
        raise RuntimeError("seed the book first: Squad's demonstration needs two clients")
    # On the innovation book the line-mapping question belongs to Stripple (its October package
    # carries the new line) and the reminder to Lumora (its October package is late); on any other
    # book the first two clients by name stand in.
    by_code = {b.code: b for b in names}
    asked = by_code.get("stripple-tech", names[0])
    reminded = by_code.get("lumora-health") or next(b for b in names if b.id != asked.id)
    existing = db.execute(select(WorkItem).where(WorkItem.borrower_id == asked.id, WorkItem.item_type == "question",
                                                 WorkItem.evidence["dedupe_key"].astext == DEMO_KEY)).scalars().first()
    item = existing or raise_question(
        db, borrower_id=asked.id, title="How should I map this line?",
        question="Is 'Recurring revenue' on page 3 ARR or MRR?", options=OPTIONS, topic="line_mapping",
        evidence={"dedupe_key": DEMO_KEY})
    found = [d for d in drafts.drafts_for(db, reminded.id) if d["kind"] == "demo_reminder"]
    draft = found[0] if found else drafts.create_draft(
        db, borrower_id=reminded.id, to="finance@client.example", subject="October MRR report",
        body="Hi,\n\nThanks for the October package. Could you send the October MRR report when you have a moment?\n\nThanks",
        kind="demo_reminder")
    db.commit()
    return {"question_borrower_code": asked.code, "draft_borrower_code": reminded.code,
            "work_item_id": str(item.id), "draft_id": draft["draft_id"]}


if __name__ == "__main__":
    with Session(get_engine()) as session:
        print(json.dumps(seed_squad_demo(session)))
