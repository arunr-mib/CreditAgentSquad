"""Metric library `metrics-1` (spec section 5): expression trees with units and rounding.

Flow lines are trailing twelve months, balance sheet lines are point in time. Ratios round
to 2 dp, dollars to 0, days to 1, and percentages are fractions (0.1282 = 12.82%) to 4 dp.

Where the spec names a metric without a formula, the formula chosen here is:
  quick_ratio = (cash + accounts receivable) / total current liabilities
  dscr        = ebitda / (interest expense + scheduled principal)
  fccr        = (ebitda - unfinanced capex - cash taxes - distributions)
                / (cash interest + scheduled principal)
  debt_to_tnw = total liabilities / tangible net worth (as the covenant archetype)
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

from . import errors as E
from .errors import CalcError
from .expr import EvalResult, Trace, evaluate
from .periods import Provider

METRICS_VERSION = "metrics-1"

USD = {"dp": 0, "mode": "half_up"}
RATIO = {"dp": 2, "mode": "half_up"}
DAYS = {"dp": 1, "mode": "half_up"}
PCT = {"dp": 4, "mode": "half_up"}
_ROUNDING = {"usd": USD, "ratio": RATIO, "days": DAYS, "pct": PCT}


@dataclass(frozen=True)
class MetricDef:
    name: str
    expr: Mapping[str, Any]
    unit: str  # usd | ratio | days | pct

    @property
    def rounding(self) -> dict[str, Any]:
        return dict(_ROUNDING[self.unit])


def line(key: str, period: str) -> dict[str, Any]:
    return {"op": "line", "key": key, "period": period}


def ttm(key: str) -> dict[str, Any]:
    return line(key, "ttm")


def t3m(key: str) -> dict[str, Any]:
    return line(key, "t3m")


def point(key: str) -> dict[str, Any]:
    return line(key, "point")


def named(name: str) -> dict[str, Any]:
    return {"op": "named", "name": name}


def const(value: str) -> dict[str, Any]:
    return {"op": "const", "value": value}


def add(*args: Any) -> dict[str, Any]:
    return {"op": "add", "args": list(args)}


def sub(*args: Any) -> dict[str, Any]:
    return {"op": "sub", "args": list(args)}


def div(num: Any, den: Any) -> dict[str, Any]:
    return {"op": "div", "num": num, "den": den}


def _days(balance: str, flow: str) -> dict[str, Any]:
    return div({"op": "mul", "args": [point(balance), const("365")]}, ttm(flow))


UNFINANCED_CAPEX = sub(ttm("cf.capex"), ttm("sup.financed_capex"))

_LIBRARY: tuple[MetricDef, ...] = (
    MetricDef("ebitda", add(ttm("is.net_income"), ttm("is.interest_expense"), ttm("is.income_tax_expense"),
                            ttm("is.depreciation_amortization")), "usd"),
    MetricDef("total_debt", add(point("bs.revolver"), point("bs.cpltd"), point("bs.long_term_debt"),
                                point("bs.subordinated_debt")), "usd"),
    MetricDef("senior_debt", sub(named("total_debt"), point("bs.subordinated_debt")), "usd"),
    MetricDef("tangible_net_worth", sub(point("bs.total_equity"), point("bs.intangibles")), "usd"),
    MetricDef("working_capital", sub(point("bs.total_current_assets"), point("bs.total_current_liabilities")), "usd"),
    MetricDef("current_ratio", div(point("bs.total_current_assets"), point("bs.total_current_liabilities")), "ratio"),
    MetricDef("quick_ratio", div(add(point("bs.cash"), point("bs.accounts_receivable")),
                                 point("bs.total_current_liabilities")), "ratio"),
    MetricDef("leverage", div(named("total_debt"), named("ebitda")), "ratio"),
    MetricDef("senior_leverage", div(named("senior_debt"), named("ebitda")), "ratio"),
    MetricDef("interest_coverage", div(named("ebitda"), ttm("is.interest_expense")), "ratio"),
    MetricDef("dscr", div(named("ebitda"), add(ttm("is.interest_expense"), ttm("sup.scheduled_principal"))), "ratio"),
    MetricDef("fccr", div(sub(named("ebitda"), UNFINANCED_CAPEX, ttm("sup.cash_taxes_paid"), ttm("cf.distributions")),
                          add(ttm("sup.cash_interest_paid"), ttm("sup.scheduled_principal"))), "ratio"),
    MetricDef("debt_to_tnw", div(point("bs.total_liabilities"), named("tangible_net_worth")), "ratio"),
    MetricDef("gross_margin", div(ttm("is.gross_profit"), ttm("is.revenue")), "pct"),
    MetricDef("ebitda_margin", div(named("ebitda"), ttm("is.revenue")), "pct"),
    MetricDef("net_margin", div(ttm("is.net_income"), ttm("is.revenue")), "pct"),
    MetricDef("dso", _days("bs.accounts_receivable", "is.revenue"), "days"),
    MetricDef("dio", _days("bs.inventory", "is.cogs"), "days"),
    MetricDef("dpo", _days("bs.accounts_payable", "is.cogs"), "days"),
    MetricDef("revenue_growth_yoy", sub(div(ttm("is.revenue"), {"op": "shift", "months": -12, "arg": ttm("is.revenue")}),
                                        const("1")), "pct"),
    MetricDef("liquidity", add(point("bs.cash"), point("bb.availability")), "usd"),
)

METRICS: dict[str, MetricDef] = {m.name: m for m in _LIBRARY}

# Names for venture covenants (runway, unrestricted cash); referenced by `named`, not part of the metrics-1 spec set.
_VENTURE: dict[str, Mapping[str, Any]] = {
    "unrestricted_cash": point("bs.cash_unrestricted"),
    "net_burn_t3m": sub(add(t3m("cf.vc_capex"), t3m("cf.capitalised_software_spend")),
                        t3m("cf.vc_operating_cash_flow")),
    "vc_ebitda": add(ttm("is.vc_operating_loss"), ttm("is.vc_depreciation_amortization")),
    "avg_net_burn": div(named("net_burn_t3m"), const("3")),
}


def metric_definitions() -> dict[str, Mapping[str, Any]]:
    """Name -> expression tree, for `named` references."""
    return {**{name: metric.expr for name, metric in METRICS.items()}, **_VENTURE}


def compute_metric(
    name: str,
    period_end: date,
    provider: Provider,
    *,
    fye_month: int = 12,
    calc_id: str | None = None,
) -> EvalResult:
    """Evaluate one library metric. An unmeasurable metric has value None and errors, never zero."""
    metric = METRICS.get(name)
    if metric is None:
        error = CalcError(E.UNKNOWN_DEFINITION, f"unknown metric {name!r} in {METRICS_VERSION}", detail={"name": name})
        return EvalResult(None, None, Trace(), [error], calc_id)
    return evaluate(metric.expr, period_end, provider, definitions=metric_definitions(),
                    rounding=metric.rounding, fye_month=fye_month, calc_id=calc_id)


def compute_metrics(
    names: Iterable[str] | None,
    period_end: date,
    provider: Provider,
    *,
    fye_month: int = 12,
) -> dict[str, EvalResult]:
    """Evaluate several metrics (all of them when `names` is None)."""
    chosen = list(METRICS) if names is None else list(names)
    return {name: compute_metric(name, period_end, provider, fye_month=fye_month) for name in chosen}
