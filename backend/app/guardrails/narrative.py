"""Agent-written text never contains a typed figure. It refers to stored facts with
`{{fact:<id>}}` or `{{fact:<id>|<format>}}`; this module checks the references, finds any stray
figure, and renders the final text. Pure code: no I/O.
"""
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.guardrails.numbers import untraceable_figures

FACT_REF = re.compile(r"\{\{fact:([0-9a-fA-F-]{36})(?:\|([a-z0-9_]+))?\}\}")
_ANY_REF = re.compile(r"\{\{[^}]*\}\}")
FORMATS = ("usd", "usd_k", "usd_m", "ratio", "pct", "days", "number")


@dataclass(frozen=True)
class FactView:
    """What the renderer needs to know about a fact."""

    id: str
    value: Decimal
    unit: str  # usd | ratio | pct | days | count


@dataclass(frozen=True)
class Note:
    """One guardrail finding. `action` is what the pipeline did or must do about it."""

    layer: str
    check: str
    action: str
    detail: str


def referenced_fact_ids(text: str) -> list[str]:
    seen: list[str] = []
    for m in FACT_REF.finditer(text):
        fid = m.group(1).lower()
        if fid not in seen:
            seen.append(fid)
    return seen


def check_narrative(
    text: str,
    facts: Mapping[str, FactView],
    *,
    allowed_figures: Iterable[Decimal] = (),
    known_ratios: Iterable[Decimal] = (),
) -> list[Note]:
    """Findings for a piece of agent text. An empty list means the text may be shown.

    - every reference must be well formed and name a fact in scope;
    - every figure typed outside a reference must match `allowed_figures` (figures from quotes
      the agent cited and constants from approved terms) or a known ratio.
    """
    notes: list[Note] = []
    for m in _ANY_REF.finditer(text):
        token = m.group(0)
        ref = FACT_REF.fullmatch(token)
        if ref is None:
            notes.append(Note("narrative", "reference_malformed", "retry", f"cannot read reference {token}"))
            continue
        fid, fmt = ref.group(1).lower(), ref.group(2)
        if fid not in facts:
            notes.append(Note("narrative", "fact_unknown", "retry", f"fact {fid} is not in scope"))
        if fmt is not None and fmt not in FORMATS:
            notes.append(Note("narrative", "format_unknown", "retry", f"unknown format {fmt!r} in {token}"))
    for problem in untraceable_figures(_ANY_REF.sub(" ", text), allowed_figures, known_ratios):
        notes.append(Note(
            "narrative", "figure_untraceable", "retry",
            f"the figure {problem.figure.raw!r} was typed, not referenced, and matches no fact or cited quote",
        ))
    return notes


def _q(value: Decimal, places: str) -> Decimal:
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


def _money(value: Decimal, places: str = "1") -> str:
    q = _q(abs(value), places)
    body = f"{q:,}"
    return f"(${body})" if value < 0 else f"${body}"


def format_fact(fact: FactView, fmt: str | None = None) -> str:
    """Render a fact as text. Rounding is half-up and happens only here, for display."""
    fmt = fmt or {"usd": "usd", "ratio": "ratio", "pct": "pct", "days": "days"}.get(fact.unit, "number")
    v = fact.value
    if fmt == "usd":
        return _money(v)
    if fmt == "usd_k":
        return _money(v / Decimal(1000)) + " thousand"
    if fmt == "usd_m":
        return _money(v / Decimal(1_000_000), "0.1") + " million"
    if fmt == "ratio":
        return f"{_q(v, '0.01')}x"
    if fmt == "pct":
        return f"{_q(v * Decimal(100), '0.1')}%"
    if fmt == "days":
        return f"{_q(v, '1')} days"
    q = _q(v, "0.01")
    return f"{q.normalize():,f}" if q != q.to_integral() else f"{q.to_integral():,}"


def render(text: str, facts: Mapping[str, FactView]) -> str:
    """Replace every reference with the fact's formatted value. Raises KeyError on an unknown
    fact: callers must run `check_narrative` first."""

    def repl(m: re.Match[str]) -> str:
        return format_fact(facts[m.group(1).lower()], m.group(2))

    return FACT_REF.sub(repl, text)
