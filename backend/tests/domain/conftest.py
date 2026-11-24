"""Fixtures for the domain tests that need a whole innovation-book client run through part of its cycle."""
import contextlib

import pytest
from sqlalchemy import select

from evals.book import generate_book, load_book
from evals.run import LoadedBorrower, _settle, scratch_file_store
from evals.standin import StandInReader

STAGE_ORDER = ("awaiting_package", "intake", "spreading", "covenant_testing", "borrowing_base", "signals")


@pytest.fixture(scope="session")
def innovation_book_root(tmp_path_factory):
    return generate_book(tmp_path_factory.mktemp("innovation-book") / "out", "innovation")


@pytest.fixture()
def innovation_cycle(engine, innovation_book_root):
    """`innovation_cycle(code, through="covenant_testing")` loads the client live (stand-in reader, nothing
    committed) and runs its cycle until the named stage is done or the cycle waits on a person.
    Returns (db, borrower row, cycle)."""
    from app.domain import stages, workflow
    from app.domain.credit import Borrower as BorrowerRow
    from app.domain.monitoring import Cycle
    from sqlalchemy.orm import Session

    with contextlib.ExitStack() as stack:
        def run(code: str, through: str = "covenant_testing"):
            stack.enter_context(scratch_file_store())
            book = load_book(innovation_book_root, [code])
            borrower = book.get(code)
            loaded = stack.enter_context(LoadedBorrower(engine, book, borrower))
            db = Session(bind=loaded.conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
            stack.callback(db.close)
            reader = StandInReader(book)
            previous = stages.LLM_FACTORY
            stages.LLM_FACTORY = lambda: reader
            stack.callback(setattr, stages, "LLM_FACTORY", previous)
            row = db.execute(select(BorrowerRow).where(BorrowerRow.code == code)).scalar_one()
            cycle = db.execute(select(Cycle).where(Cycle.borrower_id == row.id, Cycle.status == "open",
                                                   Cycle.period_end == borrower.current_period)).scalar_one()
            for _ in range(10):
                _settle(db, cycle)
                rows = {s.stage: s.status for s in workflow.stages(db, cycle)}
                if rows.get(through) == "done" or cycle.status == "closed":
                    break
                if rows.get(cycle.stage) == "needs_person" and STAGE_ORDER.index(cycle.stage) >= STAGE_ORDER.index(through):
                    break
                if rows.get(cycle.stage) == "needs_person":
                    break  # waits on a person before the stage was reached
            return db, row, cycle

        yield run
