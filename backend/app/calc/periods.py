"""Periods and the resolution of a template line for a period mode (spec section 4).

A period is `(period_end, months)` on a fiscal-year-to-date basis. A fact provider is any
callable `get(key, period_end, months) -> FactValue | None`. Dates are always passed in;
nothing here reads a clock.
"""

from __future__ import annotations

import calendar
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from . import errors as E
from .decimal_utils import CALC_CONTEXT, is_decimal
from .errors import CalcError
from .template import line_info

MODES = ("ttm", "ytd", "point", "fy", "t3m")


@dataclass(frozen=True, order=True)
class PeriodKey:
    period_end: date
    months: int


@dataclass(frozen=True)
class FactValue:
    value: Decimal
    fact_id: str | None = None


Provider = Callable[[str, date, int], FactValue | None]


@dataclass(frozen=True)
class TraceInput:
    """One fact read by a calculation. `sign` is -1 for the prior-year YTD taken off a TTM."""

    key: str
    period_end: date
    months: int
    value: Decimal
    fact_id: str | None = None
    sign: int = 1

    def to_dict(self) -> dict:
        return {"key": self.key, "period_end": self.period_end.isoformat(), "months": self.months,
                "value": str(self.value), "fact_id": self.fact_id, "sign": self.sign}


@dataclass
class LineResolution:
    value: Decimal | None = None
    inputs: list[TraceInput] = field(default_factory=list)
    errors: list[CalcError] = field(default_factory=list)


def _check_month(fye_month: int) -> None:
    if isinstance(fye_month, bool) or not isinstance(fye_month, int) or not 1 <= fye_month <= 12:
        raise ValueError("fye_month must be an int from 1 to 12")


def month_end(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def is_month_end(d: date) -> bool:
    return d.day == calendar.monthrange(d.year, d.month)[1]


def ytd_months(period_end: date, fye_month: int = 12) -> int:
    """Months of the fiscal year elapsed at `period_end` (12 at a fiscal year end)."""
    _check_month(fye_month)
    return (period_end.month - fye_month - 1) % 12 + 1


def is_fiscal_year_end(period_end: date, fye_month: int = 12) -> bool:
    _check_month(fye_month)
    return period_end.month == fye_month


def same_period_prior_year(period_end: date) -> date:
    """The month end twelve months earlier."""
    return month_end(period_end.year - 1, period_end.month)


def prior_fiscal_year_end(period_end: date, fye_month: int = 12) -> date:
    """The last fiscal year end strictly before `period_end`."""
    _check_month(fye_month)
    year = period_end.year if period_end.month > fye_month else period_end.year - 1
    return month_end(year, fye_month)


def _months_before(period_end: date, months: int) -> date:
    """The month end `months` months before `period_end`."""
    index = period_end.year * 12 + (period_end.month - 1) - months
    return month_end(index // 12, index % 12 + 1)


def provider_from_facts(facts: Mapping[tuple[str, date, int], Decimal | FactValue]) -> Provider:
    """A provider over an in-memory table keyed `(key, period_end, months)`."""
    table: dict[tuple[str, date, int], FactValue] = {}
    for ref, value in facts.items():
        fact = value if isinstance(value, FactValue) else FactValue(value)
        if not is_decimal(fact.value):
            raise TypeError(f"fact {ref} must be a finite Decimal, got {type(fact.value).__name__}")
        table[ref] = fact

    def get(key: str, period_end: date, months: int) -> FactValue | None:
        return table.get((key, period_end, months))

    return get


def _fetch(res: LineResolution, provider: Provider, key: str, period_end: date, months: int, sign: int) -> Decimal | None:
    fact = provider(key, period_end, months)
    if fact is None:
        res.errors.append(
            CalcError(E.MISSING_INPUT, f"missing input {key} for {months} months ended {period_end.isoformat()}",
                      key=key, period_end=period_end, months=months)
        )
        return None
    if isinstance(fact, Decimal):
        fact = FactValue(fact)
    if not isinstance(fact, FactValue):
        res.errors.append(
            CalcError(E.INVALID_VALUE, f"provider returned {type(fact).__name__} for {key}; expected FactValue",
                      key=key, period_end=period_end, months=months)
        )
        return None
    if isinstance(fact.value, float):
        res.errors.append(
            CalcError(E.FLOAT_NOT_ALLOWED, f"fact {key} is a float; values must be Decimal",
                      key=key, period_end=period_end, months=months)
        )
        return None
    if not is_decimal(fact.value):
        res.errors.append(
            CalcError(E.INVALID_VALUE, f"fact {key} is not a finite Decimal",
                      key=key, period_end=period_end, months=months)
        )
        return None
    res.inputs.append(TraceInput(key, period_end, months, fact.value, fact.fact_id, sign))
    return fact.value


def resolve_line(
    key: str,
    mode: str,
    period_end: date,
    provider: Provider,
    *,
    fye_month: int = 12,
) -> LineResolution:
    """Resolve one line for a period mode.

    point: the balance at `period_end` (read as the fiscal-year-to-date period ending then).
    ytd:   the fiscal-year-to-date flow at `period_end`.
    fy:    the full fiscal year; `period_end` must be a fiscal year end.
    ttm:   at a fiscal year end, the fiscal year; at an interim date,
           YTD(current) + FY(prior) - YTD(same period, prior year).
    t3m:   the flow over the three months ending at `period_end`.
    Flow lines take ttm, ytd or fy; point-in-time lines take point only.
    """
    _check_month(fye_month)
    res = LineResolution()
    if type(period_end) is not date or not is_month_end(period_end):
        res.errors.append(
            CalcError(E.INVALID_PERIOD, f"period end {period_end!r} must be a month-end date", key=key)
        )
        return res
    line = line_info(key) if isinstance(key, str) else None
    if line is None:
        res.errors.append(CalcError(E.UNKNOWN_LINE, f"unknown line {key!r}", key=str(key), period_end=period_end))
        return res
    if mode not in MODES:
        res.errors.append(
            CalcError(E.INVALID_PERIOD_MODE, f"unknown period mode {mode!r} for {key}", key=key, period_end=period_end)
        )
        return res
    if mode == "t3m" and not line.flow:
        res.errors.append(
            CalcError(E.INVALID_PERIOD_MODE, f"{key} is a point-in-time line and cannot be read as t3m",
                      key=key, period_end=period_end)
        )
        return res
    if line.flow == (mode == "point"):
        kind = "a flow" if line.flow else "a point-in-time"
        res.errors.append(
            CalcError(E.INVALID_PERIOD_MODE, f"{key} is {kind} line and cannot be read as {mode}",
                      key=key, period_end=period_end)
        )
        return res

    months = ytd_months(period_end, fye_month)
    at_year_end = is_fiscal_year_end(period_end, fye_month)
    if mode == "fy" and not at_year_end:
        res.errors.append(
            CalcError(E.NOT_FISCAL_YEAR_END, f"{key} for the fiscal year needs a fiscal year end, got {period_end.isoformat()}",
                      key=key, period_end=period_end)
        )
        return res
    if mode == "t3m":
        current = _fetch(res, provider, key, period_end, months, 1)
        if months >= 3:
            if months == 3:
                res.value = current
                return res
            earlier = _fetch(res, provider, key, _months_before(period_end, 3), months - 3, -1)
            if current is not None and earlier is not None:
                res.value = CALC_CONTEXT.subtract(current, earlier)
            return res
        prior_fy_end = prior_fiscal_year_end(period_end, fye_month)
        prior_fy = _fetch(res, provider, key, prior_fy_end, 12, 1)
        cut_end = _months_before(prior_fy_end, 3 - months)
        cut = _fetch(res, provider, key, cut_end, 12 - (3 - months), -1)
        if None not in (current, prior_fy, cut):
            res.value = CALC_CONTEXT.subtract(CALC_CONTEXT.add(current, prior_fy), cut)
        return res
    if mode in ("point", "ytd", "fy") or at_year_end:
        res.value = _fetch(res, provider, key, period_end, months, 1)
        return res

    current = _fetch(res, provider, key, period_end, months, 1)
    prior_fy = _fetch(res, provider, key, prior_fiscal_year_end(period_end, fye_month), 12, 1)
    prior_ytd = _fetch(res, provider, key, same_period_prior_year(period_end), months, -1)
    if current is not None and prior_fy is not None and prior_ytd is not None:
        res.value = CALC_CONTEXT.subtract(CALC_CONTEXT.add(current, prior_fy), prior_ytd)
    return res
