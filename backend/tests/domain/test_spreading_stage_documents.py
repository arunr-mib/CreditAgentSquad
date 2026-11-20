"""The spreading stage reads the financial pack, then each MRR report and bank statement of the period."""
import subprocess
import sys
from pathlib import Path

import pytest
from app.core.config import get_settings
from app.domain import hooks, stages, workflow  # noqa: F401
from app.domain.credit import Borrower
from app.domain.facts import Fact
from app.domain.monitoring import Cycle
from app.seed_book import seed_book
from sqlalchemy import select

from evals.book import load_book
from evals.run import _settle
from evals.standin import StandInReader

REPO = Path(__file__).resolve().parents[3]
pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def book(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("innovation") / "out"
    subprocess.run([sys.executable, "-m", "synthetic.books.innovation.generate", "--out", str(out)], cwd=REPO,
                   check=True, capture_output=True)
    return out


@pytest.fixture()
def live_cycle_for(db, book, tmp_path, monkeypatch):
    monkeypatch.setenv("FILE_STORE_DIR", str(tmp_path))
    get_settings.cache_clear()

    def make(code):
        seed_book(db, root=book, current="live", only=[code])
        borrower = db.execute(select(Borrower).where(Borrower.code == code)).scalar_one()
        cycle = db.execute(select(Cycle).where(Cycle.borrower_id == borrower.id, Cycle.status == "open")).scalar_one()
        monkeypatch.setattr(stages, "LLM_FACTORY", lambda: StandInReader(load_book(book, [code])))
        return db, cycle

    yield make
    get_settings.cache_clear()


def test_the_stage_spreads_the_pack_then_each_mrr_report_and_bank_statement(live_cycle_for):
    db, cycle = live_cycle_for("tidewell-medical")
    _settle(db, cycle)  # intake files the documents, then spreading reads them (the stand-in answers)
    keys = {f.key for f in db.execute(select(Fact).where(Fact.borrower_id == cycle.borrower_id, Fact.status != "rejected",
                                                         Fact.period_end == cycle.period_end)).scalars()}
    assert {"saas.mrr", "saas.arr", "saas.customers"} <= keys
    assert {"bank.cash_unrestricted", "bank.cash_restricted"} <= keys
