"""Append-only, hash-chained ledger of every action taken by a person, an agent or the system.

Each event stores the hash of the previous event, so any edit or removal breaks the chain.
A database trigger (see `install_guards`) also refuses UPDATE and DELETE on the table.
"""
import hashlib
import json
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
    db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _LOCK_KEY})
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
