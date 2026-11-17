"""Operator commands. Run: PYTHONPATH=backend python -m app.cli <command>

  verify-ledger   recompute every ledger hash; exits non-zero if the chain is broken
  inventory       list registered agent versions with model and prompt hash
"""
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import ledger
from app.core.db import get_engine
from app.domain.agents import AgentSpecRecord


def verify_ledger(db: Session) -> int:
    ok, count, problem = ledger.verify_chain(db)
    print(f"ledger: {count} events checked, {'chain intact' if ok else 'CHAIN BROKEN: ' + str(problem)}")
    return 0 if ok else 1


def inventory(db: Session) -> int:
    for spec in db.execute(select(AgentSpecRecord).order_by(AgentSpecRecord.name, AgentSpecRecord.version)).scalars():
        print(f"{spec.name}@{spec.version}  model={spec.model}  effort={spec.effort}  max_steps={spec.max_steps}  "
              f"prompt={spec.prompt_sha256[:12]}  tools={','.join(spec.tools) or '-'}")
    return 0


COMMANDS = {"verify-ledger": verify_ledger, "inventory": inventory}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1 or argv[0] not in COMMANDS:
        print(__doc__)
        return 2
    with Session(get_engine()) as db:
        return COMMANDS[argv[0]](db)


if __name__ == "__main__":
    raise SystemExit(main())
