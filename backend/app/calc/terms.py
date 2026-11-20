"""Strict models for the terms JSON (spec section 7), which version governs, and terms drift.

Unknown keys are rejected everywhere and no calculation field is defaulted. The only
absences with a meaning are the ones the spec gives one: an absent or null add-back cap is
uncapped, an absent sublimit or eligibility limit is no limit, and absent steps are no steps.
Decimals are written as strings; floats are rejected.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StrictStr,
    StringConstraints,
    ValidationError,
    field_validator,
    model_validator,
)

from . import errors as E
from .decimal_utils import to_decimal
from .errors import CalcError
from .expr import validate_node
from .metrics import METRICS, metric_definitions
from .template import line_info


def _to_decimal(value: Any) -> Decimal:
    if isinstance(value, float):
        raise ValueError("float is not allowed; write decimals as strings")
    try:
        return to_decimal(value)
    except TypeError as exc:
        raise ValueError(str(exc)) from exc


def _to_date(value: Any) -> date:
    if isinstance(value, datetime):
        raise ValueError("expected a date, not a datetime")
    if isinstance(value, date):
        return value
    if isinstance(value, str) and len(value) == 10:
        return date.fromisoformat(value)
    raise ValueError("expected an ISO date string (YYYY-MM-DD)")


Dec = Annotated[Decimal, BeforeValidator(_to_decimal)]
NonNegDec = Annotated[Decimal, BeforeValidator(_to_decimal), Field(ge=0)]
Fraction = Annotated[Decimal, BeforeValidator(_to_decimal), Field(ge=0, le=1)]
Day = Annotated[date, BeforeValidator(_to_date)]
Name = Annotated[StrictStr, StringConstraints(min_length=1)]

Operator = Literal[">=", "<=", ">", "<"]
Unit = Literal["ratio", "usd", "pct", "days", "count"]
Basis = Literal["ttm", "ytd", "point", "fy", "t3m"]
Frequency = Literal["monthly", "quarterly", "semiannual", "annual"]
Quality = Literal["audited", "reviewed", "compiled", "internal", "tax_return"]
Archetype = Literal[
    "coverage", "leverage", "current_ratio", "min_tangible_net_worth", "min_liquidity", "max_capex",
    "debt_to_tnw", "custom",
]
AGE_BUCKET_LIMITS = (0, 30, 60, 90)


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


def _no_duplicates(items: Iterable[Any], what: str) -> None:
    seen: set[Any] = set()
    for item in items:
        if item in seen:
            raise ValueError(f"duplicate {what}: {item!r}")
        seen.add(item)


class Citation(_Model):
    document_id: Name
    field: StrictStr | None = None
    section: StrictStr | None = None
    page: StrictInt | None = None
    quote: StrictStr | None = None


# ---- definitions and add-backs ---------------------------------------------------------


class AmountCap(_Model):
    type: Literal["amount"]
    value: NonNegDec


class PctOfCap(_Model):
    type: Literal["pct_of"]
    value: NonNegDec
    of: StrictStr | dict[str, Any]  # a metric library name, or an expression tree

    @field_validator("of")
    @classmethod
    def _known_base(cls, of: Any) -> Any:
        if isinstance(of, str):
            if of not in METRICS:
                raise ValueError(f"cap base {of!r} is not a metric library name")
            return of
        problems = validate_node(of, metric_definitions())
        if problems:
            raise ValueError("cap base expression is invalid: " + "; ".join(p.message for p in problems))
        return of


Cap = Annotated[AmountCap | PctOfCap, Field(discriminator="type")]


class Addback(_Model):
    name: Name
    source_key: Name
    cap: Cap | None = None  # absent or null means uncapped; a cap of zero must be written
    citation: Citation | None = None

    @field_validator("source_key")
    @classmethod
    def _flow_line(cls, key: str) -> str:
        line = line_info(key)
        if line is None or not line.flow:
            raise ValueError(f"add-back source {key!r} is not a flow line of the template")
        return key


class Definition(_Model):
    base: Name
    addbacks: list[Addback]

    @model_validator(mode="after")
    def _check(self) -> Definition:
        if self.base not in METRICS:
            raise ValueError(f"definition base {self.base!r} is not a metric library name")
        _no_duplicates((a.name for a in self.addbacks), "add-back")
        return self


# ---- covenants --------------------------------------------------------------------------


class Step(_Model):
    from_: Day = Field(alias="from")
    value: Dec


class CovenantTest(_Model):
    operator: Operator
    threshold: Dec
    steps: list[Step] = Field(default_factory=list)
    unit: Unit

    @model_validator(mode="after")
    def _check(self) -> CovenantTest:
        _no_duplicates((s.from_ for s in self.steps), "step date")
        return self


class Measurement(_Model):
    basis: Basis
    frequency: Frequency


class Rounding(_Model):
    dp: Annotated[StrictInt, Field(ge=0, le=12)]
    mode: Literal["half_up"]


class CoverageParams(_Model):
    numerator_base: Literal["ebitda", "adjusted_ebitda"]
    deductions: list[Literal["unfinanced_capex", "cash_taxes", "distributions"]]
    denominator: Annotated[
        list[Literal["cash_interest", "interest_expense", "scheduled_principal"]], Field(min_length=1)
    ]

    @model_validator(mode="after")
    def _check(self) -> CoverageParams:
        _no_duplicates(self.deductions, "deduction")
        _no_duplicates(self.denominator, "denominator component")
        return self


class LeverageParams(_Model):
    debt: Literal["total_debt", "senior_debt"]
    ebitda: Literal["ebitda", "adjusted_ebitda"]


class NoParams(_Model):
    pass


class MinTangibleNetWorthParams(_Model):
    step_up_pct_of_net_income: NonNegDec | None  # required key; null means no step-up


class MinLiquidityParams(_Model):
    include_availability: StrictBool


class CustomParams(_Model):
    expression: dict[str, Any]


PARAMS_BY_ARCHETYPE: dict[str, type[_Model]] = {
    "coverage": CoverageParams,
    "leverage": LeverageParams,
    "current_ratio": NoParams,
    "min_tangible_net_worth": MinTangibleNetWorthParams,
    "min_liquidity": MinLiquidityParams,
    "max_capex": NoParams,
    "debt_to_tnw": NoParams,
    "custom": CustomParams,
}

# The archetype fixes the formula's periods; the stated measurement basis must agree with it.
BASIS_BY_ARCHETYPE: dict[str, tuple[str, ...]] = {
    "coverage": ("ttm",),
    "leverage": ("ttm",),
    "current_ratio": ("point",),
    "min_tangible_net_worth": ("point",),
    "min_liquidity": ("point",),
    "max_capex": ("fy", "ttm"),
    "debt_to_tnw": ("point",),
    "custom": ("ttm", "ytd", "point", "fy"),
}


class Covenant(_Model):
    id: Name
    name: Name
    archetype: Archetype
    params: dict[str, Any]
    test: CovenantTest
    measurement: Measurement
    rounding: Rounding
    citations: list[Citation] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self) -> Covenant:
        PARAMS_BY_ARCHETYPE[self.archetype].model_validate(self.params)
        allowed = BASIS_BY_ARCHETYPE[self.archetype]
        if self.measurement.basis not in allowed:
            raise ValueError(
                f"measurement basis {self.measurement.basis!r} does not fit archetype {self.archetype!r} "
                f"(allowed: {', '.join(allowed)})"
            )
        return self

    @property
    def typed_params(self) -> Any:
        """The parameters as the archetype's strict model."""
        return PARAMS_BY_ARCHETYPE[self.archetype].model_validate(self.params)

    def uses_adjusted_ebitda(self) -> bool:
        return "adjusted_ebitda" in (self.params.get("numerator_base"), self.params.get("ebitda"))


def threshold_in_force(test: CovenantTest, period_end: date) -> Decimal:
    """The base threshold, or the value of the latest step whose date is on or before `period_end`."""
    current = test.threshold
    latest: date | None = None
    for step in test.steps:
        if step.from_ <= period_end and (latest is None or step.from_ > latest):
            latest, current = step.from_, step.value
    return current


# ---- reporting and borrowing base -----------------------------------------------------------


class ReportingRequirement(_Model):
    id: Name
    document_type: Name
    frequency: Frequency
    due_days_after_period_end: Annotated[StrictInt, Field(ge=0)]
    quality: Quality | None = None
    citation: Citation | None = None


class Eligibility(_Model):
    exclude: list[Name]
    max_age_days: StrictInt | None = None
    cross_aging_pct: Fraction | None = None
    concentration_limit_pct: Fraction | None = None

    @model_validator(mode="after")
    def _check(self) -> Eligibility:
        _no_duplicates(self.exclude, "exclusion")
        if self.max_age_days is not None and self.max_age_days not in AGE_BUCKET_LIMITS:
            raise ValueError(f"max_age_days must be an ageing bucket boundary {AGE_BUCKET_LIMITS}")
        if self.cross_aging_pct is not None and self.max_age_days is None:
            raise ValueError("cross_aging_pct needs max_age_days")
        return self


class Component(_Model):
    collateral: Literal["accounts_receivable", "inventory"]
    advance_rate: Fraction
    eligibility: Eligibility
    sublimit: NonNegDec | None = None

    @model_validator(mode="after")
    def _check(self) -> Component:
        e = self.eligibility
        if self.collateral == "inventory" and (
            e.max_age_days is not None or e.cross_aging_pct is not None or e.concentration_limit_pct is not None
        ):
            raise ValueError("ageing and concentration limits do not apply to inventory")
        return self


class Reserve(_Model):
    name: Name
    amount: NonNegDec


class BorrowingBase(_Model):
    commitment: NonNegDec
    components: Annotated[list[Component], Field(min_length=1)]
    reserves: list[Reserve]
    frequency: Frequency
    citation: Citation | None = None
    # further clauses that state the block's numbers (eligibility, reserves, the commitment)
    citations: list[Citation] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self) -> BorrowingBase:
        _no_duplicates((c.collateral for c in self.components), "borrowing base component")
        _no_duplicates((r.name for r in self.reserves), "reserve")
        return self

    def component(self, collateral: str) -> Component | None:
        return next((c for c in self.components if c.collateral == collateral), None)


class Terms(_Model):
    definitions: dict[Name, Definition]
    covenants: list[Covenant]
    reporting_requirements: list[ReportingRequirement]
    borrowing_base: BorrowingBase | None  # required key; null means no borrowing base

    @model_validator(mode="after")
    def _check(self) -> Terms:
        _no_duplicates((c.id for c in self.covenants), "covenant id")
        _no_duplicates((r.id for r in self.reporting_requirements), "reporting requirement id")
        known = dict(metric_definitions())
        known.update({f"adjusted_{name}": {} for name in self.definitions})
        for covenant in self.covenants:
            if covenant.uses_adjusted_ebitda() and "ebitda" not in self.definitions:
                raise ValueError(f"covenant {covenant.id!r} uses adjusted_ebitda but definitions.ebitda is missing")
            if covenant.archetype == "custom":
                problems = validate_node(covenant.params["expression"], known)
                if problems:
                    raise ValueError(
                        f"covenant {covenant.id!r} expression is invalid: " + "; ".join(p.message for p in problems)
                    )
        return self

    def covenant(self, covenant_id: str) -> Covenant | None:
        return next((c for c in self.covenants if c.id == covenant_id), None)


# ---- versions --------------------------------------------------------------------------------


class TermsVersion(_Model):
    version: StrictInt
    status: Literal["proposed", "approved", "superseded"]
    effective_from: Day
    effective_to: Day | None  # required key; null means open-ended
    terms: Terms
    id: StrictStr | None = None
    facility_id: StrictStr | None = None
    prepared_by: StrictStr | None = None
    approved_by: StrictStr | None = None
    approved_at: StrictStr | datetime | None = None
    warnings: list[StrictStr] | None = None  # None: never checked; []: checked and clean
    source_documents: list[Any] | None = None
    clause_index: list[Citation] | None = None  # where each extracted field was found

    @model_validator(mode="after")
    def _check(self) -> TermsVersion:
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to is before effective_from")
        return self

    def contains(self, period_end: date) -> bool:
        return self.effective_from <= period_end and (self.effective_to is None or period_end <= self.effective_to)


@dataclass(frozen=True)
class TermsInForce:
    version: TermsVersion | None
    error: CalcError | None = None


def terms_in_force(versions: Iterable[TermsVersion | Mapping[str, Any]], period_end: date) -> TermsInForce:
    """The approved or superseded version whose dates contain `period_end`.

    A proposed version never governs. No governing version, or more than one, is an error.
    """
    parsed: list[TermsVersion] = []
    for item in versions:
        if isinstance(item, TermsVersion):
            parsed.append(item)
            continue
        try:
            parsed.append(TermsVersion.model_validate(item))
        except ValidationError as exc:
            return TermsInForce(None, CalcError(
                E.INVALID_TERMS, f"a terms version is invalid ({exc.error_count()} problem(s))",
                period_end=period_end,
                detail={"problems": [{"loc": ".".join(map(str, e["loc"])), "msg": e["msg"]} for e in exc.errors()]},
            ))
    governing = [v for v in parsed if v.status in ("approved", "superseded") and v.contains(period_end)]
    if len(governing) == 1:
        return TermsInForce(governing[0])
    if not governing:
        proposed = sorted(v.version for v in parsed if v.status == "proposed" and v.contains(period_end))
        return TermsInForce(None, CalcError(
            E.NO_TERMS_IN_FORCE, f"no approved terms are in force at {period_end.isoformat()}",
            period_end=period_end, detail={"proposed_versions": proposed},
        ))
    return TermsInForce(None, CalcError(
        E.AMBIGUOUS_TERMS, f"more than one approved terms version covers {period_end.isoformat()}",
        period_end=period_end, detail={"versions": sorted(v.version for v in governing)},
    ))


# ---- terms drift ------------------------------------------------------------------------------


@dataclass(frozen=True)
class TermsDifference:
    path: str  # e.g. covenants[fccr].test.threshold
    kind: str  # changed | added (only in used) | removed (only in approved)
    used: Any
    approved: Any


class _Keyed(dict):
    """A collection addressed by identity: children are written `path[key]`."""


class _Atom(list):
    """A list compared as a whole (order-free sets are sorted first)."""


def _cite(citation: Citation | None) -> Any:
    return None if citation is None else citation.model_dump()


def _normalise(terms: Terms, include_citations: bool) -> dict[str, Any]:
    def addback(a: Addback) -> dict[str, Any]:
        out: dict[str, Any] = {"source_key": a.source_key, "cap": None if a.cap is None else a.cap.model_dump()}
        if include_citations:
            out["citation"] = _cite(a.citation)
        return out

    def covenant(c: Covenant) -> dict[str, Any]:
        params = c.typed_params.model_dump()
        for key in ("deductions", "denominator"):
            if key in params:
                params[key] = _Atom(sorted(params[key]))
        out: dict[str, Any] = {
            "name": c.name, "archetype": c.archetype, "params": params,
            "test": {"operator": c.test.operator, "threshold": c.test.threshold, "unit": c.test.unit,
                     "steps": _Keyed({s.from_.isoformat(): s.value for s in sorted(c.test.steps, key=lambda s: s.from_)})},
            "measurement": c.measurement.model_dump(), "rounding": c.rounding.model_dump(),
        }
        if include_citations:
            out["citations"] = [x.model_dump() for x in c.citations]
        return out

    def requirement(r: ReportingRequirement) -> dict[str, Any]:
        out = r.model_dump(exclude={"id", "citation"})
        if include_citations:
            out["citation"] = _cite(r.citation)
        return out

    out: dict[str, Any] = {
        "definitions": _Keyed({
            name: {"base": d.base, "addbacks": _Keyed({a.name: addback(a) for a in d.addbacks})}
            for name, d in terms.definitions.items()
        }),
        "covenants": _Keyed({c.id: covenant(c) for c in terms.covenants}),
        "reporting_requirements": _Keyed({r.id: requirement(r) for r in terms.reporting_requirements}),
    }
    bb = terms.borrowing_base
    if bb is not None:
        base: dict[str, Any] = {
            "commitment": bb.commitment,
            "components": _Keyed({
                c.collateral: {
                    "advance_rate": c.advance_rate, "sublimit": c.sublimit,
                    "eligibility": {**c.eligibility.model_dump(exclude={"exclude"}),
                                    "exclude": _Atom(sorted(c.eligibility.exclude))},
                } for c in bb.components
            }),
            "reserves": _Keyed({r.name: r.amount for r in bb.reserves}),
            "frequency": bb.frequency,
        }
        if include_citations:
            base["citation"] = _cite(bb.citation)
        out["borrowing_base"] = base
    return out


def _plain(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value


def _diff(path: str, used: Any, approved: Any, out: list[TermsDifference]) -> None:
    both_dicts = isinstance(used, dict) and isinstance(approved, dict)
    if both_dicts:
        keyed = isinstance(used, _Keyed) or isinstance(approved, _Keyed)
        for key in list(approved) + [k for k in used if k not in approved]:
            child = f"{path}[{key}]" if keyed else (f"{path}.{key}" if path else str(key))
            if key not in used:
                out.append(TermsDifference(child, "removed", None, _plain(approved[key])))
            elif key not in approved:
                out.append(TermsDifference(child, "added", _plain(used[key]), None))
            else:
                _diff(child, used[key], approved[key], out)
        return
    plain_lists = (isinstance(used, list) and isinstance(approved, list)
                   and not isinstance(used, _Atom) and not isinstance(approved, _Atom))
    if plain_lists:
        for index in range(max(len(used), len(approved))):
            child = f"{path}[{index}]"
            if index >= len(used):
                out.append(TermsDifference(child, "removed", None, _plain(approved[index])))
            elif index >= len(approved):
                out.append(TermsDifference(child, "added", _plain(used[index]), None))
            else:
                _diff(child, used[index], approved[index], out)
        return
    if type(used) is bool or type(approved) is bool:
        same = type(used) is type(approved) and used == approved
    else:
        same = used == approved
    if not same:
        out.append(TermsDifference(path, "changed", _plain(used), _plain(approved)))


def compare_terms(
    used: Terms | Mapping[str, Any],
    approved: Terms | Mapping[str, Any],
    *,
    include_citations: bool = False,
) -> list[TermsDifference]:
    """Every difference between the terms a calculation used and the approved terms.

    Decimals compare by value ("1.20" equals "1.2"); order-free lists compare as sets;
    citations are ignored unless asked for. An empty list means no drift. Invalid terms
    raise pydantic's ValidationError.
    """
    used_terms = used if isinstance(used, Terms) else Terms.model_validate(used)
    approved_terms = approved if isinstance(approved, Terms) else Terms.model_validate(approved)
    out: list[TermsDifference] = []
    _diff("", _normalise(used_terms, include_citations), _normalise(approved_terms, include_citations), out)
    return out
