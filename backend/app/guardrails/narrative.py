"""Agent-written text never contains a typed figure. It refers to stored facts with
`{{fact:<id>}}` or `{{fact:<id>|<format>}}`; this module checks the references, finds any stray
figure, and renders the final text. Pure code: no I/O.
"""
import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.guardrails.numbers import stray_digits, untraceable_figures

FACT_REF = re.compile(r"\{\{fact:([0-9a-fA-F-]{36})(?:\|([a-z0-9_]+))?\}\}")
_ANY_REF = re.compile(r"\{\{[^}]*\}\}")
FORMATS = ("usd", "usd_k", "usd_m", "ratio", "pct", "days", "number")
# the formats a fact of each unit may be shown in: a ratio shown as a percentage, or dollars as
# days, is a wrong number even though it came from a fact
UNIT_FORMATS = {"usd": ("usd", "usd_k", "usd_m"), "ratio": ("ratio",), "pct": ("pct",), "days": ("days",),
                "count": ("number",)}

# a quantity spelt out is still a typed number: "twelve million", "four point two times",
# "fifteen percent". A lone small count ("two facilities") is ordinary prose and is left alone.
_UNITS_WORD = (r"zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|"
               r"sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety")
_SCALE_WORD = r"hundred|thousand|million|billion|trillion"
_NUMBER_WORDS = re.compile(
    rf"\b(?:{_UNITS_WORD}|{_SCALE_WORD})(?:[\s-]+(?:and\s+)?(?:{_UNITS_WORD}|{_SCALE_WORD}|point))+\b"
    rf"|\b(?:{_UNITS_WORD})[\s-]+(?:percent|per\s+cent|percentage\s+points?|basis\s+points?|bps|times|fold|"
    r"dollars|days)\b"
    rf"|\b(?:{_UNITS_WORD})-?fold\b"
    rf"|\b(?:a|several|few|many|{_UNITS_WORD})\s+(?:{_SCALE_WORD})s?\b"
    r"|\b(?:doubled?|doubling|tripled?|tripling|quadrupled?|halved|halving|twice|thrice)\b"
    r"|\b(?<!first\s)(?<!second\s)(?<!first-)(?<!second-)half\s+(?:of|the|as)\b"
    r"|\b(?:one|two|a)[\s-]+(?:third|thirds|quarter|quarters|fifth|fifths)\s+of\b",
    re.I)
# text that would join onto a rendered figure and change it: "{{fact}},000", "1{{fact}}",
# "{{fact}} million", "{{fact}}%"
_BEFORE_REF = re.compile(r"[\w$£€.,+\-−–]$")
_AFTER_REF = re.compile(r"^(?:[\w%$£€]|[.,]\d|[-−–]\d|\s*(?:hundred|thousand|million|billion|trillion|mm|bn|percent|"
                        r"per\s+cent|bps|basis\s+points?|times|x)\b)", re.I)


@dataclass(frozen=True)
class FactView:
    """What the renderer needs to know about a fact."""

    id: str
    value: Decimal
    unit: str  # usd | ratio | pct | days | count


@dataclass(frozen=True)
class Note:
    """One guardrail finding. `action` is what the pipeline did or must do about it. `detail`
    never repeats a figure the agent typed: notes are shown to people, and an untraced figure
    must not reach them even inside a warning. The agent's own text stays on its run record."""

    layer: str
    check: str
    action: str
    detail: str
    subject: str = ""  # the offending text itself; shown only to the person who wrote it


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
    echo: str = "",
) -> list[Note]:
    """Findings for a piece of agent text. An empty list means the text may be shown.

    - every reference must be well formed and name a fact in scope;
    - every figure typed outside a reference must match `allowed_figures` (figures from quotes
      the agent cited and constants from approved terms) or a known ratio;
    - a quantity in words is refused unless the same words are in `echo`, the text of the
      question the answer responds to (a person's own threshold may be said back to them).
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
        elif fmt is not None and fid in facts and fmt not in UNIT_FORMATS.get(facts[fid].unit, ()):
            notes.append(Note("narrative", "format_wrong_for_unit", "retry",
                              f"{token} shows a {facts[fid].unit} fact as {fmt}"))
        if _BEFORE_REF.search(text[:m.start()]) or _AFTER_REF.match(text[m.end():]):
            notes.append(Note("narrative", "reference_joined", "retry",
                              f"text is joined onto {token} and would change the figure it shows"))
    # everything outside the references, with compatibility forms folded (full-width and
    # superscript digits read as digits)
    ratios = list(known_ratios)
    outside = unicodedata.normalize("NFKC", _ANY_REF.sub(lambda m: " " * len(m.group(0)), text))
    for problem in untraceable_figures(outside, allowed_figures, ratios):
        notes.append(Note(
            "narrative", "figure_untraceable", "retry",
            "a figure was typed, not referenced, and matches no fact or cited quote", subject=problem.figure.raw,
        ))
    for word in stray_digits(outside, ratios):
        notes.append(Note("narrative", "figure_untraceable", "retry",
                          "digits were typed that are not a fact reference, a date or a section number",
                          subject=word))
    said = " ".join(echo.lower().split())
    for m in _NUMBER_WORDS.finditer(outside):
        if said and " ".join(m.group(0).lower().split()) in said:
            continue
        notes.append(Note("narrative", "number_in_words", "retry",
                          "a quantity was stated in words; quantities come from fact references",
                          subject=m.group(0)))
    return notes


def _q(value: Decimal, places: str) -> Decimal:
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


def _money(value: Decimal, places: str = "1") -> str:
    q = _q(abs(value), places)
    body = f"{q:,}"
    return f"(${body})" if value < 0 else f"${body}"


def format_fact(fact: FactView, fmt: str | None = None) -> str:
    """Render a fact as text. Rounding is half-up and happens only here, for display."""
    default = {"usd": "usd", "ratio": "ratio", "pct": "pct", "days": "days"}.get(fact.unit, "number")
    if fmt is None or fmt not in UNIT_FORMATS.get(fact.unit, (fmt,)):
        fmt = default  # a format that does not fit the unit is never applied, checked or not
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
