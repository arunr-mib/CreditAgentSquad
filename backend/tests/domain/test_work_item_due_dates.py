"""Every work item is due by a date set from its severity when it is raised, counted in business
days from the demonstration clock; items raised before that rule are given one by a backfill."""
from datetime import UTC, date, datetime

import pytest
from app.cli import backfill_due_dates
from app.core import clock
from app.core.ledger import LedgerEvent
from app.domain import work_items
from app.domain.credit import Borrower
from app.domain.monitoring import WorkItem
from sqlalchemy import select


@pytest.fixture()
def borrower(db):
    b = Borrower(code="DUE-001", name="Due Date Borrower")
    db.add(b)
    db.flush()
    return b


def raise_test_item(db, borrower, severity, key=None):
    return work_items.raise_item(
        db, borrower_id=borrower.id, item_type="test.due_date", severity=severity, title="A test item",
        question="Does this item carry a due date?", allowed_decisions=["yes"], dedupe_key=key)


def test_business_days_skip_weekends():
    wednesday, friday = date(2026, 11, 18), date(2026, 11, 20)
    assert work_items.add_business_days(wednesday, 2) == friday
    assert work_items.add_business_days(wednesday, 5) == date(2026, 11, 25)
    assert work_items.add_business_days(friday, 1) == date(2026, 11, 23)  # over the weekend
    assert work_items.add_business_days(date(2026, 11, 21), 1) == date(2026, 11, 23)  # from a Saturday


def test_policy_covers_every_severity():
    assert set(work_items.DUE_BUSINESS_DAYS) == set(work_items.SEVERITIES)
    assert work_items.DUE_BUSINESS_DAYS == {"critical": 2, "high": 5, "medium": 10, "low": 20}


@pytest.mark.parametrize(("severity", "due"), [
    ("critical", date(2026, 11, 20)), ("high", date(2026, 11, 25)),
    ("medium", date(2026, 12, 2)), ("low", date(2026, 12, 16)),
])
def test_an_item_is_due_by_its_severity_from_the_demonstration_clock(db, borrower, severity, due):
    clock.set_today(db, date(2026, 11, 18))
    item = raise_test_item(db, borrower, severity)
    assert item.due_date == due
    raised = db.execute(select(LedgerEvent).where(LedgerEvent.action == "work_item.raised",
                                                  LedgerEvent.entity_id == str(item.id))).scalar_one()
    assert raised.payload["due_date"] == due.isoformat()


def test_a_returned_duplicate_keeps_its_own_due_date(db, borrower):
    clock.set_today(db, date(2026, 11, 18))
    first = raise_test_item(db, borrower, "high", key="same")
    clock.set_today(db, date(2026, 12, 1))
    assert raise_test_item(db, borrower, "high", key="same").due_date == first.due_date


def sign_in(client, db, who):
    from app.seed_users import seed_users

    seed_users(db, password="pw")
    r = client.post("/api/v1/auth/login", json={"email": f"{who}@bankofstoic.example", "password": "pw"})
    assert r.status_code == 200, r.text


def test_a_person_can_still_change_the_due_date(client, db, borrower):
    clock.set_today(db, date(2026, 11, 18))
    item = raise_test_item(db, borrower, "low")
    sign_in(client, db, "priya.raman")
    from app.domain.org import User
    borrower.analyst_id = db.query(User).filter(User.email == "priya.raman@bankofstoic.example").one().id  # the test's analyst owns the test's client: an analyst acts only on her own clients (owner answer 9)
    db.flush()
    done = client.post(f"/api/v1/work-items/{item.id}/assign", json={"assigned_to": None, "due_date": "2026-11-30"})
    assert done.status_code == 200, done.text
    assert done.json()["due_date"] == "2026-11-30"


def test_the_policy_register_shows_the_rule_from_the_constant(client, db):
    sign_in(client, db, "priya.raman")
    body = client.get("/api/v1/governance/policy").json()
    rules = {r["id"]: r for s in body["sections"] for r in s["rules"]}
    sla = rules["work_item_due"]
    assert sla["source"] == "domain/work_items.py"
    for severity, days in work_items.DUE_BUSINESS_DAYS.items():
        assert f"{severity.capitalize()} {days}" in sla["setting"] or f"{severity} {days}" in sla["setting"]


def test_backfill_sets_missing_due_dates_once_and_records_each(db, borrower, capsys):
    made = datetime(2026, 11, 13, 15, 0, tzinfo=UTC)  # a Friday
    def legacy(severity, status="open"):
        item = WorkItem(borrower_id=borrower.id, item_type="test.due_date", severity=severity, title="Old item",
                        question="Raised before due dates?", allowed_decisions=["yes"], status=status)
        db.add(item)
        db.flush()
        item.created_at = made
        db.flush()
        return item

    high, low, decided = legacy("high"), legacy("low"), legacy("medium", status="decided")
    already = legacy("critical")
    already.due_date = date(2027, 1, 4)
    db.flush()

    assert backfill_due_dates(db) == 0
    assert high.due_date == date(2026, 11, 20) and low.due_date == date(2026, 12, 11)
    assert decided.due_date is None and already.due_date == date(2027, 1, 4)
    events = list(db.execute(select(LedgerEvent).where(LedgerEvent.action == "work_item.due_date_set")).scalars())
    assert {e.entity_id for e in events} == {str(high.id), str(low.id)}
    assert all(e.actor_type == "system" for e in events)
    assert {e.payload["due_date"] for e in events} == {"2026-11-20", "2026-12-11"}
    assert "2 open work items" in capsys.readouterr().out

    # running it again changes nothing and records nothing
    assert backfill_due_dates(db) == 0
    again = db.execute(select(LedgerEvent).where(LedgerEvent.action == "work_item.due_date_set")).scalars().all()
    assert len(again) == 2
