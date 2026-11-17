"""Operator commands. Run: PYTHONPATH=backend python -m app.cli <command>

  verify-ledger [--expect-head <seq>:<hash>]
                      recompute every ledger hash and print the chain's head. Keep the printed
                      head somewhere the database's owner cannot reach; pass it back later with
                      --expect-head to detect a chain that was rewritten and rehashed. Exits
                      non-zero if the chain is broken or the stored head is no longer there.
  inventory           list registered agent versions with model and prompt hash
  grant-runtime-role  (owner) give the `squad_runtime` role its rights again: everything the
                      application needs, and only SELECT and INSERT on the ledger
  runtime-login <name>
                      (owner) create or update the login the application connects as, a member
                      of `squad_runtime`. The password is read from RUNTIME_DATABASE_PASSWORD.
"""
import argparse
import os
import re

from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core import ledger
from app.core.config import get_settings
from app.core.db import get_engine
from app.domain.agents import AgentSpecRecord


def verify_ledger(db: Session, expect_head: str | None = None) -> int:
    expected = ledger.parse_head(expect_head) if expect_head else None
    ok, count, problem = ledger.verify_chain(db)
    print(f"ledger: {count} events checked, {'chain intact' if ok else 'CHAIN BROKEN: ' + str(problem)}")
    head = ledger.head(db)
    print(f"head: {head[0]}:{head[1]}" if head else "head: none (the ledger is empty)")
    status = 0 if ok else 1
    if expected is not None:
        mismatch = ledger.check_head(db, expected)
        if mismatch:
            print(f"STORED HEAD NOT FOUND: {mismatch}")
            status = 1
        else:
            print(f"stored head {expected[0]}:{expected[1][:12]}... is still in the chain; "
                  f"events after {expected[0]} are not covered by it")
    else:
        print("no stored head was given: a chain rewritten and rehashed by a database owner would still "
              "verify. Keep the head above outside the database and pass it with --expect-head.")
    guard = ledger.guard_status(db)
    if guard.get("role") and not guard["append_only_for_this_role"]:
        print(f"warning: connected as {guard['role']}, which owns the ledger table or may change its rows; "
              "the application should connect as a member of squad_runtime")
    return status


def inventory(db: Session) -> int:
    for spec in db.execute(select(AgentSpecRecord).order_by(AgentSpecRecord.name, AgentSpecRecord.version)).scalars():
        print(f"{spec.name}@{spec.version}  model={spec.model}  effort={spec.effort}  max_steps={spec.max_steps}  "
              f"prompt={spec.prompt_sha256[:12]}  tools={','.join(spec.tools) or '-'}")
    return 0


def grant_runtime_role(db: Session) -> int:
    if not db.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": ledger.RUNTIME_ROLE}).first():
        print(f"role {ledger.RUNTIME_ROLE} does not exist; a superuser must create it first: "
              f"CREATE ROLE {ledger.RUNTIME_ROLE} NOLOGIN")
        return 1
    db.execute(text(ledger.runtime_role_sql()))
    db.commit()
    print(f"{ledger.RUNTIME_ROLE}: granted the working tables, and SELECT and INSERT only on ledger_events")
    return 0


def runtime_login(db: Session, name: str) -> int:
    password = os.environ.get("RUNTIME_DATABASE_PASSWORD", "")
    if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", name) or name == ledger.RUNTIME_ROLE:
        print("the login needs a plain lower-case name of its own")
        return 2
    if len(password) < 12:
        print("set RUNTIME_DATABASE_PASSWORD to a password of at least 12 characters")
        return 2
    exists = db.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": name}).first()
    quoted = db.execute(text("SELECT quote_literal(:p)"), {"p": password}).scalar()
    options = f"LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {quoted}"
    db.execute(text(f"ALTER ROLE {name} {options}" if exists else f"CREATE ROLE {name} {options}"))
    db.execute(text(f"GRANT {ledger.RUNTIME_ROLE} TO {name}"))
    db.commit()
    print(f"{name}: may sign in, as a member of {ledger.RUNTIME_ROLE}")
    return 0


def restore_files(db: Session, root: str) -> int:
    """Put back document files that are on record but missing from the file store, from a
    freshly generated synthetic book. A hosted demo whose disk is replaced on each deploy keeps
    its database and loses its files; the generator is deterministic, so each file is matched to
    its record by content hash and nothing is restored that was not there before."""
    import hashlib
    from pathlib import Path

    from app.domain.documents import Document

    wanted = {d.sha256: d for d in db.execute(select(Document)).scalars() if not Path(d.storage_path).exists()}
    restored = 0
    for path in sorted(Path(root).rglob("*.pdf")):
        data = path.read_bytes()
        document = wanted.pop(hashlib.sha256(data).hexdigest(), None)
        if document is not None:
            target = Path(document.storage_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            restored += 1
    print(f"document files restored: {restored}; still missing: {len(wanted)}")
    return 0 if not wanted else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command")
    verify = commands.add_parser("verify-ledger")
    verify.add_argument("--expect-head", metavar="<seq>:<hash>")
    commands.add_parser("inventory")
    commands.add_parser("grant-runtime-role")
    commands.add_parser("runtime-login").add_argument("name")
    commands.add_parser("restore-files").add_argument("--book", default="synthetic/out")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2
    if args.command is None:
        print(__doc__)
        return 2
    if args.command in ("grant-runtime-role", "runtime-login"):
        engine = create_engine(get_settings().owner_database_url)  # these change rights: the owner runs them
    else:
        engine = get_engine()
    with Session(engine) as db:
        if args.command == "restore-files":
            return restore_files(db, args.book)
        if args.command == "verify-ledger":
            try:
                return verify_ledger(db, args.expect_head)
            except ValueError as exc:
                print(exc)
                return 2
        if args.command == "inventory":
            return inventory(db)
        try:
            if args.command == "grant-runtime-role":
                return grant_runtime_role(db)
            return runtime_login(db, args.name)
        except DBAPIError as exc:
            print(f"refused by the database: {str(exc.orig).splitlines()[0]}. This command must be run as "
                  "the owner of the tables; creating a login also needs the right to create roles.")
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
