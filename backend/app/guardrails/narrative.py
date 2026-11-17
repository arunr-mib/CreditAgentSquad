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

# A quantity spelt out is still a typed number. A number word is let through only as a plain
# count of things ("two facilities", "the next twelve months", "two of the three customers");
# anywhere else it states an amount, a ratio or a change ("leverage is above four", "four turns",
# "four and a half times", "twelve million", "zero availability").
_CARDINAL = (r"two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|"
             r"seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|"
             r"million|billion|trillion|dozens?|zero|nil")
_COUNT_NOUN = (r"facilit(?:y|ies)|loans?|borrowers?|customers?|suppliers?|vendors?|covenants?|quarters?|months?|"
               r"years?|weeks?|periods?|amendments?|waivers?|exceptions?|items?|locations?|plants?|sites?|"
               r"statements?|certificates?|documents?|reports?|tests?|signals?|lenders?|guarantors?|subsidiar(?:y|ies)|"
               r"segments?|contracts?|accounts?|occasions?|instances?|reasons?|factors?|sections?|parties|owners?|"
               r"members?|directors?|officers?|employees?|products?|lines?|projects?|properties|payments?|draws?")
_COUNT_ADJECTIVE = (r"consecutive|largest|major|principal|main|key|new|open|remaining|prior|previous|next|last|past|"
                    r"additional|other|separate|straight|successive|fiscal|calendar|interim|reporting|financial|"
                    r"compliance|late|missed|scheduled|operating|trailing")
_ALLOWED_COUNT = re.compile(
    rf"^[\s-]+(?:(?:{_COUNT_ADJECTIVE})\s+){{0,2}}(?:{_COUNT_NOUN})\b(?!\s+(?:of\s+)?(?:ebitda|revenue|debt|income))"
    rf"|^\s+of\s+(?:the|its|their|these|those|them|which)\b", re.I)
# a Roman numeral standing for a number ("leverage is IV times"); after a capitalised word it is
# part of a name ("Article IV", "Phase II")
_ROMAN = re.compile(r"(?<![A-Za-z])(?=[IVX]{2,}\b)X{0,3}(?:IX|IV|V?I{0,3})\b")
_CAPITALISED_BEFORE = re.compile(r"[A-Z][A-Za-z.]*\s+$")
# "page three", "step two": a place in a document or a sequence, not an amount
_LABEL_BEFORE = re.compile(r"\b(?:pages?|sections?|parts?|steps?|phases?|stages?|tiers?|exhibits?|schedules?|"
                           r"appendix|notes?|items?|chapters?|paragraphs?|clauses?)\s+$", re.I)
_CARDINAL_WORD = re.compile(rf"\b(?:{_CARDINAL})\b", re.I)
_OTHER_QUANTITY_WORDS = re.compile(
    r"\b(?:doubled?|doubling|tripled?|tripling|quadrupled?|quintupled?|halved|halving|twice|thrice|\w+fold)\b"
    r"|\b(?<!first\s)(?<!second\s)(?<!latter\s)(?<!first-)(?<!second-)hal(?:f|ves)\b"
    r"|\b(?:by|nearly|about|roughly|almost|around|approximately|over|under)\s+(?:a|one|two|three)[\s-](?:thirds?|quarters?|fifths?|tenths?)\b"
    r"|\b(?:a|one|two|three)[\s-](?:thirds?|quarters?|fifths?|tenths?)\s+of\b"
    r"|\b(?:one|two|three|four)-(?:thirds?|quarters?|fifths?|tenths?)\b"
    r"|\b(?:single|double|triple)[\s-]digits?\b|\b(?:tens|hundreds|thousands|millions|billions)\s+of\b"
    r"|\b\w+[\s-]figures?\b(?<!the figures)(?<!the figure)(?<!these figures)(?<!those figures)"
    r"|\b(?:below|above|under|over|than|exceeds?|exceeded|reached|near|nearly|around|about|approximately|to|at|of|is|was)\s+one\b(?!\s+(?:of|or)\b|-)"
    r"|\bone\s+(?:times?|turns?|percent|point)\b"
    r"|[¼½¾⅓⅔⅛⅜⅝⅞]",
    re.I)
# text that would join onto a rendered figure and change it: "{{fact}},000", "1{{fact}}",
# "{{fact}} million", "{{fact}}%", "({{fact}})", "{{fact}} K", "minus {{fact}}", "double {{fact}}"
_BEFORE_REF = re.compile(r"(?:[\w$£€.,+\-−–}]|\b(?:minus|negative|less|plus|double|triple|twice|half|times)\s+)$", re.I)
_AFTER_REF = re.compile(
    r"^(?:[\w%$£€{]|[.,]\d|[-−–]\d"
    r"|\s*\(?\s*(?:in\s+)?(?:hundreds?|thousands?|millions?|billions?|trillions?|mm|bn|k|m|b|percent|per\s+cent|"
    r"percentage\s+points?|points?|pts|bps|basis\s+points?|times|turns?|x)\b)", re.I)
_BRACKETED_REF = (re.compile(r"\(\s*$"), re.compile(r"^\s*\)"))


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
        before, after = text[:m.start()], text[m.end():]
        bracketed = _BRACKETED_REF[0].search(before) and _BRACKETED_REF[1].match(after)  # reads as a negative
        if _BEFORE_REF.search(before) or _AFTER_REF.match(after) or bracketed:
            notes.append(Note("narrative", "reference_joined", "retry",
                              f"text is joined onto {token} and would change the figure it shows"))
    # everything outside the references, with compatibility forms folded (full-width and
    # superscript digits read as digits)
    ratios = list(known_ratios)
    outside = unicodedata.normalize("NFKC", _ANY_REF.sub(lambda m: " " * len(m.group(0)), text))
    for problem in untraceable_figures(outside, allowed_figures, ratios, strict=True):
        notes.append(Note(
            "narrative", "figure_untraceable", "retry",
            "a figure was typed, not referenced, and matches no fact or cited quote", subject=problem.figure.raw,
        ))
    for word in stray_digits(outside, ratios, strict=True):
        notes.append(Note("narrative", "figure_untraceable", "retry",
                          "digits were typed that are not a fact reference, a date or a section number",
                          subject=word))
    said = " ".join(echo.lower().split())
    in_words = [m for m in _CARDINAL_WORD.finditer(outside)
                if not _ALLOWED_COUNT.match(outside[m.end():]) and not _LABEL_BEFORE.search(outside[:m.start()])]
    in_words += list(_OTHER_QUANTITY_WORDS.finditer(outside))
    in_words += [m for m in _ROMAN.finditer(outside) if m.group(0) and not _CAPITALISED_BEFORE.search(outside[:m.start()])]
    for m in sorted(in_words, key=lambda found: found.start()):
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
