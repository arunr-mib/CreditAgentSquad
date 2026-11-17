"""Test every covenant in force for a loan and period, from approved terms and stored facts.

Code computes every test itself. The borrower's certificate is evidence to reconcile against,
never the trigger. Each test writes a calculation record naming every input fact.
"""
import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.calc import covenants as calc_cov
from app.calc import template
from app.calc import terms as calc_terms
from app.calc.periods import FactValue
from app.core import ledger
from app.domain.credit import Borrower, Facility
from app.domain.facts import CalcRun
from app.domain.facts_service import add_fact, current_fact
from app.domain.monitoring import CovenantTest, Cycle, WorkItem
from app.domain.terms import TermsVersion
from app.domain.work_items import raise_item

DEFAULT_TOLERANCE = {"ratio": Decimal("0.005"), "usd": Decimal("1"), "pct": Decimal("0.0005"), "days": Decimal("0.5")}
BREACH_DECISIONS = ["waiver_requested", "reservation_of_rights", "escalate_to_committee", "not_a_breach"]


def fact_provider(db: Session, borrower_id: uuid.UUID):
    """Facts for the calculation engine: the latest usable fact for a line and period."""

    def get(key: str, period_end: date, months: int) -> FactValue | None:
        # the engine asks for every line by the period's month count; a balance has no duration
        # and is stored with zero months
        line = template.line_info(key)
        if line is not None and not line.flow:
            months = 0
        fact = current_fact(db, borrower_id, key, period_end, months)
        return None if fact is None else FactValue(fact.value, str(fact.id))

    return get


def version_payload(row: TermsVersion) -> dict[str, Any]:
    return {"id": str(row.id), "facility_id": str(row.facility_id), "version": row.version, "status": row.status,
            "effective_from": row.effective_from, "effective_to": row.effective_to, "terms": row.terms}


def governing_terms(db: Session, facility: Facility, period_end: date) -> tuple[TermsVersion | None, Any]:
    """The approved (or superseded) version whose dates contain the period end. A proposed
    version never governs. Returns (row, parsed version) or (None, error)."""
    rows = list(db.execute(select(TermsVersion).where(TermsVersion.facility_id == facility.id)).scalars())
    usable = [r for r in rows if r.status in ("approved", "superseded")]
    in_force = calc_terms.terms_in_force([version_payload(r) for r in usable], period_end)
    if in_force.version is None:
        return None, in_force.error
    row = next(r for r in usable if str(r.id) == in_force.version.id)
    return row, in_force.version


def _reported(db: Session, borrower_id: uuid.UUID, covenant_id: str, period_end: date):
    """What the certificate says for this covenant, if a certificate has been read."""
    value = current_fact(db, borrower_id, f"cert.{covenant_id}.value", period_end, 0)
    threshold = current_fact(db, borrower_id, f"cert.{covenant_id}.threshold", period_end, 0)
    flag = current_fact(db, borrower_id, f"cert.{covenant_id}.in_compliance", period_end, 0)
    if value is None and threshold is None and flag is None:
        return None, None
    entry = calc_cov.CertificateEntry(
        value.value if value else None, threshold.value if threshold else None,
        None if flag is None else flag.value == 1)
    return entry, value


def _calc_run(db, borrower, version_row, covenant, period_end, result, calc_id, actor) -> CalcRun:
    calc = CalcRun(
        id=calc_id, borrower_id=borrower.id, formula_key=f"covenant.{covenant.id}",
        formula_version=f"{covenant.archetype}@terms-v{version_row.version}", terms_version_id=version_row.id,
        period_end=period_end, engine_version=result.engine_version,
        inputs=[i.to_dict() for i in result.trace.inputs],
        outputs={"value": result.value, "raw_value": result.raw_value, "threshold": result.threshold,
                 "operator": result.operator, "passed": result.passed, "headroom": result.headroom,
                 "headroom_pct": result.headroom_pct},
        trace={"expression": result.expression,
               "addbacks": [{"name": a.name, "raw": a.raw, "cap_type": a.cap_type, "cap_value": a.cap_value,
                             "cap_limit": a.cap_limit, "applied": a.applied, "capped": a.capped}
                            for a in result.trace.addbacks],
               "steps": [{"op": s.op, "label": s.label, "value": s.value, "period_end": s.period_end}
                         for s in result.trace.steps]},
        error="; ".join(e.message for e in result.errors) or None,
        created_by_type=actor[0], created_by_id=actor[1])
    calc.outputs = ledger._jsonable(calc.outputs)
    calc.trace = ledger._jsonable(calc.trace)
    db.add(calc)
    db.flush()
    return calc


def run_covenant_tests(
    db: Session, *, borrower: Borrower, facility: Facility, period_end: date, cycle: Cycle | None = None,
    origin: str = "live", raise_items: bool = True, actor: tuple[str, str] = ("system", "covenants"),
    tolerance: dict[str, Decimal] | None = None,
) -> list[CovenantTest]:
    """Run every covenant that is tested at this period end. Earlier tests for the same loan,
    covenant and period are kept and marked superseded."""
    tolerance = tolerance or DEFAULT_TOLERANCE
    version_row, version = governing_terms(db, facility, period_end)
    if version_row is None:
        test = CovenantTest(
            borrower_id=borrower.id, facility_id=facility.id, cycle_id=cycle.id if cycle else None,
            covenant_id="*", covenant_name="All covenants", period_end=period_end, outcome="cannot_test",
            error=version.message if version is not None else "no terms in force", origin=origin)
        db.add(test)
        db.flush()
        if raise_items:
            raise_item(db, borrower_id=borrower.id, facility_id=facility.id, cycle_id=cycle.id if cycle else None,
                       stage="covenant_testing", item_type="covenant.cannot_test", severity="high",
                       title=f"{facility.name}: no approved terms in force",
                       question="No approved terms cover this period, so no covenant can be tested. Approve the extracted terms?",
                       allowed_decisions=["terms_approved", "not_applicable"], required_permission="approve_terms",
                       evidence={"covenant_test_id": str(test.id), "error": test.error}, actor=actor,
                       dedupe_key=f"covenant.cannot_test:{facility.id}:{period_end}")
        return [test]

    provider = fact_provider(db, borrower.id)
    fye = borrower.fiscal_year_end_month
    tests: list[CovenantTest] = []
    for covenant in version.terms.covenants:
        if not calc_cov.is_test_date(covenant, period_end, fye):
            continue
        calc_id = uuid.uuid4()
        result = calc_cov.test_covenant(
            covenant, period_end, provider, version.terms.definitions, fye_month=fye,
            step_up_from=facility.origination_date or version_row.effective_from, calc_id=str(calc_id))
        calc = _calc_run(db, borrower, version_row, covenant, period_end, result, calc_id, actor)
        unit = result.unit or covenant.test.unit
        value_fact = None
        if result.value is not None:
            value_fact = add_fact(db, borrower_id=borrower.id, facility_id=facility.id, key=f"cov.{covenant.id}.value",
                                  period_end=period_end, months=0, value=result.value, unit=unit, kind="calculated",
                                  calc_run_id=calc.id, actor=actor)
            # the threshold in force and the headroom are shown to people, so they are facts too
            add_fact(db, borrower_id=borrower.id, facility_id=facility.id, key=f"cov.{covenant.id}.threshold",
                     period_end=period_end, months=0, value=result.threshold, unit=unit, kind="calculated",
                     calc_run_id=calc.id, actor=actor)
            if result.headroom_pct is not None:
                add_fact(db, borrower_id=borrower.id, facility_id=facility.id, key=f"cov.{covenant.id}.headroom_pct",
                         period_end=period_end, months=0, value=result.headroom_pct, unit="pct", kind="calculated",
                         calc_run_id=calc.id, actor=actor)
        entry, reported_fact = _reported(db, borrower.id, covenant.id, period_end)
        outcome = calc_cov.determine_outcome(result, entry, tolerance.get(unit, Decimal("0")))

        for old in db.execute(select(CovenantTest).where(
                CovenantTest.facility_id == facility.id, CovenantTest.covenant_id == covenant.id,
                CovenantTest.period_end == period_end, CovenantTest.superseded.is_(False))).scalars():
            old.superseded = True
        test = CovenantTest(
            borrower_id=borrower.id, facility_id=facility.id, cycle_id=cycle.id if cycle else None,
            terms_version_id=version_row.id, covenant_id=covenant.id, covenant_name=covenant.name,
            period_end=period_end, calc_run_id=calc.id, value_fact_id=value_fact.id if value_fact else None,
            value=result.value, threshold=result.threshold, operator=result.operator, unit=unit,
            passed=result.passed, headroom=result.headroom, headroom_pct=result.headroom_pct,
            reported_value=entry.value if entry else None,
            reported_in_compliance=entry.in_compliance if entry else None,
            reported_fact_id=reported_fact.id if reported_fact else None, outcome=outcome.outcome,
            error="; ".join(e.message for e in outcome.errors) or None, origin=origin)
        db.add(test)
        db.flush()
        ledger.record(db, actor_type=actor[0], actor_id=actor[1], action="covenant.tested",
                      entity_type="covenant_test", entity_id=test.id,
                      payload={"covenant": covenant.id, "period_end": period_end, "value": result.value,
                               "threshold": result.threshold, "outcome": outcome.outcome, "calc_id": calc.id,
                               "terms_version": version_row.version,
                               "variances": [{"field": v.field, "computed": v.computed, "reported": v.reported}
                                             for v in outcome.variances]})
        tests.append(test)
        if raise_items:
            _raise_for(db, borrower, facility, cycle, test, outcome, actor)
    db.flush()
    return tests


def _raise_for(db, borrower, facility, cycle, test: CovenantTest, outcome, actor) -> WorkItem | None:
    common = dict(borrower_id=borrower.id, facility_id=facility.id, cycle_id=cycle.id if cycle else None,
                  stage="covenant_testing", actor=actor,
                  evidence={"covenant_test_id": str(test.id), "calc_run_id": str(test.calc_run_id),
                            "value_fact_id": str(test.value_fact_id) if test.value_fact_id else None,
                            "reported_fact_id": str(test.reported_fact_id) if test.reported_fact_id else None,
                            "errors": [e.to_dict() for e in outcome.errors]})
    key = f"{test.facility_id}:{test.covenant_id}:{test.period_end}"
    if test.outcome == "breach_reported_compliant":
        return raise_item(
            db, item_type="covenant.reported_mismatch", severity="critical",
            title=f"{borrower.name}: {test.covenant_name} fails but the certificate reports compliance",
            question="The calculated covenant fails while the borrower certified compliance. How should the bank respond?",
            allowed_decisions=BREACH_DECISIONS, required_permission="decide_breach",
            dedupe_key=f"covenant.reported_mismatch:{key}", **common)
    if test.outcome == "breach":
        return raise_item(
            db, item_type="covenant.breach", severity="high",
            title=f"{borrower.name}: {test.covenant_name} is in breach",
            question="This covenant fails its test for the period. How should the bank respond?",
            allowed_decisions=BREACH_DECISIONS, required_permission="decide_breach",
            dedupe_key=f"covenant.breach:{key}", **common)
    if test.outcome == "cannot_test":
        missing = ", ".join(sorted({e.key for e in outcome.errors if e.key})) or "an input"
        return raise_item(
            db, item_type="covenant.cannot_test", severity="medium",
            title=f"{borrower.name}: {test.covenant_name} cannot be tested",
            question=f"The test needs {missing}, which is not available for this period. Provide it, or record why the test does not apply?",
            allowed_decisions=["input_provided", "not_applicable"], required_permission="confirm_spread",
            dedupe_key=f"covenant.cannot_test:{key}", **common)
    if test.outcome == "compliant_variance" and test.reported_in_compliance is False:
        # the borrower itself reports a breach and the bank's calculation passes: one of the two
        # is wrong, and a pass computed from a misread figure is the dangerous one
        return raise_item(
            db, item_type="covenant.reported_breach_unconfirmed", severity="high",
            title=f"{borrower.name}: the certificate reports {test.covenant_name} as not in compliance, "
                  "but the calculation passes",
            question="The borrower certified non-compliance while the bank's calculation passes. Which is in "
                     "error, the figures the bank spread or the certificate?",
            allowed_decisions=["spread_in_error", "certificate_in_error", "escalate_to_committee"],
            required_permission="decide_breach", dedupe_key=f"covenant.reported_breach_unconfirmed:{key}", **common)
    return None  # compliant, or a variance that passes either way: recorded on the ledger only
