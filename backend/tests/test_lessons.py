"""Teach once: a person's own words become precedent the agents read."""
import pytest
from app.core.ledger import LedgerEvent
from app.domain.agents import Lesson
from app.domain.credit import Borrower
from app.domain.lessons import record_lesson
from app.domain.org import User
from app.seed_users import seed_users
from sqlalchemy import select

URL = "/api/v1/lessons"


def make_borrower(db, code="LSN") -> Borrower:
    b = Borrower(code=code, name="Quillfeather Labs, Inc.")
    db.add(b)
    db.flush()
    return b


def an_author(db) -> User:
    seed_users(db, password="pw")
    return db.execute(select(User).where(User.email == "priya.raman@bankofstoic.example")).scalar_one()


def agent_query(db, topics, tag=None):
    # exactly the query covenant_tools._search_lessons runs (it needs a whole case in scope to be called)
    query = select(Lesson).where(Lesson.topic.in_(topics))
    if tag:
        query = query.where(Lesson.tag == tag)
    return list(db.execute(query).scalars())


def test_recorded_lesson_is_what_the_agent_query_returns(db):
    b, author = make_borrower(db), an_author(db)
    lesson = record_lesson(db, borrower_id=b.id, topic="leverage", tag="amendment_addback", written_by=author.id,
                           text="  Check for a signed amendment first.\n  Keep inner spacing.  ")
    assert lesson.text == "Check for a signed amendment first.\n  Keep inner spacing."
    assert agent_query(db, {"leverage", "other"}) == [lesson]
    assert agent_query(db, {"leverage"}, tag="amendment_addback") == [lesson]
    assert agent_query(db, {"leverage"}, tag="nope") == []
    assert lesson.borrower_id == b.id and lesson.written_by == author.id


@pytest.mark.parametrize("text", ["", "   ", "\n\t "])
def test_empty_text_is_refused(db, text):
    b, author = make_borrower(db), an_author(db)
    with pytest.raises(ValueError, match="a lesson is a person's own words"):
        record_lesson(db, borrower_id=b.id, topic="leverage", text=text, written_by=author.id)
    assert db.execute(select(Lesson)).first() is None


def test_author_must_be_a_user(db):
    import uuid
    b = make_borrower(db)
    with pytest.raises(ValueError):
        record_lesson(db, borrower_id=b.id, topic="leverage", text="x", written_by=uuid.uuid4())


def test_one_ledger_event(db):
    b, author = make_borrower(db), an_author(db)
    lesson = record_lesson(db, borrower_id=b.id, topic="leverage", tag="t", text="Because.", written_by=author.id)
    events = db.execute(select(LedgerEvent).where(LedgerEvent.action == "lesson.recorded")).scalars().all()
    assert len(events) == 1
    ev = events[0]
    assert ev.actor_type == "user" and ev.actor_id == str(author.id) and ev.entity_id == str(lesson.id)
    assert ev.payload["borrower_id"] == str(b.id) and ev.payload["topic"] == "leverage"
    assert ev.payload["tag"] == "t" and ev.payload["work_item_id"] is None


def _sign_in(client, who):
    r = client.post("/api/v1/auth/login", json={"email": f"{who}@bankofstoic.example", "password": "pw"})
    assert r.status_code == 200, r.text


def test_lesson_api(client, db):
    seed_users(db, password="pw")
    b = make_borrower(db)
    body = {"borrower_id": str(b.id), "topic": "leverage", "text": "Check the amendment.", "tag": "x"}
    assert client.post(URL, json=body).status_code == 401
    _sign_in(client, "ruth.calloway")  # view and QA only
    assert client.post(URL, json=body).status_code == 403
    _sign_in(client, "priya.raman")
    created = client.post(URL, json=body)
    assert created.status_code == 201, created.text
    lesson = db.get(Lesson, created.json()["id"])
    assert lesson.text == "Check the amendment."
    me = db.execute(select(User).where(User.email == "priya.raman@bankofstoic.example")).scalar_one()
    assert lesson.written_by == me.id
    # the author is never taken from the body
    other = client.post(URL, json={**body, "written_by": "00000000-0000-4000-8000-000000000000"})
    assert other.status_code == 201
    assert db.get(Lesson, other.json()["id"]).written_by == me.id
    assert client.post(URL, json={**body, "text": "  "}).status_code == 422
    assert client.post(URL, json={**body, "borrower_id": "00000000-0000-4000-8000-000000000000"}).status_code == 404


def test_lesson_text_is_capped_and_the_work_item_must_belong_to_the_borrower(client, db):
    from app.domain.monitoring import WorkItem
    seed_users(db, password="pw")
    b, other = make_borrower(db), make_borrower(db, code="LSO")
    item = WorkItem(borrower_id=other.id, item_type="spread.value_unverified", severity="medium", title="t",
                    question="Is this right?", allowed_decisions=["retry"], stage="spreading")
    db.add(item)
    db.flush()
    db.commit()
    _sign_in(client, "priya.raman")
    body = {"borrower_id": str(b.id), "topic": "leverage", "text": "x" * 2000}
    assert client.post(URL, json=body).status_code == 201
    assert client.post(URL, json={**body, "text": "x" * 2001}).status_code == 422
    assert client.post(URL, json={**body, "text": "ok", "work_item_id": str(item.id)}).status_code == 422
    ok = client.post(URL, json={**body, "borrower_id": str(other.id), "text": "ok", "work_item_id": str(item.id)})
    assert ok.status_code == 201
    missing = client.post(URL, json={**body, "text": "ok", "work_item_id": "00000000-0000-4000-8000-000000000000"})
    assert missing.status_code == 404
