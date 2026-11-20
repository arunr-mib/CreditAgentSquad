from decimal import Decimal

import pytest
from app.domain.cash_reconciliation import reconcile_cash
from app.domain.covenant_service import DEFAULT_TOLERANCE
from app.domain.facts_service import current_fact
from app.domain.monitoring import CovenantTest, WorkItem
from app.domain.work_items import raise_item
from sqlalchemy import select

pytestmark = pytest.mark.slow


def items(db, borrower, kind):
    return list(db.execute(select(WorkItem).where(WorkItem.borrower_id == borrower.id,
                                                  WorkItem.item_type == kind)).scalars())


def test_tidewell_gets_one_mismatch_for_the_certificate_that_counts_the_escrow_account(innovation_cycle):
    db, borrower, cycle = innovation_cycle("tidewell-medical", through="covenant_testing")
    assert len(items(db, borrower, "cash.statement_mismatch")) == 1  # the covenant stage raised it itself
    first = reconcile_cash(db, borrower=borrower, cycle=cycle)
    again = reconcile_cash(db, borrower=borrower, cycle=cycle)
    assert first is not None and first.item_type == "cash.statement_mismatch" and first.severity == "high"
    assert first.blocks_stage is False and first.required_permission == "decide_breach"
    assert Decimal(first.evidence["bank_value"]) == Decimal("4300000")
    assert Decimal(first.evidence["certificate_value"]) == Decimal("5300000")
    assert again is not None and again.id == first.id  # once per period
    assert len(items(db, borrower, "cash.statement_mismatch")) == 1


def test_dataflake_already_asks_the_question_so_it_gets_no_second_item(innovation_cycle):
    db, borrower, cycle = innovation_cycle("dataflake", through="covenant_testing")
    assert items(db, borrower, "covenant.reported_mismatch")
    assert reconcile_cash(db, borrower=borrower, cycle=cycle) is None
    assert items(db, borrower, "cash.statement_mismatch") == []


def test_a_client_whose_certificate_agrees_with_the_bank_gets_nothing(innovation_cycle):
    db, borrower, cycle = innovation_cycle("ferrogate-cloud", through="covenant_testing")
    assert current_fact(db, borrower.id, "bank.cash_unrestricted", cycle.period_end, 0) is not None
    assert reconcile_cash(db, borrower=borrower, cycle=cycle) is None


def test_no_bank_statement_means_no_reconciliation_and_no_zero(innovation_cycle):
    db, borrower, cycle = innovation_cycle("lumora-health", through="covenant_testing")  # the bank statement is late
    assert current_fact(db, borrower.id, "bank.cash_unrestricted", cycle.period_end, 0) is None
    assert reconcile_cash(db, borrower=borrower, cycle=cycle) is None
    assert items(db, borrower, "cash.statement_mismatch") == []


def _fresh(db, borrower, cycle):
    """Tidewell as the stage left it, with the cash item taken away so the reconciliation runs afresh."""
    for item in items(db, borrower, "cash.statement_mismatch"):
        db.delete(item)
    db.flush()
    return db.execute(select(CovenantTest).where(
        CovenantTest.cycle_id == cycle.id, CovenantTest.covenant_id == "min_unrestricted_cash",
        CovenantTest.superseded.is_(False))).scalars().first()


def test_a_difference_within_the_engines_dollar_tolerance_raises_nothing(innovation_cycle):
    db, borrower, cycle = innovation_cycle("tidewell-medical", through="covenant_testing")
    test = _fresh(db, borrower, cycle)
    bank = current_fact(db, borrower.id, "bank.cash_unrestricted", cycle.period_end, 0)
    test.reported_value = bank.value + Decimal("0.40")
    db.flush()
    assert reconcile_cash(db, borrower=borrower, cycle=cycle) is None
    test.reported_value = bank.value + DEFAULT_TOLERANCE["usd"] + Decimal("0.01")
    db.flush()
    assert reconcile_cash(db, borrower=borrower, cycle=cycle) is not None


def test_a_covenant_breach_does_not_suppress_the_cash_item_but_a_reported_mismatch_does(innovation_cycle):
    db, borrower, cycle = innovation_cycle("tidewell-medical", through="covenant_testing")
    test = _fresh(db, borrower, cycle)
    common = dict(borrower_id=borrower.id, cycle_id=cycle.id, stage="covenant_testing", title="t",
                  question="What now?", allowed_decisions=["escalate_to_committee"],
                  evidence={"covenant_test_id": str(test.id)})
    raise_item(db, item_type="covenant.breach", **common)
    cash = reconcile_cash(db, borrower=borrower, cycle=cycle)
    assert cash is not None and len(items(db, borrower, "covenant.breach")) == 1
    db.delete(cash)
    db.flush()
    raise_item(db, item_type="covenant.reported_mismatch", **common).status = "decided"
    db.flush()
    assert reconcile_cash(db, borrower=borrower, cycle=cycle) is None  # decided still counts: asked already


def test_once_per_period_even_after_the_item_is_decided_and_the_wording_is_neutral(innovation_cycle):
    db, borrower, cycle = innovation_cycle("tidewell-medical", through="covenant_testing")
    first = items(db, borrower, "cash.statement_mismatch")[0]
    first.status, first.decision = "decided", "reviewed"
    db.flush()
    again = reconcile_cash(db, borrower=borrower, cycle=cycle)
    assert again is not None and again.id == first.id
    assert len(items(db, borrower, "cash.statement_mismatch")) == 1
    assert "lower unrestricted cash than the certificate counts" in first.question
    assert not any(ch.isdigit() for ch in first.question)


def test_the_stage_says_why_reconciliation_waited_only_when_it_did(innovation_cycle):
    from datetime import date
    from types import SimpleNamespace

    from app.domain import workflow
    from app.domain.cash_reconciliation import waiting_reason

    db, borrower, cycle = innovation_cycle("tidewell-medical", through="covenant_testing")
    stage = next(s for s in workflow.stages(db, cycle) if s.stage == "covenant_testing")
    assert "cash_reconciliation_waiting" not in stage.detail and waiting_reason(db, borrower, cycle) is None
    # a period with no bank statement on file (the certificate's figure is still there to compare)
    no_statement = SimpleNamespace(id=cycle.id, period_end=date(2020, 1, 31))
    assert "bank.cash_unrestricted" in waiting_reason(db, borrower, no_statement)
    assert reconcile_cash(db, borrower=borrower, cycle=no_statement) is None
