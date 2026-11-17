import pytest
from app.core import ledger
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError


def _add(db, n):
    return ledger.record(db, actor_type="system", actor_id="test", action=f"test.event_{n}",
                         entity_type="thing", entity_id=str(n), payload={"n": n, "amount": "12.50"})


def test_chain_links_and_verifies(db):
    first, second, third = _add(db, 1), _add(db, 2), _add(db, 3)
    assert first.prev_hash == ledger.GENESIS
    assert second.prev_hash == first.hash and third.prev_hash == second.hash
    assert [first.seq, second.seq, third.seq] == [1, 2, 3]
    assert ledger.verify_chain(db) == (True, 3, None)


def test_update_is_refused_by_the_database(db):
    _add(db, 1)
    with pytest.raises(DBAPIError, match="append-only"):
        with db.begin_nested():
            db.execute(text("UPDATE ledger_events SET action = 'tampered' WHERE seq = 1"))
    assert ledger.verify_chain(db)[0] is True


def test_delete_is_refused_by_the_database(db):
    _add(db, 1)
    with pytest.raises(DBAPIError, match="append-only"):
        with db.begin_nested():
            db.execute(text("DELETE FROM ledger_events"))


def test_tampering_is_detected_when_the_guard_is_bypassed(db):
    _add(db, 1)
    _add(db, 2)
    _add(db, 3)
    # simulate someone with database superuser rights disabling the trigger and editing a row
    db.execute(text("ALTER TABLE ledger_events DISABLE TRIGGER ledger_events_no_update"))
    db.execute(text("UPDATE ledger_events SET payload = '{\"n\": 99}' WHERE seq = 2"))
    db.execute(text("ALTER TABLE ledger_events ENABLE TRIGGER ledger_events_no_update"))
    db.expire_all()
    ok, _, problem = ledger.verify_chain(db)
    assert ok is False and "seq 2" in problem


def test_unknown_actor_type_is_rejected(db):
    with pytest.raises(ValueError):
        ledger.record(db, actor_type="robot", actor_id="x", action="a", entity_type="t", entity_id="1")
