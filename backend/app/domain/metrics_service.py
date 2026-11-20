"""Compute library metrics from stored facts and keep each result as a calculated fact, so a
metric shown to a person or referenced in commentary has a source like any other figure."""
import uuid
from collections.abc import Mapping
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.calc import metrics as lib
from app.calc.expr import evaluate
from app.calc.metrics import add, const, div, named, t3m
from app.core import ledger
from app.domain.covenant_service import fact_provider
from app.domain.credit import Borrower
from app.domain.facts import CalcRun, Fact
from app.domain.facts_service import add_fact, current_fact

# metrics outside the library that reviews need
EXTRA = {"revenue_ttm": (lib.ttm("is.revenue"), "usd"), "net_income_ttm": (lib.ttm("is.net_income"), "usd"),
         "cash": (lib.point("bs.cash"), "usd"),
         # venture metrics (vc-1): runway in months is not money, so it is a plain count at six places
         "avg_net_burn": (named("avg_net_burn"), "usd"),
         "rml": (div(named("unrestricted_cash"), named("avg_net_burn")), "count")}
_PRECISE = {"rml": 6, "avg_net_burn": 2}  # decimal places, where whole dollars would lose the figure
REVIEW_METRICS = ("revenue_ttm", "ebitda", "ebitda_margin", "net_income_ttm", "leverage", "interest_coverage",
                  "current_ratio", "dso", "dpo", "cash", "total_debt", "revenue_growth_yoy")


def _store(db: Session, borrower: Borrower, key: str, period_end: date, expression, unit: str, dp: int,
           actor: tuple[str, str], terms_version_id: uuid.UUID | None = None,
           extra_inputs: list[dict] | None = None, extra_outputs: dict | None = None) -> Fact | None:
    """Evaluate the expression, record the calculation and keep the result as a calculated fact. A fact already
    stored is reused, unless it was computed under other terms than `terms_version_id` (an amended plan recomputes;
    the old fact stays, superseded by the newer one)."""
    existing = current_fact(db, borrower.id, key, period_end, 0)
    if existing is not None and (terms_version_id is None or (
            existing.calc_run_id is not None
            and getattr(db.get(CalcRun, existing.calc_run_id), "terms_version_id", None) == terms_version_id)):
        return existing
    calc_id = uuid.uuid4()
    result = evaluate(expression, period_end, fact_provider(db, borrower.id), definitions=lib.metric_definitions(),
                      rounding={"dp": dp, "mode": "half_up"}, fye_month=borrower.fiscal_year_end_month,
                      calc_id=str(calc_id))
    if result.errors or result.rounded is None:
        return None
    calc = CalcRun(
        id=calc_id, borrower_id=borrower.id, formula_key=key, formula_version=lib.METRICS_VERSION,
        period_end=period_end, engine_version=result.engine_version,
        terms_version_id=terms_version_id,
        inputs=[i.to_dict() for i in result.trace.inputs] + (extra_inputs or []),
        outputs=ledger._jsonable({"value": result.rounded, "raw_value": result.value, **(extra_outputs or {})}),
        created_by_type=actor[0], created_by_id=actor[1])
    db.add(calc)
    db.flush()
    return add_fact(db, borrower_id=borrower.id, key=key, period_end=period_end, months=0, value=result.rounded,
                    unit=unit, kind="calculated", calc_run_id=calc.id, actor=actor)


def store_plan_ratio(db: Session, borrower: Borrower, period_end: date, plan: Mapping[date, Decimal],
                     terms_version_id: uuid.UUID, actor: tuple[str, str] = ("system", "metrics")) -> Fact | None:
    """The last three months' revenue over the approved plan for those months, kept as a fact. `plan` is the three
    plan months from the approved terms version `terms_version_id` (the caller reads them from the governing
    terms); the calculation records that version, each plan month and the total, so the plan is traceable."""
    total = sum(plan.values(), Decimal(0))
    months = {m.isoformat(): str(amount) for m, amount in sorted(plan.items())}
    return _store(db, borrower, "metric.plan_ratio", period_end,
                  div(add(t3m("is.subscription_revenue"), t3m("is.services_revenue")), const(str(total))),
                  "ratio", 6, actor, terms_version_id=terms_version_id,
                  extra_inputs=[{"key": "terms.revenue_plan", "period_end": period_end.isoformat(),
                                 "plan_months": months, "value": str(total), "terms_version_id": str(terms_version_id)}],
                  extra_outputs={"plan_months": months, "plan_total": str(total)})


def store_metric(db: Session, borrower: Borrower, name: str, period_end: date,
                 actor: tuple[str, str] = ("system", "metrics")) -> Fact | None:
    """The metric as a fact for this period, computed and stored on first use. None when it
    cannot be measured: an unmeasured metric is never stored as zero."""
    key = f"metric.{name}"
    if name in EXTRA:
        expression, unit = EXTRA[name]
        return _store(db, borrower, key, period_end, expression, unit, _PRECISE.get(name, 0), actor)
    if name not in lib.METRICS:
        raise KeyError(name)
    existing = current_fact(db, borrower.id, key, period_end, 0)
    if existing is not None:
        return existing
    calc_id = uuid.uuid4()
    result = lib.compute_metric(name, period_end, fact_provider(db, borrower.id),
                                fye_month=borrower.fiscal_year_end_month, calc_id=str(calc_id))
    if result.errors or result.rounded is None:
        return None
    calc = CalcRun(
        id=calc_id, borrower_id=borrower.id, formula_key=key, formula_version=lib.METRICS_VERSION,
        period_end=period_end, engine_version=result.engine_version,
        inputs=[i.to_dict() for i in result.trace.inputs],
        outputs=ledger._jsonable({"value": result.rounded, "raw_value": result.value}),
        created_by_type=actor[0], created_by_id=actor[1])
    db.add(calc)
    db.flush()
    return add_fact(db, borrower_id=borrower.id, key=key, period_end=period_end, months=0, value=result.rounded,
                    unit=lib.METRICS[name].unit, kind="calculated", calc_run_id=calc.id, actor=actor)


def store_metrics(db: Session, borrower: Borrower, period_end: date, names=REVIEW_METRICS) -> dict[str, Fact]:
    out = {}
    for name in names:
        fact = store_metric(db, borrower, name, period_end)
        if fact is not None:
            out[name] = fact
    return out
