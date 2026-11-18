"""Vercel entry point: the product's API as one serverless function, plus a setup route.

The product itself is unchanged. What differs on this host:
- no disk that persists: document files are read from the synthetic book shipped with the
  deployment (FILE_FALLBACK_DIR), and anything written goes to /tmp and is lost;
- no background worker: a decision is recorded, but the cycle's next stage does not run;
- the tables live in their own schema (DB_SCHEMA) on a shared PostgreSQL server.

Setup is done once, by calling the routes under /api/_setup with the X-Setup-Token header set to
the DEMO_SETUP_TOKEN variable. Without that variable the routes do not exist.
"""
import hmac
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT)]
os.environ.setdefault("FILE_STORE_DIR", "/tmp/files")
os.environ.setdefault("FILE_FALLBACK_DIR", str(ROOT / "synthetic" / "out" / "documents"))
os.environ.setdefault("DB_POOL", "null")
os.environ.setdefault("DB_SCHEMA", "squad")

from app.main import create_app  # noqa: E402
from fastapi import Header, HTTPException  # noqa: E402

app = create_app()
BOOK = ROOT / "synthetic" / "out"


def _allowed(token: str | None) -> None:
    expected = os.environ.get("DEMO_SETUP_TOKEN", "")
    if not expected or not token or not hmac.compare_digest(token, expected):
        raise HTTPException(404, "Not found.")


def _session():
    from app.core.db import get_engine
    from sqlalchemy.orm import Session

    return Session(get_engine())


@app.get("/api/_setup/status")
def setup_status(x_setup_token: str | None = Header(default=None)) -> dict:
    _allowed(x_setup_token)
    import json

    from sqlalchemy import text

    codes = sorted(p.stem for p in (BOOK / "truth").glob("*.json"))
    try:
        with _session() as db:
            loaded = sorted(db.execute(text("select code from borrowers")).scalars())
            users = db.execute(text("select count(*) from users")).scalar()
    except Exception as exc:  # noqa: BLE001 - before migration there are no tables to count
        # the first line of a driver error names the host and the reason, never the password
        reason = (str(getattr(exc, "orig", exc)).splitlines() or [""])[0][:200]
        return {"migrated": False, "detail": type(exc).__name__, "reason": reason, "book": codes}
    manifest = json.loads((BOOK / "manifest.json").read_text()) if (BOOK / "manifest.json").exists() else {}
    return {"migrated": True, "users": users, "loaded": loaded, "to_load": [c for c in codes if c not in loaded],
            "book_borrowers": len(codes), "book_seed": manifest.get("seed")}


@app.post("/api/_setup/migrate")
def setup_migrate(x_setup_token: str | None = Header(default=None)) -> dict:
    _allowed(x_setup_token)
    from alembic import command
    from alembic.config import Config

    config = Config(str(ROOT / "backend" / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "backend" / "migrations"))
    try:
        command.upgrade(config, "head")
    except Exception as exc:  # noqa: BLE001 - say why to the person holding the setup token
        reason = (str(getattr(exc, "orig", exc)).splitlines() or [""])[0][:300]
        raise HTTPException(500, f"{type(exc).__name__}: {reason}") from exc
    from app.seed_users import seed_users

    with _session() as db:
        created = seed_users(db)
        db.commit()
    return {"migrated": True, "users_created": created}


@app.post("/api/_setup/seed/{code}")
def setup_seed(code: str, x_setup_token: str | None = Header(default=None)) -> dict:
    """Load one borrower of the synthetic book. One borrower per call keeps each call short."""
    _allowed(x_setup_token)
    from app.domain import hooks  # noqa: F401
    from app.seed_book import seed_book
    from sqlalchemy import text

    if not (BOOK / "truth" / f"{code}.json").exists():
        raise HTTPException(404, "No such borrower in the book.")
    with _session() as db:
        if db.execute(text("select 1 from borrowers where code = :c"), {"c": code}).first():
            return {"code": code, "loaded": "already"}
        report = seed_book(db, root=BOOK, only=[code])
        db.commit()
    return {"code": code, "loaded": "now", "documents": report.documents}


@app.post("/api/_setup/backfill-due-dates")
def setup_backfill_due_dates(x_setup_token: str | None = Header(default=None)) -> dict:
    """Give open items raised before the due-date policy their policy date, one ledger event
    each. The same code as `python -m app.cli backfill-due-dates`; safe to call again."""
    _allowed(x_setup_token)
    from app.cli import backfill_due_dates
    from app.domain.monitoring import WorkItem
    from sqlalchemy import func, select

    with _session() as db:
        missing = select(func.count()).select_from(WorkItem).where(WorkItem.status == "open", WorkItem.due_date.is_(None))
        before = db.execute(missing).scalar_one()
        backfill_due_dates(db)  # commits
        after = db.execute(missing).scalar_one()
    return {"open_items_without_due_date_before": before, "after": after}
