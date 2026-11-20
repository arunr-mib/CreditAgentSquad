from decimal import Decimal

import pytest
from app.domain.cash_reconciliation import reconcile_cash
from app.domain.facts_service import current_fact
from app.domain.monitoring import WorkItem
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
