from app.core import ledger

from .conftest import sign_in


def _event(db, n):
    return ledger.record(db, actor_type="system", actor_id="t", action="test.event", entity_type="t", entity_id=str(n))


def test_after_seq_returns_only_newer_events_oldest_first(db, client, world):
    first = _event(db, 1)
    second = _event(db, 2)
    third = _event(db, 3)
    db.commit()
    sign_in(client, "priya.raman")
    rows = client.get(f"/api/v1/ledger?entity_type=t&after_seq={first.seq}").json()
    assert [r["seq"] for r in rows] == [second.seq, third.seq]


def test_after_seq_at_the_head_is_empty_not_an_error(db, client, world):
    last = _event(db, 1)
    db.commit()
    sign_in(client, "priya.raman")
    assert client.get(f"/api/v1/ledger?entity_type=t&after_seq={last.seq}").json() == []


def test_without_after_seq_the_list_is_still_newest_first(db, client, world):
    a, b = _event(db, 1), _event(db, 2)
    db.commit()
    sign_in(client, "priya.raman")
    seqs = [r["seq"] for r in client.get("/api/v1/ledger?entity_type=t").json()]
    assert seqs == [b.seq, a.seq]


def test_after_seq_rejects_a_negative_cursor(client, world):
    sign_in(client, "priya.raman")
    assert client.get("/api/v1/ledger?after_seq=-1").status_code == 422
