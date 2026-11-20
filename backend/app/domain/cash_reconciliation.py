"""Bank statements against the compliance certificate: does the cash the borrower counts as unrestricted
match what the bank's own statements show as unrestricted? One question per cause: if a covenant item
already asks it for this period, no second item is raised.

A missing input is never zero: without a bank statement fact or a reported certificate figure there is
nothing to reconcile, and nothing is compared."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.credit import Borrower
from app.domain.facts_service import current_fact
from app.domain.monitoring import CovenantTest, Cycle, WorkItem
from app.domain.work_items import raise_item

COVENANT = "min_unrestricted_cash"
COVENANT_ITEMS = ("covenant.breach", "covenant.reported_mismatch")


def reconcile_cash(db: Session, *, borrower: Borrower, cycle: Cycle) -> WorkItem | None:
    bank = current_fact(db, borrower.id, "bank.cash_unrestricted", cycle.period_end, 0)
    test = db.execute(select(CovenantTest).where(
        CovenantTest.cycle_id == cycle.id, CovenantTest.covenant_id == COVENANT,
        CovenantTest.superseded.is_(False))).scalars().first()
    if bank is None or test is None or test.reported_value is None:
        return None  # a missing input is never zero: nothing to reconcile
    if bank.value == test.reported_value:
        return None
    asked = db.execute(select(WorkItem.id).where(
        WorkItem.cycle_id == cycle.id, WorkItem.item_type.in_(COVENANT_ITEMS),
        WorkItem.evidence["covenant_test_id"].astext == str(test.id))).first()
    if asked is not None:
        return None
    return raise_item(
        db, borrower_id=borrower.id, cycle_id=cycle.id, stage="covenant_testing", item_type="cash.statement_mismatch",
        severity="high", blocks_stage=False,
        title=f"{borrower.name}: bank statements and the certificate disagree on unrestricted cash",
        question="The bank statements show less unrestricted cash than the certificate counts. An account may be "
                 "pledged or restricted. What should we do?",
        allowed_decisions=["reviewed", "ask_borrower", "escalate_to_committee"], required_permission="decide_breach",
        evidence={"bank_fact_id": str(bank.id), "covenant_test_id": str(test.id),
                  "bank_value": format(bank.value, "f"), "certificate_value": format(test.reported_value, "f")},
        dedupe_key=f"cash.statement_mismatch:{borrower.code}:{cycle.period_end}", actor=("system", "reconciliation"))
