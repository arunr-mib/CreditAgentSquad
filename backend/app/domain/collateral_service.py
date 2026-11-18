"""Borrowing base review: code recalculates the base from the aging and inventory listing under
the terms in force, reconciles every line to the borrower's certificate, and raises a work item
for a mismatch or an over-advance."""
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.calc import borrowing_base as bb_calc
from app.core import ledger
from app.domain.covenant_service import governing_terms
from app.domain.credit import Borrower, Facility
from app.domain.facts import CalcRun
from app.domain.facts_service import add_fact, current_fact
from app.domain.monitoring import BorrowingBaseReview, Cycle
from app.domain.work_items import raise_item

ENGINE_VERSION = "borrowing-base-1"
DEFAULT_TOLERANCE = Decimal("1")


def review_borrowing_base(
    db: Session, *, borrower: Borrower, facility: Facility, period_end: date, ar_rows: list[dict[str, Any]],
    inventory_rows: list[dict[str, Any]], certificate: dict[str, Decimal], outstanding: Decimal,
    letters_of_credit: Decimal, cycle: Cycle | None = None, origin: str = "live", raise_items: bool = True,
    tolerance: Decimal = DEFAULT_TOLERANCE, source: dict[str, Any] | None = None, require_all_lines: bool = False,
    actor: tuple[str, str] = ("system", "borrowing_base"),
) -> BorrowingBaseReview:
    """`ar_rows` and `inventory_rows` are the listing rows with decimals as strings; `certificate`
    maps the calculation's line names to what the borrower reported; `source` records where the
    rows came from (document and fact ids), so the review can be traced. With `require_all_lines`
    (a certificate read from a document), a line the recalculation has a figure for and the
    certificate reading lacks is reported as a difference."""
    version_row, version = governing_terms(db, facility, period_end)
    terms = version.terms.borrowing_base if version_row is not None else None
    result = bb_calc.compute_borrowing_base(
        [bb_calc.ArRow.from_mapping(r) for r in ar_rows],
        [bb_calc.InventoryRow(r["category"], Decimal(str(r["amount"]))) for r in inventory_rows],
        terms, outstanding, letters_of_credit)
    differences = bb_calc.reconcile(result, certificate, tolerance) if not result.errors else []
    if not result.errors and require_all_lines:
        # only lines the certificate reports can be compared, so a line the recalculation has a
        # figure for and the reading left out is itself a difference: otherwise leaving lines
        # out is the way to make a certificate "agree"
        differences += [bb_calc.LineDifference(name, value, Decimal(0), value, "not_reported")
                        for name, value in result.lines.items()
                        if name not in certificate and name != "over_advance" and value not in (None, Decimal(0))]
    mismatches = [d for d in differences if d.status != "match"]

    calc = CalcRun(
        borrower_id=borrower.id, formula_key="borrowing_base", formula_version=ENGINE_VERSION,
        terms_version_id=version_row.id if version_row else None, period_end=period_end,
        engine_version=ENGINE_VERSION,
        inputs=ledger._jsonable({"ar_rows": ar_rows, "inventory_rows": inventory_rows, "outstanding": outstanding,
                                 "letters_of_credit": letters_of_credit, "source": source or {}}),
        outputs=ledger._jsonable(result.lines),
        trace=ledger._jsonable({
            "customers": [vars(c) for c in result.customers], "excluded_by_flag": result.excluded_by_flag,
            "inventory_ineligible_by_category": result.inventory_ineligible_by_category,
            "reserves_by_name": result.reserves_by_name}),
        error="; ".join(e.message for e in result.errors) or None,
        created_by_type=actor[0], created_by_id=actor[1])
    db.add(calc)
    db.flush()

    if result.errors:
        outcome = "cannot_compute"
    elif result.is_over_advance:
        outcome = "over_advance"
    elif mismatches:
        outcome = "mismatch"
    else:
        outcome = "agrees"
    review = BorrowingBaseReview(
        borrower_id=borrower.id, facility_id=facility.id, cycle_id=cycle.id if cycle else None,
        terms_version_id=version_row.id if version_row else None, period_end=period_end, calc_run_id=calc.id,
        computed=ledger._jsonable(result.lines), certificate=ledger._jsonable(certificate),
        differences=ledger._jsonable([vars(d) for d in differences]),
        availability=result.availability, over_advance=result.over_advance, outcome=outcome, origin=origin)
    db.add(review)
    db.flush()
    if result.availability is not None:
        add_fact(db, borrower_id=borrower.id, facility_id=facility.id, key="bb.availability", period_end=period_end,
                 months=0, value=result.availability, kind="calculated", calc_run_id=calc.id, actor=actor)
    ledger.record(db, actor_type=actor[0], actor_id=actor[1], action="borrowing_base.reviewed",
                  entity_type="borrowing_base_review", entity_id=review.id,
                  payload={"period_end": period_end, "outcome": outcome, "availability": result.availability,
                           "over_advance": result.over_advance, "mismatched_lines": [d.line for d in mismatches]})
    if raise_items:
        _raise_for(db, borrower, facility, cycle, review, mismatches, result, actor)
    db.flush()
    return review


def _raise_for(db, borrower, facility, cycle, review, mismatches, result, actor) -> None:
    common = dict(borrower_id=borrower.id, facility_id=facility.id, cycle_id=cycle.id if cycle else None,
                  stage="borrowing_base", actor=actor)
    evidence: dict[str, Any] = {"borrowing_base_review_id": str(review.id), "calc_run_id": str(review.calc_run_id)}
    key = f"{facility.id}:{review.period_end}"
    if review.outcome == "over_advance":
        raise_item(
            db, item_type="bb.over_advance", severity="critical",
            title=f"{borrower.name}: the line is over-advanced",
            question="Borrowings exceed the recalculated borrowing base. Require a paydown, or approve a temporary over-advance?",
            allowed_decisions=["paydown_required", "temporary_overadvance_approved", "escalate_to_committee"],
            required_permission="decide_breach", evidence=evidence, dedupe_key=f"bb.over_advance:{key}", **common)
    if mismatches:
        raise_item(
            db, item_type="bb.certificate_mismatch", severity="high" if review.outcome != "over_advance" else "medium",
            title=f"{borrower.name}: the borrowing base certificate does not agree with the recalculation",
            question="One or more certificate lines differ from the recalculation. Accept the bank's figures, or ask the borrower to resubmit?",
            allowed_decisions=["bank_figures_stand", "borrower_to_resubmit", "certificate_correct"],
            evidence={**evidence, "lines": ledger._jsonable([vars(d) for d in mismatches])},
            dedupe_key=f"bb.certificate_mismatch:{key}", **common)
    if review.outcome == "cannot_compute":
        raise_item(
            db, item_type="bb.certificate_mismatch", severity="medium",
            title=f"{borrower.name}: the borrowing base could not be recalculated",
            question="The collateral listing could not be used as provided. Correct the listing, or request a new certificate?",
            allowed_decisions=["listing_corrected", "borrower_to_resubmit"],
            evidence={**evidence, "errors": [e.to_dict() for e in result.errors]},
            dedupe_key=f"bb.cannot_compute:{key}", **common)


def store_line_availability(db: Session, *, borrower: Borrower, facility: Facility, period_end: date,
                            actor: tuple[str, str] = ("system", "borrowing_base")):
    """For a revolver with no borrowing base, availability is commitment less outstanding, both
    taken from the system of record at the period end. Stored as a calculated fact that names
    the two system facts. Returns None when either is missing: nothing is assumed."""
    if facility.facility_type != "revolver" or facility.has_borrowing_base:
        return None
    commitment = current_fact(db, borrower.id, "sys.commitment", period_end, 0)
    outstanding = current_fact(db, borrower.id, "sys.revolver_outstanding", period_end, 0)
    if commitment is None or outstanding is None:
        return None
    existing = current_fact(db, borrower.id, "bb.availability", period_end, 0)
    value = commitment.value - outstanding.value
    if existing is not None and existing.value == value:
        return existing
    calc = CalcRun(
        borrower_id=borrower.id, formula_key="line_availability", formula_version="1", period_end=period_end,
        engine_version=ENGINE_VERSION,
        inputs=[{"key": f.key, "fact_id": str(f.id), "value": str(f.value)} for f in (commitment, outstanding)],
        outputs={"availability": str(value)}, created_by_type=actor[0], created_by_id=actor[1])
    db.add(calc)
    db.flush()
    return add_fact(db, borrower_id=borrower.id, facility_id=facility.id, key="bb.availability",
                    period_end=period_end, months=0, value=value, kind="calculated", calc_run_id=calc.id, actor=actor)
