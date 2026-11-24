"""Append-only, hash-chained ledger of every action taken by a person, an agent or the system.

Each event stores the hash of the previous event, so any edit or removal breaks the chain.
A database trigger (see `install_guards`) also refuses UPDATE and DELETE on the table, and the
application runs as a role that cannot switch the trigger off (see `runtime_role_sql`).

What this does not do: a database user with owner or superuser rights can still disable the
trigger, rewrite events and recompute every hash, and the rewritten chain verifies against
itself. That is detectable only by comparing with a copy of the chain's head kept outside the
database (`head`, `check_head`, and `verify-ledger --expect-head`).
"""
import hashlib
import json
import re
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, DateTime, String, Text, select, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.db import Base

GENESIS = "0" * 64
_LOCK_KEY = 4_216_001  # advisory lock that serialises ledger appends


class LedgerEvent(Base):
    __tablename__ = "ledger_events"

    seq: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, default=uuid.uuid4)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actor_type: Mapped[str] = mapped_column(String(16))  # user | agent | system
    actor_id: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(96), index=True)
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_jsonable(v) for v in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


def _digest(prev_hash: str, body: dict[str, Any]) -> str:
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256((prev_hash + canonical).encode("utf-8")).hexdigest()


def _body(ev: LedgerEvent) -> dict[str, Any]:
    return {
        "seq": ev.seq,
        "id": str(ev.id),
        "ts": ev.ts.astimezone(UTC).isoformat(),
        "actor_type": ev.actor_type,
        "actor_id": ev.actor_id,
        "action": ev.action,
        "entity_type": ev.entity_type,
        "entity_id": ev.entity_id,
        "payload": ev.payload,
        "note": ev.note,
    }


def lock(db: Session) -> None:
    """Take the ledger's append lock (held to the end of the transaction). A caller that reads the ledger to
    decide what to append takes it first, so the read cannot be stale by the time it appends."""
    db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _LOCK_KEY})


def record(
    db: Session,
    *,
    actor_type: str,
    actor_id: str | uuid.UUID,
    action: str,
    entity_type: str,
    entity_id: str | uuid.UUID,
    payload: dict[str, Any] | None = None,
    note: str | None = None,
) -> LedgerEvent:
    """Append one event inside the caller's transaction. Appends are serialised by an advisory lock."""
    if actor_type not in ("user", "agent", "system"):
        raise ValueError(f"unknown actor_type {actor_type!r}")
    lock(db)
    last = db.execute(
        select(LedgerEvent.seq, LedgerEvent.hash).order_by(LedgerEvent.seq.desc()).limit(1)
    ).first()
    seq, prev_hash = (last.seq + 1, last.hash) if last else (1, GENESIS)
    ev = LedgerEvent(
        seq=seq,
        id=uuid.uuid4(),
        ts=datetime.now(UTC).replace(microsecond=0),
        actor_type=actor_type,
        actor_id=str(actor_id),
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        payload=_jsonable(payload or {}),
        prev_hash=prev_hash,
        note=note,
    )
    ev.hash = _digest(prev_hash, _body(ev))
    db.add(ev)
    db.flush()
    return ev


def verify_chain(db: Session) -> tuple[bool, int, str | None]:
    """Recompute every hash. Returns (ok, events_checked, first_problem)."""
    prev = GENESIS
    expected_seq = 1
    count = 0
    for ev in db.execute(select(LedgerEvent).order_by(LedgerEvent.seq)).scalars():
        count += 1
        if ev.seq != expected_seq:
            return False, count, f"gap or reorder at seq {ev.seq} (expected {expected_seq})"
        if ev.prev_hash != prev:
            return False, count, f"broken link at seq {ev.seq}"
        if _digest(prev, _body(ev)) != ev.hash:
            return False, count, f"content changed at seq {ev.seq}"
        prev = ev.hash
        expected_seq += 1
    return True, count, None


GUARD_SQL = """
CREATE OR REPLACE FUNCTION ledger_events_append_only() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'ledger_events is append-only (% refused)', TG_OP;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS ledger_events_no_update ON ledger_events;
CREATE TRIGGER ledger_events_no_update BEFORE UPDATE OR DELETE ON ledger_events
  FOR EACH ROW EXECUTE FUNCTION ledger_events_append_only();
DROP TRIGGER IF EXISTS ledger_events_no_truncate ON ledger_events;
CREATE TRIGGER ledger_events_no_truncate BEFORE TRUNCATE ON ledger_events
  FOR EACH STATEMENT EXECUTE FUNCTION ledger_events_append_only();
"""


def install_guards(connection) -> None:
    """Create the triggers that refuse UPDATE, DELETE and TRUNCATE on the ledger."""
    connection.execute(text(GUARD_SQL))


# The triggers stop an honest mistake. They do not stop the table's owner, who can disable them.
# So the application must not connect as the owner: it runs as a login that is a member of this
# role, which may read and append to the ledger and nothing else, and owns no table.
RUNTIME_ROLE = "squad_runtime"


def runtime_role_name() -> str:
    """The runtime role of this deployment: `DB_RUNTIME_ROLE`, `squad_runtime` when unset."""
    from app.core.config import get_settings

    name = get_settings().db_runtime_role.strip() or RUNTIME_ROLE
    if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", name):
        raise ValueError(f"not a plain role name: {name!r}")
    return name


def runtime_role_sql(role: str = RUNTIME_ROLE, schema: str = "public") -> str:
    """Grants for the role the application runs as, in the schema that holds the tables. Run by
    the owner (migration `0003`, or `app.cli grant-runtime-role`); safe to run again."""
    for name in (role, schema):
        if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", name):
            raise ValueError(f"not a plain role or schema name: {name!r}")
    return f"""
GRANT USAGE ON SCHEMA {schema} TO {role};
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {schema} TO {role};
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {schema} TO {role};
ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {role};
ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} GRANT USAGE, SELECT ON SEQUENCES TO {role};
REVOKE ALL ON {schema}.ledger_events FROM {role};
GRANT SELECT, INSERT ON {schema}.ledger_events TO {role};
DO $$
BEGIN
  IF to_regclass('{schema}.alembic_version') IS NOT NULL THEN
    EXECUTE 'REVOKE INSERT, UPDATE, DELETE ON {schema}.alembic_version FROM {role}';
  END IF;
END $$;
"""


def guard_status(db: Session) -> dict[str, Any]:
    """Who this session is connected as, and whether that role could switch the guard off."""
    row = db.execute(text(
        "SELECT current_user AS role, pg_get_userbyid(c.relowner) AS owner, "
        "       pg_has_role(current_user, c.relowner, 'USAGE') AS acts_as_owner, "
        "       (SELECT rolsuper FROM pg_roles WHERE rolname = current_user) AS superuser, "
        "       has_table_privilege(current_user, c.oid, 'UPDATE') AS may_update, "
        "       has_table_privilege(current_user, c.oid, 'DELETE') AS may_delete, "
        "       has_table_privilege(current_user, c.oid, 'TRUNCATE') AS may_truncate "
        "FROM pg_class c WHERE c.oid = to_regclass('ledger_events')")).mappings().first()
    status = dict(row) if row else {"role": None}
    status["append_only_for_this_role"] = bool(row) and not any(
        row[k] for k in ("acts_as_owner", "superuser", "may_update", "may_delete", "may_truncate"))
    return status


def head(db: Session) -> tuple[int, str] | None:
    """The newest event's sequence number and hash: the value to copy somewhere the database's
    owner cannot reach."""
    last = db.execute(select(LedgerEvent.seq, LedgerEvent.hash).order_by(LedgerEvent.seq.desc()).limit(1)).first()
    return (last.seq, last.hash) if last else None


def parse_head(value: str) -> tuple[int, str]:
    """`<seq>:<hash>` as printed by `verify-ledger`."""
    seq, _, digest = value.strip().partition(":")
    if not seq.isdigit() or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("a ledger head is written <sequence number>:<64 hexadecimal characters>")
    return int(seq), digest


def check_head(db: Session, expected: tuple[int, str]) -> str | None:
    """Compare the chain with a head recorded earlier and kept outside the database. A chain that
    was rewritten and rehashed verifies against itself, but its event at that sequence number no
    longer carries the recorded hash. Returns the problem, or None when the head is still there."""
    seq, digest = expected
    found = db.execute(select(LedgerEvent.hash).where(LedgerEvent.seq == seq)).scalar_one_or_none()
    if found is None:
        return f"the ledger has no event {seq}: events recorded before the stored head have been removed"
    if found != digest:
        return (f"event {seq} no longer has the stored hash: history at or before it has been rewritten "
                f"(stored {digest[:12]}..., found {found[:12]}...)")
    return None
