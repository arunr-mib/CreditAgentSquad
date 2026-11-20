"""Early warning rules `signals-1` (spec section 8), as data.

Each rule is a row in `RULES`; `evaluate_signals` applies them to a series of period metrics
and system-of-record rows. A fired signal carries its rule id, severity and a machine-readable
basis (the values compared and their period keys) and no prose. A rule that cannot be
evaluated because a value is unmeasured is listed in `not_evaluated`; it never fires on a
missing value and never treats one as zero.

Each rule computes one figure (a change, a ratio, a day count), rounds it once at the end,
and fires when that rounded figure is strictly beyond the trigger, so the figure in the basis
is exactly the figure that was tested. Metric values in the series are therefore UNROUNDED
(`compute_signal_inputs` returns them that way): a change of 1.0409 in leverage is 1.04, not
the 1.05 that differencing two rounded ratios would give.

Changes are measured against the same period a year earlier (`compare: "yoy"`), the one
comparison basis the spec states; change it per rule in the table. "Two periods running" uses
the two periods before the current one in the series. Percentages and headroom are fractions
(0.10 = 10 percent).

`availability` is borrowing base availability. For a line without a borrowing base leave it
None: availability below 10 percent of commitment is then the same fact as usage above 90
percent, and `line_usage_high` already reports it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from .covenants import compute_rml
from .decimal_utils import CALC_CONTEXT, ZERO, is_decimal, round_half_up
from .errors import CalcError
from .expr import Trace, evaluate, shift_period_end
from .metrics import METRICS, add, metric_definitions, named, point, t3m, ttm
from .periods import FactValue, Provider, same_period_prior_year

SIGNALS_VERSION = "signals-1"


@dataclass(frozen=True)
class SignalRule:
    id: str
    severity: str  # low | medium | high
    kind: str
    params: Mapping[str, Any] = field(default_factory=dict)
    templates: frozenset[str] = frozenset({"ci-1"})  # the spreading templates the rule applies to


CI = frozenset({"ci-1"})
VC = frozenset({"vc-1"})
BOTH = CI | VC

RULES: tuple[SignalRule, ...] = (
    SignalRule("covenant_headroom_low", "medium", "headroom_below", {"threshold": Decimal("0.10")}, BOTH),
    SignalRule("covenant_headroom_falling", "low", "headroom_falling", {"periods": 2}, BOTH),
    SignalRule("revenue_ttm_decline", "medium", "pct_decrease",
               {"metric": "revenue_ttm", "compare": "yoy", "threshold": Decimal("0.10"), "dp": 4}),
    SignalRule("ebitda_margin_decline", "medium", "abs_decrease",
               {"metric": "ebitda_margin", "compare": "yoy", "threshold": Decimal("0.03"), "dp": 4}),
    SignalRule("dso_increase", "medium", "abs_increase",
               {"metric": "dso", "compare": "yoy", "threshold": Decimal("10"), "dp": 1}),
    SignalRule("dpo_increase", "medium", "abs_increase",
               {"metric": "dpo", "compare": "yoy", "threshold": Decimal("15"), "dp": 1}),
    SignalRule("leverage_increase", "medium", "abs_increase",
               {"metric": "leverage", "compare": "yoy", "threshold": Decimal("0.5"), "dp": 2}),
    SignalRule("net_loss", "high", "below", {"metric": "net_income_ttm", "threshold": Decimal("0")}),
    SignalRule("cash_decline", "medium", "pct_decrease",
               {"metric": "cash", "compare": "yoy", "threshold": Decimal("0.30"), "dp": 4}),
    SignalRule("line_usage_high", "medium", "usage_above", {"threshold": Decimal("0.90"), "dp": 4}, BOTH),
    SignalRule("availability_low", "medium", "availability_below", {"threshold": Decimal("0.10"), "dp": 4}, BOTH),
    SignalRule("reporting_late", "high", "reporting_late", {"days": 15}, BOTH),
    SignalRule("payment_past_due", "high", "past_due", {"days": 10}, BOTH),
    SignalRule("auditor_opinion", "high", "auditor_opinion", {"opinions": ("qualified", "going_concern")}, BOTH),
    # startup rules (vc-1): monthly series of rml, avg_net_burn and plan_ratio
    SignalRule("runway_below_watch", "high", "rml_below", {"watch": Decimal("12"), "high_below": Decimal("9")}, VC),
    # runway shrinking faster than the calendar: more than `min_fall` months lost in each of `periods` monthly steps
    SignalRule("runway_falling", "medium", "rml_falling", {"periods": 3, "min_fall": Decimal("1.0")}, VC),
    SignalRule("burn_rising", "medium", "pct_increase",
               {"metric": "avg_net_burn", "threshold": Decimal("0.20"), "compare_months": 3, "dp": 4}, VC),
    SignalRule("revenue_below_plan", "medium", "plan_ratio_below", {"threshold": Decimal("1.00"), "dp": 4}, VC),
)


def _check_values(values: Mapping[str, Any], what: str) -> None:
    for name, value in values.items():
        number = value.value if isinstance(value, FactValue) else value
        if number is not None and not is_decimal(number):
            raise TypeError(f"{what} {name!r} must be a Decimal, a FactValue or None, got {type(number).__name__}")


@dataclass(frozen=True)
class PeriodMetrics:
    """One period's measured values. `metrics` uses the names in `SIGNAL_INPUTS` plus
    `availability`; `headroom` maps covenant id to headroom_pct. None means unmeasured."""

    period_end: date
    months: int
    metrics: Mapping[str, Decimal | FactValue | None]
    headroom: Mapping[str, Decimal | FactValue | None] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _check_values(self.metrics, "metric")
        _check_values(self.headroom, "headroom")


@dataclass(frozen=True)
class SystemRow:
    """A system-of-record row for the facility."""

    date: date
    revolver_outstanding: Decimal
    commitment: Decimal
    past_due_days: int

    def __post_init__(self) -> None:
        if not is_decimal(self.revolver_outstanding) or not is_decimal(self.commitment):
            raise TypeError("system row amounts must be Decimals")
        if isinstance(self.past_due_days, bool) or not isinstance(self.past_due_days, int):
            raise TypeError("past_due_days must be an int")


@dataclass(frozen=True)
class ReportingItem:
    requirement_id: str
    period_end: date
    due_date: date
    received_date: date | None  # None: not received yet


@dataclass(frozen=True)
class AuditorOpinion:
    """An opinion the agent detected and quoted; the fact and page are carried, not the words."""

    period_end: date
    opinion: str  # e.g. unqualified | qualified | going_concern
    fact_id: str | None = None
    document_id: str | None = None
    page: int | None = None


@dataclass(frozen=True)
class Signal:
    rule_id: str
    severity: str
    period_end: date
    subject: str | None  # covenant id or reporting requirement id, where the rule is per item
    basis: dict[str, Any]


@dataclass(frozen=True)
class NotEvaluated:
    rule_id: str
    subject: str | None
    reason: str  # missing_value | no_comparison_period | non_positive_base | no_system_row | no_as_of_date
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class SignalEvaluation:
    signals: list[Signal] = field(default_factory=list)
    not_evaluated: list[NotEvaluated] = field(default_factory=list)


def _point(entry: PeriodMetrics, value: Decimal | FactValue | None) -> dict[str, Any] | None:
    if value is None:
        return None
    fact = value if isinstance(value, FactValue) else FactValue(value)
    return {"period_end": entry.period_end, "months": entry.months, "value": fact.value, "fact_id": fact.fact_id}


def _flag(value: Decimal | FactValue | None) -> bool:
    number = value.value if isinstance(value, FactValue) else value
    return number is not None and number != ZERO


class _Evaluation:
    def __init__(self, period_end: date, series: Sequence[PeriodMetrics], system_rows: Sequence[SystemRow],
                 reporting: Sequence[ReportingItem], opinions: Sequence[AuditorOpinion], as_of: date | None) -> None:
        ordered = sorted(series, key=lambda e: e.period_end)
        self.by_end = {e.period_end: e for e in ordered}
        if len(self.by_end) != len(ordered):
            raise ValueError("the series has more than one entry for a period end")
        if period_end not in self.by_end:
            raise ValueError(f"the series has no entry for {period_end.isoformat()}")
        self.period_end = period_end
        self.current = self.by_end[period_end]
        self.before = [e for e in ordered if e.period_end < period_end]
        rows = [r for r in system_rows if r.date <= period_end]
        self.row = max(rows, key=lambda r: r.date) if rows else None
        self.reporting, self.opinions, self.as_of = reporting, opinions, as_of
        self.out = SignalEvaluation()

    def fire(self, rule: SignalRule, basis: dict[str, Any], subject: str | None = None,
             severity: str | None = None) -> None:
        self.out.signals.append(Signal(rule.id, severity or rule.severity, self.period_end, subject, basis))

    def skip(self, rule: SignalRule, reason: str, subject: str | None = None, **detail: Any) -> None:
        self.out.not_evaluated.append(NotEvaluated(rule.id, subject, reason, detail))

    # -- covenant headroom

    def headroom_below(self, rule: SignalRule) -> None:
        for covenant_id, value in self.current.headroom.items():
            current = _point(self.current, value)
            if current is None:
                self.skip(rule, "missing_value", covenant_id, metric="headroom_pct")
            elif current["value"] < rule.params["threshold"]:
                self.fire(rule, {"metric": "headroom_pct", "covenant_id": covenant_id, "current": current,
                                 "threshold": rule.params["threshold"]}, covenant_id)

    def headroom_falling(self, rule: SignalRule) -> None:
        count = rule.params["periods"]
        for covenant_id in self.current.headroom:
            window = self.before[-count:] + [self.current]
            if len(window) < count + 1:
                self.skip(rule, "no_comparison_period", covenant_id)
                continue
            points = [_point(e, e.headroom.get(covenant_id)) for e in window]
            if any(p is None for p in points):
                self.skip(rule, "missing_value", covenant_id, metric="headroom_pct")
            elif all(later["value"] < earlier["value"] for earlier, later in zip(points, points[1:], strict=False)):
                self.fire(rule, {"metric": "headroom_pct", "covenant_id": covenant_id, "values": points}, covenant_id)

    # -- metric comparisons

    def _pair(self, rule: SignalRule) -> tuple[dict[str, Any], dict[str, Any]] | None:
        metric = rule.params["metric"]
        current = _point(self.current, self.current.metrics.get(metric))
        if current is None:
            self.skip(rule, "missing_value", metric=metric, period_end=self.period_end)
            return None
        if rule.params["compare"] == "yoy":
            prior_entry = self.by_end.get(same_period_prior_year(self.period_end))
        else:  # prior_period
            prior_entry = self.before[-1] if self.before else None
        if prior_entry is None:
            self.skip(rule, "no_comparison_period", metric=metric, compare=rule.params["compare"])
            return None
        prior = _point(prior_entry, prior_entry.metrics.get(metric))
        if prior is None:
            self.skip(rule, "missing_value", metric=metric, period_end=prior_entry.period_end)
            return None
        return current, prior

    def _compared(self, rule: SignalRule, current: dict, prior: dict, change: Decimal) -> dict[str, Any]:
        return {"metric": rule.params["metric"], "compare": rule.params["compare"], "current": current,
                "prior": prior, "change": change, "threshold": rule.params["threshold"]}

    def pct_decrease(self, rule: SignalRule) -> None:
        pair = self._pair(rule)
        if pair is None:
            return
        current, prior = pair
        if prior["value"] <= ZERO:
            self.skip(rule, "non_positive_base", metric=rule.params["metric"], period_end=prior["period_end"])
            return
        change = CALC_CONTEXT.divide(CALC_CONTEXT.subtract(current["value"], prior["value"]), prior["value"])
        change = round_half_up(change, rule.params["dp"])
        if change < -rule.params["threshold"]:
            self.fire(rule, self._compared(rule, current, prior, change))

    def _abs_change(self, rule: SignalRule) -> tuple[dict[str, Any], dict[str, Any], Decimal] | None:
        pair = self._pair(rule)
        if pair is None:
            return None
        change = round_half_up(CALC_CONTEXT.subtract(pair[0]["value"], pair[1]["value"]), rule.params["dp"])
        return pair[0], pair[1], change

    def abs_decrease(self, rule: SignalRule) -> None:
        found = self._abs_change(rule)
        if found is not None and found[2] < -rule.params["threshold"]:
            self.fire(rule, self._compared(rule, *found))

    def abs_increase(self, rule: SignalRule) -> None:
        found = self._abs_change(rule)
        if found is not None and found[2] > rule.params["threshold"]:
            self.fire(rule, self._compared(rule, *found))

    def below(self, rule: SignalRule) -> None:
        metric = rule.params["metric"]
        current = _point(self.current, self.current.metrics.get(metric))
        if current is None:
            self.skip(rule, "missing_value", metric=metric, period_end=self.period_end)
        elif current["value"] < rule.params["threshold"]:
            self.fire(rule, {"metric": metric, "current": current, "threshold": rule.params["threshold"]})

    # -- startup (monthly) rules

    def _rml(self, rule: SignalRule, entry: PeriodMetrics) -> dict[str, Any] | None | bool:
        """The entry's RML point; None if unmeasured (skipped); False if not meaningful (skipped)."""
        if _flag(entry.metrics.get("rml_not_meaningful")):
            self.skip(rule, "not_meaningful", metric="rml", period_end=entry.period_end)
            return False
        point_ = _point(entry, entry.metrics.get("rml"))
        if point_ is None:
            self.skip(rule, "missing_value", metric="rml", period_end=entry.period_end)
        return point_

    def rml_below(self, rule: SignalRule) -> None:
        current = self._rml(rule, self.current)
        if not current:  # unmeasured, or cash-flow positive: never a runway signal
            return
        value = current["value"]
        if value < rule.params["watch"]:
            severity = "high" if value < rule.params["high_below"] else "medium"
            self.fire(rule, {"metric": "rml", "current": current, "watch": rule.params["watch"],
                             "high_below": rule.params["high_below"]}, severity=severity)

    def rml_falling(self, rule: SignalRule) -> None:
        count = rule.params["periods"]
        window = self.before[-count:] + [self.current]
        if len(window) < count + 1:
            self.skip(rule, "no_comparison_period", metric="rml")
            return
        points = [self._rml(rule, e) for e in window]
        if not all(points):
            return
        floor = rule.params["min_fall"]
        if all(earlier["value"] - later["value"] > floor for earlier, later in zip(points, points[1:], strict=False)):
            self.fire(rule, {"metric": "rml", "values": points, "min_fall": floor})

    def pct_increase(self, rule: SignalRule) -> None:
        metric = rule.params["metric"]
        current = _point(self.current, self.current.metrics.get(metric))
        if current is None:
            self.skip(rule, "missing_value", metric=metric, period_end=self.period_end)
            return
        prior_end = shift_period_end(self.period_end, -rule.params["compare_months"])
        prior_entry = self.by_end.get(prior_end)
        if prior_entry is None:
            self.skip(rule, "no_comparison_period", metric=metric, compare_months=rule.params["compare_months"])
            return
        prior = _point(prior_entry, prior_entry.metrics.get(metric))
        if prior is None:
            self.skip(rule, "missing_value", metric=metric, period_end=prior_end)
            return
        if prior["value"] <= ZERO:
            self.skip(rule, "non_positive_base", metric=metric, period_end=prior_end)
            return
        change = round_half_up(CALC_CONTEXT.divide(CALC_CONTEXT.subtract(current["value"], prior["value"]),
                                                   prior["value"]), rule.params["dp"])
        if change > rule.params["threshold"]:
            self.fire(rule, {"metric": metric, "compare_months": rule.params["compare_months"], "current": current,
                             "prior": prior, "change": change, "threshold": rule.params["threshold"]})

    def plan_ratio_below(self, rule: SignalRule) -> None:
        current = _point(self.current, self.current.metrics.get("plan_ratio"))
        if current is None:  # no plan (or a plan month missing): absent data is not a signal
            self.skip(rule, "missing_value", metric="plan_ratio", period_end=self.period_end)
            return
        ratio = round_half_up(current["value"], rule.params["dp"])
        if ratio < rule.params["threshold"]:
            self.fire(rule, {"metric": "plan_ratio", "current": current, "ratio": ratio,
                             "threshold": rule.params["threshold"]})

    # -- system of record

    def _commitment(self, rule: SignalRule) -> SystemRow | None:
        if self.row is None:
            self.skip(rule, "no_system_row")
            return None
        if self.row.commitment <= ZERO:
            self.skip(rule, "non_positive_base", date=self.row.date)
            return None
        return self.row

    def usage_above(self, rule: SignalRule) -> None:
        row = self._commitment(rule)
        if row is None:
            return
        usage = round_half_up(CALC_CONTEXT.divide(row.revolver_outstanding, row.commitment), rule.params["dp"])
        if usage > rule.params["threshold"]:
            self.fire(rule, {"date": row.date, "revolver_outstanding": row.revolver_outstanding,
                             "commitment": row.commitment, "usage": usage, "threshold": rule.params["threshold"]})

    def availability_below(self, rule: SignalRule) -> None:
        row = self._commitment(rule)
        if row is None:
            return
        availability = _point(self.current, self.current.metrics.get("availability"))
        if availability is None:
            self.skip(rule, "missing_value", metric="availability", period_end=self.period_end)
            return
        ratio = round_half_up(CALC_CONTEXT.divide(availability["value"], row.commitment), rule.params["dp"])
        if ratio < rule.params["threshold"]:
            self.fire(rule, {"availability": availability, "date": row.date, "commitment": row.commitment,
                             "ratio": ratio, "threshold": rule.params["threshold"]})

    def past_due(self, rule: SignalRule) -> None:
        if self.row is None:
            self.skip(rule, "no_system_row")
        elif self.row.past_due_days > rule.params["days"]:
            self.fire(rule, {"date": self.row.date, "past_due_days": self.row.past_due_days,
                             "threshold": rule.params["days"]})

    # -- reporting and opinion

    def reporting_late(self, rule: SignalRule) -> None:
        for item in self.reporting:
            reference = item.received_date or self.as_of
            if reference is None:
                self.skip(rule, "no_as_of_date", item.requirement_id, period_end=item.period_end)
                continue
            days_late = (reference - item.due_date).days
            if days_late > rule.params["days"]:
                self.fire(rule, {"requirement_id": item.requirement_id, "period_end": item.period_end,
                                 "due_date": item.due_date, "received_date": item.received_date,
                                 "as_of": None if item.received_date else self.as_of,
                                 "days_late": days_late, "threshold": rule.params["days"]}, item.requirement_id)

    def auditor_opinion(self, rule: SignalRule) -> None:
        for item in self.opinions:
            if item.opinion in rule.params["opinions"]:
                self.fire(rule, {"opinion": item.opinion, "period_end": item.period_end, "fact_id": item.fact_id,
                                 "document_id": item.document_id, "page": item.page})


def evaluate_signals(
    period_end: date,
    series: Sequence[PeriodMetrics],
    *,
    system_rows: Sequence[SystemRow] = (),
    reporting: Sequence[ReportingItem] = (),
    opinions: Sequence[AuditorOpinion] = (),
    as_of: date | None = None,
    rules: Sequence[SignalRule] = RULES,
    template_id: str = "ci-1",
) -> SignalEvaluation:
    """Apply the rule table for the period ending `period_end`.

    `series` must contain that period and whatever history exists (any order). `system_rows`
    are the facility's rows; the latest on or before `period_end` is used. `reporting` and
    `opinions` are the items to judge. `as_of` is the date lateness of an unreceived document
    is measured to; without it such items are not evaluated. Only rules whose `templates` include
    `template_id` run. Signals come back in rule order.
    """
    run = _Evaluation(period_end, series, system_rows, reporting, opinions, as_of)
    for rule in rules:
        if template_id in rule.templates:
            getattr(run, rule.kind)(rule)
    return run.out


# ---- building the series -------------------------------------------------------------------

# Signal input name -> expression. `availability` is not here: it is the borrowing base result.
SIGNAL_INPUTS: dict[str, Mapping[str, Any]] = {
    "revenue_ttm": ttm("is.revenue"),
    "net_income_ttm": ttm("is.net_income"),
    "cash": point("bs.cash"),
    "ebitda_margin": METRICS["ebitda_margin"].expr,
    "dso": METRICS["dso"].expr,
    "dpo": METRICS["dpo"].expr,
    "leverage": METRICS["leverage"].expr,
}


@dataclass
class SignalInputs:
    values: dict[str, Decimal | None]  # UNROUNDED; None means unmeasured
    errors: dict[str, list[CalcError]]  # only the inputs that could not be measured
    traces: dict[str, Trace]  # the facts behind each input
    history: dict[date, SignalInputs] = field(default_factory=dict)  # venture: the months before, oldest first


def _venture_inputs(period_end: date, provider: Provider, fye_month: int,
                    plan: Mapping[date, Decimal] | None) -> SignalInputs:
    out = SignalInputs({}, {}, {})
    definitions = metric_definitions()
    rml = compute_rml(period_end, provider, fye_month)
    out.values["rml"] = rml.value
    out.values["rml_not_meaningful"] = None if rml.errors else (Decimal(1) if rml.not_meaningful else Decimal(0))
    out.traces["rml"] = rml.trace
    if rml.errors:
        out.errors["rml"] = rml.errors
    burn = evaluate(named("avg_net_burn"), period_end, provider, definitions=definitions, fye_month=fye_month)
    out.values["avg_net_burn"], out.traces["avg_net_burn"] = burn.value, burn.trace
    if burn.errors:
        out.errors["avg_net_burn"] = burn.errors
    out.values["plan_ratio"] = None
    months = [shift_period_end(period_end, -2), shift_period_end(period_end, -1), period_end]
    if plan is not None and all(m in plan for m in months):
        planned = sum((plan[m] for m in months), ZERO)
        revenue = evaluate(add(t3m("is.subscription_revenue"), t3m("is.services_revenue")), period_end, provider,
                           definitions=definitions, fye_month=fye_month)
        out.traces["plan_ratio"] = revenue.trace
        if revenue.errors:
            out.errors["plan_ratio"] = revenue.errors
        elif planned > ZERO:
            out.values["plan_ratio"] = CALC_CONTEXT.divide(revenue.value, planned)
    return out


def compute_signal_inputs(
    period_end: date,
    provider: Provider,
    *,
    fye_month: int = 12,
    template_id: str = "ci-1",
    history_months: int | None = None,
    plan: Mapping[date, Decimal] | None = None,
) -> SignalInputs:
    """Measure the metric inputs of the signal rules for one period (for `PeriodMetrics.metrics`).

    Values are unrounded on purpose: the rules round once, at the end of their own formula.
    For `vc-1` the inputs are `rml`, `rml_not_meaningful` (1 when cash-flow positive), `avg_net_burn`
    and `plan_ratio` (last three months' revenue over the plan for those months; None with no plan
    or a plan month missing, which is absent data and never a miss), and `history` holds the same
    for each of the `history_months` (default 6) months before `period_end`. `plan` maps month end
    to planned revenue. For `ci-1` the quarterly metrics are returned and `history_months` and
    `plan` are ignored.
    """
    if template_id == "vc-1":
        out = _venture_inputs(period_end, provider, fye_month, plan)
        count = 6 if history_months is None else history_months
        for back in range(count, 0, -1):
            month = shift_period_end(period_end, -back)
            out.history[month] = _venture_inputs(month, provider, fye_month, plan)
        return out
    out = SignalInputs({}, {}, {})
    definitions = metric_definitions()
    for name, expression in SIGNAL_INPUTS.items():
        result = evaluate(expression, period_end, provider, definitions=definitions, fye_month=fye_month)
        out.values[name] = result.value
        out.traces[name] = result.trace
        if result.errors:
            out.errors[name] = result.errors
    return out


def reporting_due_date(period_end: date, due_days_after_period_end: int) -> date:
    """The date a required document is due."""
    return period_end + timedelta(days=due_days_after_period_end)
