"""The spreading stage reads the financial pack, then each MRR report and bank statement of the period."""
import subprocess
import sys
from pathlib import Path

import pytest
from app.core.config import get_settings
from app.domain import hooks, stages, workflow  # noqa: F401
from app.domain.credit import Borrower
from app.domain.facts import Fact
from app.domain.monitoring import Cycle, WorkItem
from app.domain.org import User
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

    def make(code, tamper=None):
        seed_book(db, root=book, current="live", only=[code])
        borrower = db.execute(select(Borrower).where(Borrower.code == code)).scalar_one()
        cycle = db.execute(select(Cycle).where(Cycle.borrower_id == borrower.id, Cycle.status == "open")).scalar_one()
        monkeypatch.setattr(stages, "LLM_FACTORY", lambda: StandInReader(load_book(book, [code]), tamper=tamper))
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


def _swap_two_expense_lines(agent, answer, context):
    """The pack is read with two lines filed under each other's keys: every figure is on the page, no total
    changes, but each row's label does not name the line it was filed under, so the pack is held."""
    if agent == "spreading" and any(c["key"] == "is.rnd" for c in answer["cells"]):
        for c in answer["cells"]:
            c["key"] = {"is.rnd": "is.gna", "is.gna": "is.rnd"}.get(c["key"], c["key"])
    return answer


def test_a_held_pack_does_not_stop_the_reports_and_a_repaired_pack_ends_with_them_read(live_cycle_for):
    db, cycle = live_cycle_for("tidewell-medical", tamper=_swap_two_expense_lines)
    _settle(db, cycle)

    def keys():
        return {f.key for f in db.execute(select(Fact).where(
            Fact.borrower_id == cycle.borrower_id, Fact.period_end == cycle.period_end,
            Fact.status != "rejected")).scalars()}

    held = db.execute(select(WorkItem).where(WorkItem.cycle_id == cycle.id, WorkItem.status == "open",
                                             WorkItem.stage == "spreading")).scalars().all()
    assert held and cycle.stage == "spreading", "the pack should be held for a person"
    assert {"saas.mrr", "bank.cash_unrestricted"} <= keys()  # read although the pack is held
    analyst = User(email="an@x.example", name="Analyst", role="analyst", password_hash="x")
    db.add(analyst)
    db.flush()
    for item in held:
        workflow.decide_work_item(db, item, user_id=analyst.id, user_role=analyst.role, decision="values_confirmed")
    _settle(db, cycle)
    assert cycle.stage != "spreading"
    assert {"saas.mrr", "saas.arr", "saas.customers", "bank.cash_unrestricted", "bank.cash_restricted"} <= keys()
    # no document was read twice
    assert len([f for f in db.execute(select(Fact).where(
        Fact.borrower_id == cycle.borrower_id, Fact.key == "saas.mrr", Fact.period_end == cycle.period_end,
        Fact.status != "rejected")).scalars()]) == 1


def test_under_assisted_autonomy_each_extra_gets_its_own_reading_review(live_cycle_for, monkeypatch):
    monkeypatch.setenv("EXTRACTION_AUTONOMY", "assisted")
    get_settings.cache_clear()
    try:
        db, cycle = live_cycle_for("tidewell-medical")
        _settle(db, cycle)
        reviewed = {w.evidence["what"] for w in db.execute(select(WorkItem).where(
            WorkItem.cycle_id == cycle.id, WorkItem.item_type == "reading.review")).scalars()}
        assert {"MRR report", "bank statement"} <= reviewed
    finally:
        get_settings.cache_clear()


def test_running_the_stage_again_does_not_read_a_read_document_again(live_cycle_for):
    db, cycle = live_cycle_for("tidewell-medical")
    _settle(db, cycle)
    st = next(s for s in workflow.stages(db, cycle) if s.stage == "spreading")

    def count():
        return len(db.execute(select(Fact).where(Fact.borrower_id == cycle.borrower_id, Fact.key == "saas.mrr",
                                                 Fact.period_end == cycle.period_end)).scalars().all())

    before = count()
    stages.spreading_stage(db, cycle, st)
    assert before >= 1 and count() == before


def _spy(monkeypatch):
    from app.agents import spreading
    calls = []
    real = spreading.spread_document

    def spy(db, **kw):
        calls.append((kw["document"].doc_type, kw.get("scale_override")))
        return real(db, **kw)
    monkeypatch.setattr(spreading, "spread_document", spy)
    return calls


def _stage(db, cycle):
    return next(s for s in workflow.stages(db, cycle) if s.stage == "spreading")


def test_a_units_answer_for_the_mrr_report_does_not_rescale_the_pack(live_cycle_for, monkeypatch):
    db, cycle = live_cycle_for("tidewell-medical")
    _settle(db, cycle)
    st = _stage(db, cycle)
    mrr = stages._documents(db, cycle, "mrr_report")[0]
    calls = _spy(monkeypatch)
    st.detail = {**st.detail, f"scale_override:{mrr.id}": 1000}
    stages.spreading_stage(db, cycle, st)
    assert calls == [("mrr_report", 1000)]  # the pack is settled and not read again; the bank statement is not asked
    assert f"scale_override:{mrr.id}" not in st.detail  # carried out once, then forgotten
    calls.clear()
    stages.spreading_stage(db, cycle, st)
    assert calls == []  # a later run of the stage re-reads (and re-bills) nothing


def test_a_units_answer_for_the_pack_does_not_rescale_the_mrr_report(live_cycle_for, monkeypatch):
    db, cycle = live_cycle_for("tidewell-medical")
    _settle(db, cycle)
    st = _stage(db, cycle)
    pack = stages._documents(db, cycle, stages.statements_wanted(cycle, db.get(Borrower, cycle.borrower_id)))[-1]
    calls = _spy(monkeypatch)
    st.detail = {**st.detail, f"scale_override:{pack.id}": 1000}
    stages.spreading_stage(db, cycle, st)
    assert calls and all(scale == 1000 for kind, scale in calls if kind not in ("mrr_report", "bank_statement"))
    assert [c for c in calls if c[0] in ("mrr_report", "bank_statement")] == []


def test_the_units_decision_keys_the_answer_by_document(live_cycle_for):
    """The hook files the answer under the item's own document, not the stage as a whole."""
    from app.domain.documents import Document
    from app.domain.hooks import on_spread_decision
    db, cycle = live_cycle_for("tidewell-medical")
    _settle(db, cycle)
    mrr = db.execute(select(Document).where(Document.borrower_id == cycle.borrower_id,
                                            Document.doc_type == "mrr_report")).scalars().first()
    user = db.execute(select(User)).scalars().first()
    item = WorkItem(borrower_id=cycle.borrower_id, cycle_id=cycle.id, stage="spreading", item_type="spread.scale_conflict",
                    severity="high", title="units", question="units?", evidence={"document_id": str(mrr.id)}, status="open")
    db.add(item)
    db.flush()
    on_spread_decision(db, item, user, "in_thousands", "")
    detail = _stage(db, cycle).detail
    assert detail.get(f"scale_override:{mrr.id}") == 1000 and "scale_override" not in detail


def test_an_extra_that_stored_only_proposed_figures_or_none_is_not_read_and_billed_again(live_cycle_for, monkeypatch):
    from sqlalchemy import update
    db, cycle = live_cycle_for("tidewell-medical")
    _settle(db, cycle)
    st = _stage(db, cycle)
    mrr = stages._documents(db, cycle, "mrr_report")[0]
    bank = stages._documents(db, cycle, "bank_statement")[0]
    # the MRR report's figures are held (proposed); the bank statement stored nothing (its facts are rejected)
    db.execute(update(Fact).where(Fact.document_id == mrr.id).values(status="proposed"))
    db.execute(update(Fact).where(Fact.document_id == bank.id).values(status="rejected"))
    db.flush()
    calls = _spy(monkeypatch)
    stages.spreading_stage(db, cycle, st)
    assert calls == []  # the stage already read both once; nothing asks for a retry
    # a person's retry request reads that one document again, once
    st.detail = {**st.detail, f"retry:{mrr.id}": True}
    stages.spreading_stage(db, cycle, st)
    assert [c[0] for c in calls] == ["mrr_report"]
    stages.spreading_stage(db, cycle, st)
    assert [c[0] for c in calls] == ["mrr_report"]


def test_a_units_answer_on_an_item_with_no_document_is_refused_not_dropped(live_cycle_for):
    from app.domain.hooks import on_spread_decision
    db, cycle = live_cycle_for("tidewell-medical")
    _settle(db, cycle)
    user = db.execute(select(User)).scalars().first()
    item = WorkItem(borrower_id=cycle.borrower_id, cycle_id=cycle.id, stage="spreading", item_type="spread.scale_conflict",
                    severity="high", title="units", question="units?", evidence={}, status="open")
    db.add(item)
    db.flush()
    with pytest.raises(ValueError, match="no document"):
        on_spread_decision(db, item, user, "in_thousands", "")
    on_spread_decision(db, item, user, "retry", "")  # a plain retry needs no document
