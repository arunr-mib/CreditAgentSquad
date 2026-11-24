"""A corrected figure in history loaded from the book: totals, metrics and covenant tests follow.

Kept apart from test_corrections.py: the book fixture holds one transaction open for the whole
module, and with it the ledger's lock, so tests on another connection cannot share a module."""
from decimal import Decimal as D

import pytest
from app.core.ledger import LedgerEvent
from app.domain import corrections
from app.domain.credit import Borrower
from app.domain.facts import CalcRun, Fact
from app.domain.facts_service import current_fact
from app.domain.monitoring import CovenantTest, WorkItem
from app.domain.org import User
from sqlalchemy import select
from support.agent_book import book, book_db  # noqa: F401


def _tests(db, borrower, period):
    return {t.covenant_id: t for t in db.execute(select(CovenantTest).where(
        CovenantTest.borrower_id == borrower.id, CovenantTest.period_end == period,
        CovenantTest.superseded.is_(False))).scalars()}


def test_a_reclassification_withholds_results_until_the_statements_foot_then_retests(book):  # noqa: F811
    db, _ = book
    borrower = db.execute(select(Borrower).where(Borrower.code == "vantry-freight")).scalar_one()
    analyst = db.execute(select(User).where(User.role == "analyst")).scalars().first()
    periods = sorted({t.period_end for t in db.execute(select(CovenantTest).where(
        CovenantTest.borrower_id == borrower.id)).scalars()})
    period = next(p for p in periods if all(t.outcome == "compliant" for t in _tests(db, borrower, p).values()))
    before = _tests(db, borrower, period)
    assert "total_leverage" in before
    debt = current_fact(db, borrower.id, "bs.long_term_debt", period, 0)
    equity = current_fact(db, borrower.id, "bs.total_equity", period, 0)
    liabilities = current_fact(db, borrower.id, "bs.total_liabilities", period, 0)
    moved = current_fact(db, borrower.id, "bs.total_assets", period, 0).value

    # step one: debt is restated upward. The balance sheet no longer balances, so nothing
    # calculated from it stays in use and no covenant can be tested
    _, first = corrections.correct(db, debt, value=debt.value + moved, user_id=analyst.id,
                                   reason="Shareholder loan was booked in equity; it is debt.")
    assert first["totals"] == "does_not_foot" and first["retired"] > 0
    assert liabilities.status == "superseded"
    assert current_fact(db, borrower.id, "bs.total_liabilities", period, 0) is None
    assert {t.outcome for t in _tests(db, borrower, period).values()} == {"cannot_test"}
    open_types = [w.item_type for w in db.execute(select(WorkItem).where(
        WorkItem.borrower_id == borrower.id, WorkItem.status == "open", WorkItem.created_at >= debt.created_at))
        .scalars() if w.item_type.startswith(("spread.", "fact.", "covenant.cannot"))]
    assert open_types.count("spread.does_not_foot") == 1 and "covenant.cannot_test" not in open_types

    # step two: the other side of the entry. The statements foot again and everything is redone
    _, second = corrections.correct(db, equity, value=equity.value - moved, user_id=analyst.id,
                                    reason="Shareholder loan was booked in equity; it is debt.")
    assert second["totals"] == "recalculated"
    assert current_fact(db, borrower.id, "bs.total_liabilities", period, 0).value == liabilities.value + moved
    after = _tests(db, borrower, period)
    assert set(after) == set(before)
    assert after["total_leverage"].outcome in ("breach", "breach_reported_compliant")
    assert after["total_leverage"].value > before["total_leverage"].value
    for test in after.values():
        assert test.value_fact_id is None or db.get(Fact, test.value_fact_id).status == "verified"
    # a person is told the outcome changed, and the breach is raised like any other
    types = {w.item_type for w in db.execute(select(WorkItem).where(
        WorkItem.borrower_id == borrower.id, WorkItem.status == "open")).scalars()}
    assert "fact.correction_changed_outcome" in types and types & {"covenant.breach", "covenant.reported_mismatch"}
    actions = {e.action for e in db.execute(select(LedgerEvent).where(
        LedgerEvent.action.in_(("fact.results_retired", "fact.results_recalculated")))).scalars()}
    assert actions == {"fact.results_retired", "fact.results_recalculated"}
    # early warning signals for the period were computed from the old figures: closed and run again
    from app.domain.monitoring import Signal
    signals = list(db.execute(select(Signal).where(Signal.borrower_id == borrower.id,
                                                   Signal.period_end == period)).scalars())
    assert second["signals"] and any(s.status == "closed" for s in signals)
    for signal in signals:
        if signal.status != "closed":
            for value in signal.basis.values():
                if isinstance(value, dict) and value.get("fact_id"):
                    assert db.get(Fact, value["fact_id"]).status in ("verified", "confirmed"), signal.rule_id
    # nothing still in use was calculated from a figure that is not
    runs = {r.id: r for r in db.execute(select(CalcRun).where(CalcRun.borrower_id == borrower.id)).scalars()}
    for fact in db.execute(select(Fact).where(Fact.borrower_id == borrower.id,
                                              Fact.status.in_(("verified", "confirmed")))).scalars():
        for entry in (runs[fact.calc_run_id].inputs if fact.calc_run_id else []):
            if entry.get("fact_id"):
                assert db.get(Fact, entry["fact_id"]).status in ("verified", "confirmed"), (fact.key, entry)


def test_a_calculated_figure_cannot_be_corrected(book):  # noqa: F811
    db, _ = book
    borrower = db.execute(select(Borrower).where(Borrower.code == "vantry-freight")).scalar_one()
    analyst = db.execute(select(User).where(User.role == "analyst")).scalars().first()
    calculated = db.execute(select(Fact).where(Fact.borrower_id == borrower.id, Fact.kind == "calculated",
                                               Fact.status == "verified")).scalars().first()
    with pytest.raises(ValueError, match="correct the figure it was calculated from"):
        corrections.correct(db, calculated, value=D(1), user_id=analyst.id, reason="Looks wrong.")
