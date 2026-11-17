"""Load a database for the repair journeys (frontend/e2e/repair.mjs). No model is called.

The normal seed (`python -m app.seed_book`) loads every borrower's current period from the book's
ground truth, so it holds no spread with figures waiting for a person. This loads three borrowers
through the live path instead, with the evaluation harness's stand-in reader answering for the
model, and then loads the rest of the book as the normal seed does:

- harrowgate-precision: the stand-in's answer is made wrong in four cells, so the spread rests on
  `spread.value_unverified` with two figures held for a doubtful row label and two with no value;
- ashgrove-fleet: the book's missing-page scenario, resting on `spread.does_not_foot`;
- larkspur-environmental: a clean borrower run to review preparation, so a review sheet with
  drafted commentary is waiting for approval.

Run it on an empty, migrated database, from the repository root:

    cd backend && uv run alembic upgrade head && cd ..
    PYTHONPATH=backend:. uv run python frontend/e2e/seed_repair.py

The repair journey records real corrections and a decision, so it needs a fresh load each time.
"""
import json
import sys

from app.core.db import get_engine
from app.domain import hooks, stages  # noqa: F401  (registers stage handlers and decision hooks)
from app.domain.credit import Borrower
from app.domain.monitoring import Cycle, WorkItem
from app.seed_book import seed_book
from app.seed_users import seed_users
from sqlalchemy import select
from sqlalchemy.orm import Session

from evals.book import load_book
from evals.run import _settle
from evals.standin import StandInReader

HELD = "harrowgate-precision"
LIVE = [HELD, "ashgrove-fleet", "larkspur-environmental"]


def _bump(figure: str) -> str:
    """Change the last digit, keeping the figure well formed."""
    index = max(i for i, ch in enumerate(figure) if ch.isdigit())
    return figure[:index] + str((int(figure[index]) + 1) % 10) + figure[index + 1:]


def tamper(agent, answer, context):
    """A reader that is wrong in four cells of one borrower's statements."""
    if agent != "spreading" or context["borrower"] != HELD:
        return answer
    cells = {c["key"]: c for c in answer["cells"]}
    if "bs.inventory" in cells:  # a label that is not on the page: nothing is stored
        cells["bs.inventory"]["printed_label"] = "Inventories, net of reserves"
    payable, accrued = cells.get("bs.accounts_payable"), cells.get("bs.accrued_liabilities")
    if payable and accrued:  # two rows filed under each other's lines: both are held
        payable["key"], accrued["key"] = "bs.accrued_liabilities", "bs.accounts_payable"
    if "is.interest_expense" in cells:  # a figure that is not on the page: nothing is stored
        cells["is.interest_expense"]["printed_figure"] = _bump(cells["is.interest_expense"]["printed_figure"])
    return answer


def main() -> None:
    reader = StandInReader(load_book(), tamper=tamper)
    stages.LLM_FACTORY = lambda: reader
    with Session(get_engine()) as db:
        if db.execute(select(Borrower.id).limit(1)).first():
            sys.exit("This database already holds borrowers. Load the repair journeys' data into an empty, migrated database.")
        seed_users(db)
        db.commit()
        for code in LIVE:
            seed_book(db, current="live", only=[code])
            db.commit()
            borrower = db.execute(select(Borrower).where(Borrower.code == code)).scalar_one()
            cycle = db.execute(select(Cycle).where(Cycle.borrower_id == borrower.id, Cycle.status == "open")
                               .order_by(Cycle.period_end.desc())).scalars().first()
            _settle(db, cycle)
            db.commit()
            waiting = sorted(w.item_type for w in db.execute(select(WorkItem).where(
                WorkItem.borrower_id == borrower.id, WorkItem.status == "open")).scalars())
            print(f"{code}: rests at {cycle.stage} on {', '.join(waiting) or 'nothing'}", file=sys.stderr)
        report = seed_book(db, current="seeded")
        db.commit()
    print(json.dumps(report.__dict__, indent=1, default=str))


if __name__ == "__main__":
    main()
