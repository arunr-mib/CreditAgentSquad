"""Covenant compilation, testing and outcomes (spec sections 7 and 8).

Each archetype's parameters compile to an expression tree; the tree is evaluated by
`expr.evaluate`, so every covenant result carries the trace of the facts it used.
The rounded value (per the covenant's rounding spec) is what is compared with the threshold.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import ValidationError

from . import errors as E
from .decimal_utils import CALC_CONTEXT, ZERO, is_decimal, round_half_up, to_decimal
from .errors import CalcError
from .expr import ENGINE_VERSION, Trace, evaluate, shift_period_end
from .metrics import UNFINANCED_CAPEX, add, const, div, metric_definitions, named, point, sub, t3m, ttm
from .periods import Provider, is_month_end, month_end, resolve_line, ytd_months
from .terms import Covenant, Definition, threshold_in_force

HEADROOM_PCT_DP = 4

_DEDUCTIONS: dict[str, dict[str, Any]] = {
    "unfinanced_capex": UNFINANCED_CAPEX,
    "cash_taxes": ttm("sup.cash_taxes_paid"),
    "distributions": ttm("cf.distributions"),
}
_DENOMINATORS: dict[str, dict[str, Any]] = {
    "cash_interest": ttm("sup.cash_interest_paid"),
    "interest_expense": ttm("is.interest_expense"),
    "scheduled_principal": ttm("sup.scheduled_principal"),
}


def build_definitions(definitions: Mapping[str, Definition | Mapping[str, Any]] | None) -> dict[str, Any]:
    """The names an expression may reference: the metric library plus `adjusted_<name>`
    for each terms definition (`adjusted_ebitda` = ebitda + its add-backs, each capped as specified).

    Raises pydantic's ValidationError if a definition mapping is invalid.
    """
    out: dict[str, Any] = dict(metric_definitions())
    for name, raw in (definitions or {}).items():
        definition = raw if isinstance(raw, Definition) else Definition.model_validate(raw)
        args: list[Any] = [named(definition.base)]
        for addback in definition.addbacks:
            node: dict[str, Any] = {"op": "addback", "name": addback.name, "source": ttm(addback.source_key), "cap": None}
            if addback.cap is not None:
                cap: dict[str, Any] = {"type": addback.cap.type, "value": str(addback.cap.value)}
                if addback.cap.type == "pct_of":
                    of = addback.cap.of
                    cap["of"] = named(of) if isinstance(of, str) else of
                node["cap"] = cap
            args.append(node)
        out[f"adjusted_{name}"] = {"op": "add", "args": args}
    return out


class PlanMissing(Exception):
    """The approved plan has no figure for one or more months the test needs."""

    def __init__(self, months: list[date]) -> None:
        super().__init__(months)
        self.months = months


NOT_MEANINGFUL_CASH_FLOW_POSITIVE = "not_meaningful_cash_flow_positive"


@dataclass
class RmlResult:
    value: Decimal | None
    burn: Decimal | None  # average monthly net burn over the last three months
    not_meaningful: bool
    errors: list[CalcError]
    trace: Trace


def compute_rml(period_end: date, provider: Provider, fye_month: int = 12) -> RmlResult:
    """RML = unrestricted cash / average monthly net burn (last 3 months). Burn <= 0: not meaningful."""
    defs = metric_definitions()
    burn = evaluate(named("avg_net_burn"), period_end, provider, definitions=defs, fye_month=fye_month)
    cash = evaluate(named("unrestricted_cash"), period_end, provider, definitions=defs, fye_month=fye_month)
    trace = Trace(inputs=cash.trace.inputs + burn.trace.inputs, steps=cash.trace.steps + burn.trace.steps)
    errors = burn.errors + cash.errors
    if errors:
        return RmlResult(None, burn.value, False, errors, trace)
    if burn.value <= ZERO:
        return RmlResult(None, burn.value, True, [], trace)
    return RmlResult(CALC_CONTEXT.divide(cash.value, burn.value), burn.value, False, [], trace)


class UndefinedForTemplate(Exception):
    """The covenant names a measure the borrower's spreading template does not define."""


def compile_covenant(covenant: Covenant, period_end: date | None = None, template_id: str = "ci-1") -> dict[str, Any]:
    """The archetype's formula as an expression tree."""
    params = covenant.typed_params
    archetype = covenant.archetype
    if archetype == "coverage":
        base = params.numerator_base
        deductions, denominators = _DEDUCTIONS, _DENOMINATORS
        if template_id == "vc-1":
            if base == "adjusted_ebitda":
                raise UndefinedForTemplate("adjusted EBITDA is not defined for the venture template")
            base = "vc_ebitda"
            deductions = {**_DEDUCTIONS, "unfinanced_capex": ttm("cf.vc_capex")}  # no purchase-money financing line
            denominators = {**_DENOMINATORS, "interest_expense": ttm("is.vc_interest")}
        numerator: dict[str, Any] = named(base)
        if params.deductions:
            numerator = sub(numerator, *[deductions[d] for d in params.deductions])
        parts = [denominators[d] for d in params.denominator]
        return div(numerator, parts[0] if len(parts) == 1 else add(*parts))
    if archetype == "leverage":
        return div(named(params.debt), named(params.ebitda))
    if archetype == "current_ratio":
        return div(point("bs.total_current_assets"), point("bs.total_current_liabilities"))
    if archetype == "min_tangible_net_worth":
        return named("tangible_net_worth")
    if archetype == "min_liquidity":
        cash = point("bs.cash")
        return add(cash, point("bb.availability")) if params.include_availability else cash
    if archetype == "max_capex":
        return ttm("cf.capex")  # the fiscal year at a year end, trailing twelve months at an interim date
    if archetype == "debt_to_tnw":
        return div(point("bs.total_liabilities"), named("tangible_net_worth"))
    if archetype == "min_unrestricted_cash":
        return named("unrestricted_cash")
    if archetype == "min_runway_months":
        return div(named("unrestricted_cash"), named("avg_net_burn"))  # test_covenant uses compute_rml
    if archetype == "revenue_vs_plan":
        if period_end is None:
            raise ValueError("revenue_vs_plan needs the period end to pick plan months")
        if params.metric == "arr":
            measured, months = point("saas.arr"), [period_end]
        else:
            measured = add(t3m("is.subscription_revenue"), t3m("is.services_revenue"))
            months = [shift_period_end(period_end, -2), shift_period_end(period_end, -1), period_end]
        plan = {p.period_end: p.amount for p in params.plan}
        missing = [m for m in months if m not in plan]
        if missing:
            raise PlanMissing(missing)
        total = sum((plan[m] for m in months), ZERO)
        return div(measured, const(str(total)))
    return params.expression  # custom: as written


@dataclass
class CovenantTestResult:
    covenant_id: str | None
    period_end: date
    value: Decimal | None = None  # rounded per the covenant's rounding; this is what is tested
    raw_value: Decimal | None = None  # unrounded
    threshold: Decimal | None = None  # threshold in force at the period end
    operator: str | None = None
    unit: str | None = None
    passed: bool | None = None  # None: could not be tested
    headroom: Decimal | None = None  # positive is cushion, for every operator
    headroom_pct: Decimal | None = None  # headroom / |threshold| as a fraction, 4 dp; None if threshold is 0
    trace: Trace = field(default_factory=Trace)
    errors: list[CalcError] = field(default_factory=list)
    expression: dict[str, Any] | None = None
    note: str | None = None  # e.g. not_meaningful_cash_flow_positive
    avg_net_burn: Decimal | None = None  # runway tests only: average monthly net burn over the last three months
    calc_id: str | None = None
    engine_version: str = ENGINE_VERSION


def untested(covenant_id: str | None, period_end: date, errors: list[CalcError]) -> CovenantTestResult:
    """A result for a covenant that could not be tested at all (for example no terms in force)."""
    return CovenantTestResult(covenant_id, period_end, errors=list(errors))


def is_test_date(covenant: Covenant, period_end: date, fye_month: int = 12) -> bool:
    """Whether the covenant's measurement frequency falls on `period_end`."""
    if not is_month_end(period_end):
        return False
    months = ytd_months(period_end, fye_month)
    every = {"monthly": 1, "quarterly": 3, "semiannual": 6, "annual": 12}[covenant.measurement.frequency]
    return months % every == 0


def _step_up(
    result: CovenantTestResult,
    pct: Decimal,
    step_up_from: date | None,
    period_end: date,
    provider: Provider,
    fye_month: int,
) -> Decimal | None:
    """pct x the positive net income of each fiscal year ended after `step_up_from`, up to `period_end`."""
    if type(step_up_from) is not date:
        result.errors.append(CalcError(
            E.MISSING_PARAMETER, "the tangible net worth threshold steps up with net income; step_up_from is needed",
            key="step_up_from", period_end=period_end))
        return None
    total = ZERO
    failed = False
    seen = {(i.key, i.period_end, i.months, i.sign) for i in result.trace.inputs}
    for year in range(step_up_from.year, period_end.year + 1):
        year_end = month_end(year, fye_month)
        if not step_up_from < year_end <= period_end:
            continue
        res = resolve_line("is.net_income", "fy", year_end, provider, fye_month=fye_month)
        result.errors.extend(res.errors)
        for item in res.inputs:
            if (item.key, item.period_end, item.months, item.sign) not in seen:
                seen.add((item.key, item.period_end, item.months, item.sign))
                result.trace.inputs.append(item)
        if res.value is None:
            failed = True
        elif res.value > ZERO:
            total = CALC_CONTEXT.add(total, res.value)
    return None if failed else CALC_CONTEXT.multiply(pct, total)


def test_covenant(
    covenant: Covenant | Mapping[str, Any],
    period_end: date,
    provider: Provider,
    definitions: Mapping[str, Definition | Mapping[str, Any]] | None = None,
    *,
    fye_month: int = 12,
    step_up_from: date | None = None,
    calc_id: str | None = None,
    template_id: str = "ci-1",
) -> CovenantTestResult:
    """Test one covenant at `period_end`.

    `template_id` is the borrower's spreading template; a `vc-1` coverage covenant measures
    `vc_ebitda`.

    `definitions` is the governing terms' `definitions` block. `step_up_from` is only needed by
    a min_tangible_net_worth covenant with a step-up percentage: fiscal years ended after that
    date add pct x positive net income to the threshold. Never raises on bad data.
    """
    covenant_id = covenant.get("id") if isinstance(covenant, Mapping) else getattr(covenant, "id", None)
    result = CovenantTestResult(covenant_id if isinstance(covenant_id, str) else None, period_end, calc_id=calc_id)
    try:
        cov = covenant if isinstance(covenant, Covenant) else Covenant.model_validate(covenant)
        names = build_definitions(definitions)
    except ValidationError as exc:
        result.errors.append(CalcError(
            E.INVALID_TERMS, f"covenant terms are invalid ({exc.error_count()} problem(s))", period_end=period_end,
            detail={"problems": [{"loc": ".".join(map(str, e["loc"])), "msg": e["msg"]} for e in exc.errors()]}))
        return result
    if type(period_end) is not date or not is_month_end(period_end):
        result.errors.append(CalcError(E.INVALID_PERIOD, f"period end {period_end!r} must be a month-end date"))
        return result

    result.operator, result.unit = cov.test.operator, cov.test.unit
    if cov.archetype == "min_runway_months":
        return _test_rml(cov, result, period_end, provider, fye_month)
    try:
        result.expression = compile_covenant(cov, period_end, template_id)
    except UndefinedForTemplate as exc:
        result.errors.append(CalcError(E.UNDEFINED_FOR_TEMPLATE, str(exc), key="numerator_base", period_end=period_end))
        return result
    except PlanMissing as exc:
        result.errors.append(CalcError(
            E.MISSING_PARAMETER,
            f"no approved plan figure for {', '.join(m.isoformat() for m in exc.months)}", period_end=period_end))
        return result
    evaluation = evaluate(result.expression, period_end, provider, definitions=names, rounding=cov.rounding,
                          fye_month=fye_month, calc_id=calc_id)
    result.trace = evaluation.trace
    result.errors.extend(evaluation.errors)

    threshold: Decimal | None = threshold_in_force(cov.test, period_end)
    step_pct = cov.typed_params.step_up_pct_of_net_income if cov.archetype == "min_tangible_net_worth" else None
    if step_pct is not None:
        increase = _step_up(result, step_pct, step_up_from, period_end, provider, fye_month)
        threshold = None if increase is None else round_half_up(CALC_CONTEXT.add(threshold, increase), cov.rounding.dp)
    result.threshold = threshold

    if result.errors or evaluation.rounded is None or threshold is None:
        return result
    value = evaluation.rounded
    result.value, result.raw_value = value, evaluation.value
    operator = cov.test.operator
    result.passed = {">=": value >= threshold, ">": value > threshold,
                     "<=": value <= threshold, "<": value < threshold}[operator]
    result.headroom = value - threshold if operator in (">=", ">") else threshold - value
    if threshold != ZERO:
        result.headroom_pct = round_half_up(CALC_CONTEXT.divide(result.headroom, abs(threshold)), HEADROOM_PCT_DP)
    return result


def _test_rml(cov: Covenant, result: CovenantTestResult, period_end: date, provider: Provider,
              fye_month: int) -> CovenantTestResult:
    # Reference formula for audit only; it is never evaluated. The test uses compute_rml so burn <= 0 never divides.
    result.expression = compile_covenant(cov, period_end)
    rml = compute_rml(period_end, provider, fye_month)
    result.trace = rml.trace
    result.errors.extend(rml.errors)
    result.avg_net_burn = rml.burn
    result.threshold = threshold_in_force(cov.test, period_end)
    if result.errors:
        return result
    if rml.not_meaningful:
        result.passed, result.note = True, NOT_MEANINGFUL_CASH_FLOW_POSITIVE
        return result
    value = round_half_up(rml.value, cov.rounding.dp)
    result.value, result.raw_value = value, rml.value
    threshold, operator = result.threshold, cov.test.operator
    result.passed = {">=": value >= threshold, ">": value > threshold,
                     "<=": value <= threshold, "<": value < threshold}[operator]
    result.headroom = value - threshold if operator in (">=", ">") else threshold - value
    if threshold != ZERO:
        result.headroom_pct = round_half_up(CALC_CONTEXT.divide(result.headroom, abs(threshold)), HEADROOM_PCT_DP)
    return result


test_covenant.__test__ = False  # not a pytest test, whatever the name suggests


# ---- outcomes ------------------------------------------------------------------------------

COMPLIANT = "compliant"
COMPLIANT_VARIANCE = "compliant_variance"
BREACH = "breach"
BREACH_REPORTED_COMPLIANT = "breach_reported_compliant"
CANNOT_TEST = "cannot_test"
OUTCOMES = (COMPLIANT, COMPLIANT_VARIANCE, BREACH, BREACH_REPORTED_COMPLIANT, CANNOT_TEST)


@dataclass(frozen=True)
class CertificateEntry:
    """What the borrower's compliance certificate reports for one covenant."""

    value: Decimal | None
    threshold: Decimal | None
    in_compliance: bool | None
    not_meaningful: bool = False  # the certificate prints "Not meaningful" instead of a figure

    def __post_init__(self) -> None:
        for name in ("value", "threshold"):
            number = getattr(self, name)
            if number is not None and not is_decimal(number):
                raise TypeError(f"certificate {name} must be a Decimal or None")
        if self.in_compliance is not None and type(self.in_compliance) is not bool:
            raise TypeError("certificate in_compliance must be a bool or None")
        if type(self.not_meaningful) is not bool:
            raise TypeError("certificate not_meaningful must be a bool")

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> CertificateEntry:
        """Parse {"value": "1.25", "threshold": "1.20", "in_compliance": true}; decimals as strings."""
        if not {"value", "threshold", "in_compliance"} <= set(data) <= {"value", "threshold", "in_compliance", "not_meaningful"}:
            raise ValueError(f"certificate entry must have value, threshold and in_compliance (and optionally "
                             f"not_meaningful), got {sorted(data)}")
        value = None if data["value"] is None else to_decimal(data["value"])
        threshold = None if data["threshold"] is None else to_decimal(data["threshold"])
        return cls(value, threshold, data["in_compliance"], data.get("not_meaningful", False))


@dataclass(frozen=True)
class Variance:
    field: str  # value | threshold | in_compliance
    computed: Any
    reported: Any


@dataclass
class Outcome:
    outcome: str
    variances: list[Variance] = field(default_factory=list)
    errors: list[CalcError] = field(default_factory=list)  # what is missing, for cannot_test
    certificate_compared: bool = False
    note: str | None = None


def determine_outcome(
    test_result: CovenantTestResult,
    certificate_entry: CertificateEntry | Mapping[str, Any] | None,
    tolerance: Decimal,
) -> Outcome:
    """One of the five outcomes of spec section 8.

    The computed result agrees with the certificate when the reported value is within
    `tolerance` (absolute, inclusive), the reported threshold equals the threshold in force and
    the reported compliance flag matches. With no certificate entry a pass is `compliant` and a
    fail is `breach`, with `certificate_compared` False.
    """
    if not is_decimal(tolerance):
        raise TypeError("tolerance must be a Decimal")
    if tolerance < ZERO:
        raise ValueError("tolerance cannot be negative")
    if isinstance(certificate_entry, Mapping):
        certificate_entry = CertificateEntry.from_mapping(certificate_entry)
    if test_result.errors or test_result.passed is None:
        return Outcome(CANNOT_TEST, errors=list(test_result.errors), certificate_compared=False)

    variances: list[Variance] = []
    entry = certificate_entry
    if entry is not None:
        # A not-meaningful runway has no measured value; the certificate's own figure is not a covenant input.
        if (entry.value is not None and test_result.value is not None
                and test_result.note != NOT_MEANINGFUL_CASH_FLOW_POSITIVE and abs(test_result.value - entry.value) > tolerance):
            variances.append(Variance("value", test_result.value, entry.value))
        if entry.not_meaningful and test_result.value is not None:
            # the borrower certifies the metric as not meaningful where the bank measures a figure
            variances.append(Variance("value", test_result.value, None))
        if entry.threshold is not None and entry.threshold != test_result.threshold:
            variances.append(Variance("threshold", test_result.threshold, entry.threshold))
        if entry.in_compliance is not None and entry.in_compliance != test_result.passed:
            variances.append(Variance("in_compliance", test_result.passed, entry.in_compliance))
    compared = entry is not None
    if test_result.passed:
        return Outcome(COMPLIANT_VARIANCE if variances else COMPLIANT, variances, certificate_compared=compared,
                       note=test_result.note)
    if entry is not None and entry.in_compliance is True:
        return Outcome(BREACH_REPORTED_COMPLIANT, variances, certificate_compared=compared)
    return Outcome(BREACH, variances, certificate_compared=compared)
