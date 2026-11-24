"""Traced expression engine (spec section 5).

`evaluate` walks a JSON expression tree over Decimals and returns the value, the value
rounded per the formula's rounding spec, and a trace naming every fact it read. It never
raises on bad data: a malformed node, a missing input or a non-positive denominator comes
back as a structured error and the value is None.

Node types: line, const, add, sub, mul, div, min, max, named, addback, and `shift`
(an extension: evaluate `arg` at a period end `months` away, used for year-on-year metrics).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, localcontext
from typing import Any

from . import errors as E
from .decimal_utils import CALC_CONTEXT, ZERO, FloatNotAllowed, round_half_up, to_decimal
from .errors import CalcError
from .periods import MODES, Provider, TraceInput, is_month_end, month_end, resolve_line
from .template import line_info

ENGINE_VERSION = "calc-1"
MAX_DEPTH = 100

# op -> (required keys, optional keys), besides "op" itself
_SHAPES: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    "line": (frozenset({"key", "period"}), frozenset()),
    "const": (frozenset({"value"}), frozenset()),
    "add": (frozenset({"args"}), frozenset()),
    "sub": (frozenset({"args"}), frozenset()),
    "mul": (frozenset({"args"}), frozenset()),
    "min": (frozenset({"args"}), frozenset()),
    "max": (frozenset({"args"}), frozenset()),
    "div": (frozenset({"num", "den"}), frozenset()),
    "named": (frozenset({"name"}), frozenset()),
    "addback": (frozenset({"name", "source"}), frozenset({"cap"})),
    "shift": (frozenset({"months", "arg"}), frozenset()),
}
_CAP_SHAPES = {"amount": frozenset({"type", "value"}), "pct_of": frozenset({"type", "value", "of"})}


@dataclass(frozen=True)
class TraceStep:
    """One evaluated node, in evaluation order (children before parents)."""

    op: str
    label: str | None
    value: Decimal
    period_end: date


@dataclass(frozen=True)
class AddbackTrace:
    name: str
    raw: Decimal  # the add-back's source amount before any cap
    cap_type: str | None  # None (uncapped) | "amount" | "pct_of"
    cap_value: Decimal | None  # the cap parameter: an amount, or the fraction for pct_of
    cap_limit: Decimal | None  # the cap in dollars; None means uncapped
    applied: Decimal  # min(raw, cap_limit), or raw when uncapped
    capped: bool
    period_end: date


@dataclass
class Trace:
    inputs: list[TraceInput] = field(default_factory=list)
    addbacks: list[AddbackTrace] = field(default_factory=list)
    steps: list[TraceStep] = field(default_factory=list)


@dataclass
class EvalResult:
    value: Decimal | None
    rounded: Decimal | None
    trace: Trace
    errors: list[CalcError]
    calc_id: str | None = None
    engine_version: str = ENGINE_VERSION

    @property
    def ok(self) -> bool:
        return not self.errors


def _canonical(node: Any) -> str:
    return json.dumps(node, sort_keys=True, default=str)


def _number(value: Any, what: str) -> Decimal | CalcError:
    try:
        return to_decimal(value)
    except FloatNotAllowed:
        return CalcError(E.FLOAT_NOT_ALLOWED, f"{what} is a float; write it as a string")
    except (TypeError, ValueError):
        return CalcError(E.INVALID_VALUE, f"{what} is not a decimal number: {value!r}")


def _check_cap(cap: Any) -> CalcError | None:
    if cap is None:
        return None
    if not isinstance(cap, Mapping):
        return CalcError(E.INVALID_NODE, "an add-back cap must be null or an object")
    kind = cap.get("type")
    if kind not in _CAP_SHAPES:
        return CalcError(E.INVALID_NODE, f"unknown add-back cap type {kind!r}")
    unknown = set(cap) - _CAP_SHAPES[kind]
    if unknown:
        return CalcError(E.UNKNOWN_KEY, f"unknown key(s) in {kind} cap: {sorted(map(str, unknown))}")
    missing = _CAP_SHAPES[kind] - set(cap)
    if missing:
        return CalcError(E.INVALID_NODE, f"{kind} cap is missing {sorted(missing)}")
    number = _number(cap["value"], "add-back cap value")
    if isinstance(number, CalcError):
        return number
    if number < 0:
        return CalcError(E.NEGATIVE_CAP, f"add-back cap value {number} is negative")
    return None


def _check_node(node: Any) -> CalcError | None:
    """Check one node's own shape (not its children)."""
    if not isinstance(node, Mapping):
        return CalcError(E.INVALID_NODE, f"an expression node must be an object, got {type(node).__name__}")
    op = node.get("op")
    if op is None:
        return CalcError(E.INVALID_NODE, "node has no op")
    if not isinstance(op, str) or op not in _SHAPES:
        return CalcError(E.UNKNOWN_OP, f"unknown op {op!r}")
    required, optional = _SHAPES[op]
    unknown = set(node) - required - optional - {"op"}
    if unknown:
        return CalcError(E.UNKNOWN_KEY, f"unknown key(s) in {op} node: {sorted(map(str, unknown))}")
    missing = required - set(node)
    if missing:
        return CalcError(E.INVALID_NODE, f"{op} node is missing {sorted(missing)}")

    if op == "line":
        key, mode = node["key"], node["period"]
        if not isinstance(key, str):
            return CalcError(E.INVALID_NODE, "line key must be a string")
        line = line_info(key)
        if line is None:
            return CalcError(E.UNKNOWN_LINE, f"unknown line {key!r}", key=key)
        if mode not in MODES:
            return CalcError(E.INVALID_PERIOD_MODE, f"unknown period mode {mode!r} for {key}", key=key)
        if line.flow == (mode == "point"):
            return CalcError(E.INVALID_PERIOD_MODE, f"{key} cannot be read as {mode}", key=key)
    elif op == "const":
        number = _number(node["value"], "constant")
        if isinstance(number, CalcError):
            return number
    elif op in ("add", "sub", "mul", "min", "max"):
        args = node["args"]
        if not isinstance(args, (list, tuple)) or len(args) < (2 if op == "sub" else 1):
            return CalcError(E.INVALID_NODE, f"{op} needs a list of at least {2 if op == 'sub' else 1} argument(s)")
        if op in ("add", "sub"):
            seen: set[str] = set()
            names: set[str] = set()
            for arg in args:
                text = _canonical(arg)
                name = arg.get("name") if isinstance(arg, Mapping) and arg.get("op") == "addback" else None
                if text in seen or (name is not None and name in names):
                    return CalcError(E.DUPLICATE_COMPONENT, f"duplicate component in {op}: {text}",
                                     detail={"component": text})
                seen.add(text)
                if name is not None:
                    names.add(name)
    elif op == "named":
        if not isinstance(node["name"], str) or not node["name"]:
            return CalcError(E.INVALID_NODE, "named needs a definition name")
    elif op == "addback":
        if not isinstance(node["name"], str) or not node["name"]:
            return CalcError(E.INVALID_NODE, "addback needs a name")
        return _check_cap(node.get("cap"))
    elif op == "shift":
        months = node["months"]
        if isinstance(months, bool) or not isinstance(months, int):
            return CalcError(E.INVALID_NODE, "shift months must be an integer")
    return None


def _children(node: Mapping) -> list[Any]:
    op = node["op"]
    if op in ("add", "sub", "mul", "min", "max"):
        return list(node["args"])
    if op == "div":
        return [node["num"], node["den"]]
    if op == "shift":
        return [node["arg"]]
    if op == "addback":
        cap = node.get("cap")
        return [node["source"]] + ([cap["of"]] if cap and cap["type"] == "pct_of" else [])
    return []


def validate_node(node: Any, definitions: Mapping[str, Any] | None = None) -> list[CalcError]:
    """Structural check of a whole tree without reading any facts.

    With `definitions`, `named` references must exist (definitions themselves are not walked).
    """
    found: list[CalcError] = []

    def walk(n: Any, depth: int) -> None:
        if depth > MAX_DEPTH:
            found.append(CalcError(E.INVALID_NODE, "expression is nested too deeply"))
            return
        error = _check_node(n)
        if error is not None:
            found.append(error)
            return
        if n["op"] == "named" and definitions is not None and n["name"] not in definitions:
            found.append(CalcError(E.UNKNOWN_DEFINITION, f"unknown definition {n['name']!r}"))
        for child in _children(n):
            walk(child, depth + 1)

    walk(node, 0)
    return found


def shift_period_end(period_end: date, months: int) -> date:
    index = period_end.year * 12 + (period_end.month - 1) + months
    return month_end(index // 12, index % 12 + 1)


class _Run:
    def __init__(self, provider: Provider, definitions: Mapping[str, Any], fye_month: int) -> None:
        self.provider = provider
        self.definitions = definitions
        self.fye_month = fye_month
        self.trace = Trace()
        self.errors: list[CalcError] = []
        self._seen_inputs: set[tuple] = set()
        self._seen_errors: set[tuple] = set()
        self._lines: dict[tuple, Decimal | None] = {}
        self._named: dict[tuple, Decimal | None] = {}
        self._stack: list[tuple] = []
        self._addbacks: set[tuple] = set()

    def fail(self, error: CalcError) -> None:
        ident = (error.code, error.key, error.period_end, error.months, error.message)
        if ident not in self._seen_errors:
            self._seen_errors.add(ident)
            self.errors.append(error)

    def step(self, op: str, label: str | None, value: Decimal | None, period_end: date) -> Decimal | None:
        if value is not None:
            self.trace.steps.append(TraceStep(op, label, value, period_end))
        return value

    def eval(self, node: Any, period_end: date, depth: int = 0) -> Decimal | None:
        if depth > MAX_DEPTH:
            self.fail(CalcError(E.INVALID_NODE, "expression is nested too deeply"))
            return None
        error = _check_node(node)
        if error is not None:
            self.fail(error)
            return None
        op = node["op"]
        handler = getattr(self, f"_op_{op}", None) or self._op_nary
        return self.step(op, _label(node), handler(node, period_end, depth), period_end)

    def _op_line(self, node: Mapping, period_end: date, depth: int) -> Decimal | None:
        ref = (node["key"], node["period"], period_end)
        if ref not in self._lines:
            res = resolve_line(node["key"], node["period"], period_end, self.provider, fye_month=self.fye_month)
            for item in res.inputs:
                ident = (item.key, item.period_end, item.months, item.sign)
                if ident not in self._seen_inputs:
                    self._seen_inputs.add(ident)
                    self.trace.inputs.append(item)
            for err in res.errors:
                self.fail(err)
            self._lines[ref] = res.value
        return self._lines[ref]

    def _op_const(self, node: Mapping, period_end: date, depth: int) -> Decimal | None:
        return to_decimal(node["value"])

    def _op_nary(self, node: Mapping, period_end: date, depth: int) -> Decimal | None:
        values = [self.eval(arg, period_end, depth + 1) for arg in node["args"]]
        if any(v is None for v in values):
            return None
        op = node["op"]
        if op == "min":
            return min(values)
        if op == "max":
            return max(values)
        total = values[0]
        for v in values[1:]:
            total = total + v if op == "add" else total - v if op == "sub" else total * v
        return total

    def _op_div(self, node: Mapping, period_end: date, depth: int) -> Decimal | None:
        num = self.eval(node["num"], period_end, depth + 1)
        den = self.eval(node["den"], period_end, depth + 1)
        if den is not None and den <= ZERO:
            self.fail(CalcError(E.NON_POSITIVE_DENOMINATOR, f"denominator is {den}; it must be greater than zero",
                                period_end=period_end, detail={"denominator": den, "node": _canonical(node["den"])}))
            return None
        if num is None or den is None:
            return None
        return num / den

    def _op_named(self, node: Mapping, period_end: date, depth: int) -> Decimal | None:
        name = node["name"]
        ref = (name, period_end)
        if ref in self._named:
            return self._named[ref]
        if name not in self.definitions:
            self.fail(CalcError(E.UNKNOWN_DEFINITION, f"unknown definition {name!r}", detail={"name": name}))
            return None
        if ref in self._stack:
            chain = [n for n, _ in self._stack] + [name]
            self.fail(CalcError(E.CIRCULAR_DEFINITION, f"definition {name!r} refers to itself: {' -> '.join(chain)}",
                                detail={"chain": chain}))
            return None
        self._stack.append(ref)
        try:
            value = self.eval(self.definitions[name], period_end, depth + 1)
        finally:
            self._stack.pop()
        self._named[ref] = value
        return value

    def _op_addback(self, node: Mapping, period_end: date, depth: int) -> Decimal | None:
        name = node["name"]
        ref = (name, period_end)
        if ref in self._addbacks:
            self.fail(CalcError(E.DUPLICATE_COMPONENT, f"add-back {name!r} is applied more than once",
                                period_end=period_end, detail={"component": name}))
            return None
        self._addbacks.add(ref)
        raw = self.eval(node["source"], period_end, depth + 1)
        cap = node.get("cap")
        cap_type = cap_value = cap_limit = None
        if cap is not None:
            cap_type = cap["type"]
            cap_value = to_decimal(cap["value"])
            if cap_type == "amount":
                cap_limit = cap_value
            else:
                base = self.eval(cap["of"], period_end, depth + 1)
                if base is None:
                    return None
                cap_limit = cap_value * base
                if cap_limit < ZERO:
                    self.fail(CalcError(E.NEGATIVE_CAP, f"cap of add-back {name!r} is {cap_limit}; a cap cannot be negative",
                                        period_end=period_end, detail={"cap_limit": cap_limit, "base": base}))
                    return None
        if raw is None:
            return None
        applied = raw if cap_limit is None else min(raw, cap_limit)
        self.trace.addbacks.append(
            AddbackTrace(name, raw, cap_type, cap_value, cap_limit, applied, applied != raw, period_end)
        )
        return applied

    def _op_shift(self, node: Mapping, period_end: date, depth: int) -> Decimal | None:
        return self.eval(node["arg"], shift_period_end(period_end, node["months"]), depth + 1)


def _label(node: Mapping) -> str | None:
    op = node["op"]
    if op == "line":
        return f"{node['key']}:{node['period']}"
    if op == "const":
        return str(node["value"])
    if op in ("named", "addback"):
        return node["name"]
    if op == "shift":
        return str(node["months"])
    return None


def parse_rounding(rounding: Any) -> tuple[int, str] | CalcError:
    """Accept {"dp": int, "mode": "half_up"} or an object with those attributes."""
    if isinstance(rounding, Mapping):
        if set(rounding) != {"dp", "mode"}:
            return CalcError(E.INVALID_ROUNDING, f"rounding must have exactly dp and mode, got {sorted(map(str, rounding))}")
        dp, mode = rounding["dp"], rounding["mode"]
    elif hasattr(rounding, "dp") and hasattr(rounding, "mode"):
        dp, mode = rounding.dp, rounding.mode
    else:
        return CalcError(E.INVALID_ROUNDING, f"rounding must be an object with dp and mode, got {rounding!r}")
    if isinstance(dp, bool) or not isinstance(dp, int) or dp < 0:
        return CalcError(E.INVALID_ROUNDING, f"rounding dp must be a non-negative integer, got {dp!r}")
    if mode != "half_up":
        return CalcError(E.INVALID_ROUNDING, f"rounding mode must be half_up, got {mode!r}")
    return dp, mode


def evaluate(
    node: Any,
    period_end: date,
    provider: Provider,
    *,
    definitions: Mapping[str, Any] | None = None,
    rounding: Any = None,
    fye_month: int = 12,
    calc_id: str | None = None,
) -> EvalResult:
    """Evaluate an expression tree at `period_end`.

    `definitions` maps a name to an expression tree for `named` nodes. `rounding` is the
    formula's spec, applied once to the final value (`rounded`); `value` stays unrounded.
    """
    run = _Run(provider, definitions or {}, fye_month)
    if type(period_end) is not date or not is_month_end(period_end):
        error = CalcError(E.INVALID_PERIOD, f"period end {period_end!r} must be a month-end date")
        return EvalResult(None, None, run.trace, [error], calc_id)
    with localcontext(CALC_CONTEXT):
        value = run.eval(node, period_end)
        rounded = None
        if rounding is not None:
            spec = parse_rounding(rounding)
            if isinstance(spec, CalcError):
                run.fail(spec)
            elif value is not None and not run.errors:
                rounded = round_half_up(value, spec[0])
    if run.errors:
        value = None
    return EvalResult(value, rounded, run.trace, run.errors, calc_id)
