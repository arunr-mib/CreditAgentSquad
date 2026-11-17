"""Compute library metrics from stored facts and keep each result as a calculated fact, so a
metric shown to a person or referenced in commentary has a source like any other figure."""
import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.calc import metrics as lib
from app.calc.expr import evaluate
from app.core import ledger
from app.domain.covenant_service import fact_provider
from app.domain.credit import Borrower
from app.domain.facts import CalcRun, Fact
from app.domain.facts_service import add_fact, current_fact

# metrics outside the library that reviews need
EXTRA = {"revenue_ttm": (lib.ttm("is.revenue"), "usd"), "net_income_ttm": (lib.ttm("is.net_income"), "usd"),
         "cash": (lib.point("bs.cash"), "usd")}
REVIEW_METRICS = ("revenue_ttm", "ebitda", "ebitda_margin", "net_income_ttm", "leverage", "interest_coverage",
                  "current_ratio", "dso", "dpo", "cash", "total_debt", "revenue_growth_yoy")
_USD = {"dp": 0, "mode": "half_up"}


def store_metric(db: Session, borrower: Borrower, name: str, period_end: date,
                 actor: tuple[str, str] = ("system", "metrics")) -> Fact | None:
    """The metric as a fact for this period, computed and stored on first use. None when it
    cannot be measured: an unmeasured metric is never stored as zero."""
    key = f"metric.{name}"
    existing = current_fact(db, borrower.id, key, period_end, 0)
    if existing is not None:
        return existing
    provider = fact_provider(db, borrower.id)
    calc_id = uuid.uuid4()
    if name in EXTRA:
        expression, unit = EXTRA[name]
        result = evaluate(expression, period_end, provider, definitions=lib.metric_definitions(), rounding=_USD,
                          fye_month=borrower.fiscal_year_end_month, calc_id=str(calc_id))
    elif name in lib.METRICS:
        unit = lib.METRICS[name].unit
        result = lib.compute_metric(name, period_end, provider, fye_month=borrower.fiscal_year_end_month,
                                    calc_id=str(calc_id))
    else:
        raise KeyError(name)
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
                    unit=unit, kind="calculated", calc_run_id=calc.id, actor=actor)


def store_metrics(db: Session, borrower: Borrower, period_end: date, names=REVIEW_METRICS) -> dict[str, Fact]:
    out = {}
    for name in names:
        fact = store_metric(db, borrower, name, period_end)
        if fact is not None:
            out[name] = fact
    return out
