"""The application's own database role must not be able to rewrite the ledger, and a chain
rewritten by an owner must be detectable from a head kept outside the database."""
import pytest
from app import cli
from app.core import ledger
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

RUNTIME_TEST_ROLE = "squad_runtime_test"


def _add(db, n):
    return ledger.record(db, actor_type="system", actor_id="test", action=f"test.event_{n}",
                         entity_type="thing", entity_id=str(n), payload={"n": n})


@pytest.fixture()
def runtime_role(db):
    """A role that owns nothing and holds exactly the grants migration 0003 gives `squad_runtime`.

    Creating a role needs CREATEROLE. Where the test database user lacks it, a superuser creates
    the role once:  CREATE ROLE squad_runtime_test NOLOGIN; GRANT squad_runtime_test TO <test user>;
    """
    member = db.execute(text("SELECT pg_has_role(current_user, oid, 'MEMBER') FROM pg_roles WHERE rolname = :r"),
                        {"r": RUNTIME_TEST_ROLE}).scalar()
    if member is None:
        try:
            with db.begin_nested():
                db.execute(text(f"CREATE ROLE {RUNTIME_TEST_ROLE} NOLOGIN"))
                db.execute(text(f"GRANT {RUNTIME_TEST_ROLE} TO current_user"))
        except DBAPIError:
            pytest.skip(f"needs the role {RUNTIME_TEST_ROLE}; this fixture names the two statements a superuser runs")
    elif not member:
        pytest.skip(f"the test database user is not a member of {RUNTIME_TEST_ROLE}")
    db.execute(text(ledger.runtime_role_sql(RUNTIME_TEST_ROLE)))
    return RUNTIME_TEST_ROLE


REWRITES = [
    ("ALTER TABLE ledger_events DISABLE TRIGGER USER", "must be owner"),
    ("ALTER TABLE ledger_events DISABLE TRIGGER ledger_events_no_update", "must be owner"),
    ("DROP TRIGGER ledger_events_no_update ON ledger_events", "must be owner"),
    ("ALTER TABLE ledger_events OWNER TO squad_runtime_test", "must be owner"),
    ("DROP TABLE ledger_events", "must be owner"),
    ("CREATE OR REPLACE FUNCTION ledger_events_append_only() RETURNS trigger AS $$ BEGIN RETURN NEW; END; $$ "
     "LANGUAGE plpgsql", "must be owner|permission denied"),
    ("UPDATE ledger_events SET actor_id = 'someone-else' WHERE seq = 1", "permission denied"),
    ("DELETE FROM ledger_events WHERE seq = 1", "permission denied"),
    ("TRUNCATE ledger_events", "permission denied"),
]


def test_the_runtime_role_appends_and_reads_but_cannot_disable_the_guard_or_change_a_row(db, runtime_role):
    _add(db, 1)
    _add(db, 2)
    assert ledger.guard_status(db)["append_only_for_this_role"] is False  # the owner could switch it off
    db.execute(text(f"SET LOCAL ROLE {runtime_role}"))
    try:
        assert db.execute(text("SELECT current_user")).scalar() == runtime_role
        _add(db, 3)  # the application's work: append and read
        assert ledger.verify_chain(db) == (True, 3, None)
        for statement, refusal in REWRITES:
            with pytest.raises(DBAPIError, match=refusal):
                with db.begin_nested():
                    db.execute(text(statement))
        assert ledger.guard_status(db)["append_only_for_this_role"] is True
    finally:
        db.execute(text("RESET ROLE"))
    assert ledger.verify_chain(db) == (True, 3, None)


def test_the_runtime_role_can_still_do_the_applications_other_work(db, runtime_role):
    db.execute(text(f"SET LOCAL ROLE {runtime_role}"))
    try:
        from app.domain.credit import Borrower
        db.add(Borrower(code="R-1", name="Runtime Borrower"))
        db.flush()
        db.execute(text("UPDATE borrowers SET name = 'Renamed' WHERE code = 'R-1'"))
        assert db.execute(text("SELECT name FROM borrowers WHERE code = 'R-1'")).scalar() == "Renamed"
        with pytest.raises(DBAPIError, match="must be owner"):
            with db.begin_nested():
                db.execute(text("ALTER TABLE borrowers ADD COLUMN note text"))
    finally:
        db.execute(text("RESET ROLE"))


def test_the_grants_leave_a_non_owner_with_append_and_read_on_the_ledger_and_nothing_more(db):
    """The same grants read back from the database's own privilege tables. This runs where no
    role can be created: the grants are given, inside the test's transaction, to a role every
    server already has and that holds no rights on any table."""
    stand_in = "pg_signal_backend"
    db.execute(text(ledger.runtime_role_sql(stand_in)))

    def may(table, privilege):
        return db.execute(text("SELECT has_table_privilege(:r, :t, :p)"),
                          {"r": stand_in, "t": table, "p": privilege}).scalar()

    assert {p: may("ledger_events", p) for p in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "TRIGGER")} == {
        "SELECT": True, "INSERT": True, "UPDATE": False, "DELETE": False, "TRUNCATE": False, "TRIGGER": False}
    assert all(may("work_items", p) for p in ("SELECT", "INSERT", "UPDATE", "DELETE")) and not may("work_items", "TRUNCATE")
    # only a table's owner may alter it or disable its triggers, and the role is not the owner
    owns = db.execute(text("SELECT pg_has_role(:r, relowner, 'USAGE') FROM pg_class "
                           "WHERE oid = to_regclass('ledger_events')"), {"r": stand_in}).scalar()
    assert owns is False
    assert db.execute(text("SELECT has_schema_privilege(:r, 'public', 'CREATE')"), {"r": stand_in}).scalar() is False


def test_runtime_role_grants_refuse_a_name_that_is_not_a_plain_role():
    with pytest.raises(ValueError):
        ledger.runtime_role_sql("squad; DROP TABLE ledger_events")


def _rewrite_and_rehash(db, seq):
    """What an owner-level user can do: switch the guard off, change one event, recompute every hash."""
    db.execute(text("ALTER TABLE ledger_events DISABLE TRIGGER USER"))
    prev = ledger.GENESIS
    for ev in db.execute(select(ledger.LedgerEvent).order_by(ledger.LedgerEvent.seq)).scalars():
        if ev.seq == seq:
            ev.actor_type, ev.actor_id = "user", "00000000-0000-4000-8000-00000000beef"
        ev.prev_hash = prev
        ev.hash = ledger._digest(prev, ledger._body(ev))
        prev = ev.hash
    db.flush()
    db.execute(text("ALTER TABLE ledger_events ENABLE TRIGGER USER"))
    db.expire_all()


def test_a_rewritten_and_rehashed_chain_verifies_but_has_lost_the_stored_head(db, capsys):
    for n in range(1, 6):
        _add(db, n)
    stored = ledger.head(db)
    assert stored[0] == 5 and ledger.check_head(db, stored) is None
    assert cli.verify_ledger(db, f"{stored[0]}:{stored[1]}") == 0
    assert f"head: 5:{stored[1]}" in capsys.readouterr().out

    _rewrite_and_rehash(db, 2)
    assert ledger.verify_chain(db) == (True, 5, None)  # the chain agrees with itself: this alone proves nothing
    assert "rewritten" in ledger.check_head(db, stored)
    assert cli.verify_ledger(db, f"{stored[0]}:{stored[1]}") == 1
    out = capsys.readouterr().out
    assert "chain intact" in out and "STORED HEAD NOT FOUND" in out
    # without the outside copy the command passes, and says what it could not check
    assert cli.verify_ledger(db) == 0 and "no stored head was given" in capsys.readouterr().out


def test_a_stored_head_also_exposes_removed_events_and_a_malformed_head_is_refused(db):
    for n in range(1, 4):
        _add(db, n)
    stored = ledger.head(db)
    db.execute(text("ALTER TABLE ledger_events DISABLE TRIGGER USER"))
    db.execute(text("DELETE FROM ledger_events WHERE seq = 3"))
    db.execute(text("ALTER TABLE ledger_events ENABLE TRIGGER USER"))
    db.expire_all()
    assert ledger.verify_chain(db) == (True, 2, None) and "removed" in ledger.check_head(db, stored)
    assert ledger.parse_head(f" 3:{stored[1]} ") == stored
    for bad in ("", "3", "3:abc", f"x:{stored[1]}", f"3:{stored[1].upper()}"):
        with pytest.raises(ValueError):
            ledger.parse_head(bad)
