"""Find and normalise the figures in a piece of text, and check each against an allowed set.

Pure code: no I/O. Every rule here has a test for what it must refuse and a test for what it
must still allow (see docs/lessons/number-normalisation-traps.md).
"""
import re
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

_SCALES = {
    "k": Decimal(1_000), "m": Decimal(1_000_000), "mm": Decimal(1_000_000),
    "bn": Decimal(1_000_000_000), "b": Decimal(1_000_000_000),
    "thousand": Decimal(1_000), "million": Decimal(1_000_000), "billion": Decimal(1_000_000_000),
}
_MONTH = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|"
    r"Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?"
)

# Things that contain digits but are not figures. Each is blanked out before figures are read.
_NOT_FIGURES: list[tuple[str, re.Pattern[str]]] = [
    ("fact_ref", re.compile(r"\{\{fact:[^}]*\}\}")),
    ("uuid", re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)),
    # identifiers such as calc_3f9a2b, run-7, doc_12: letters, a separator, then a part with a digit
    ("identifier", re.compile(r"\b[A-Za-z][A-Za-z]*[_-][0-9A-Za-z_-]*\d[0-9A-Za-z_-]*\b")),
    ("iso_date", re.compile(r"\b\d{4}-\d{2}-\d{2}\b")),
    ("slash_date", re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b")),
    ("month_day", re.compile(rf"\b{_MONTH}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+\d{{4}})?\b", re.I)),
    ("day_month", re.compile(rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+{_MONTH}(?:,?\s+\d{{4}})?(?!\w)", re.I)),
    ("month_year", re.compile(rf"\b{_MONTH}\s+\d{{4}}\b", re.I)),
    ("quarter", re.compile(r"\b(?:Q[1-4]|[1-4]Q)\s?-?\s?(?:FY)?\s?'?\d{2,4}\b", re.I)),
    ("fiscal_year", re.compile(r"\bFY\s?'?\d{2,4}\b", re.I)),
    ("version", re.compile(r"\b(?:version\s+\d+|v\d+)\b", re.I)),
    ("section_sign", re.compile(r"§+\s*\d[\w.()\-]*")),
    ("reference", re.compile(
        r"\b(?:Sections?|Articles?|Clauses?|Exhibits?|Schedules?|Annex(?:es)?|Appendi(?:x|ces)|Amendments?|"
        r"Paragraphs?|Pages?|Notes?|Items?)\s+(?:No\.?\s*)?(?:\d[\w.()\-]*|[IVXLC]+\b)", re.I)),
    ("number_label", re.compile(r"\bNo\.\s*\d+\b")),
    ("ordinal", re.compile(r"\b\d+(?:st|nd|rd|th)\b", re.I)),
    ("enumeration", re.compile(r"(?<![\w$])\((?:\d{1,2}|[ivx]{1,4}|[a-z])\)(?!\s*[%x])", re.I)),
    # a bare year: four digits 1900-2099 with no comma, currency sign, decimal part or unit attached
    ("year", re.compile(r"(?<![\d,.$£€(-])\b(?:19|20)\d{2}\b(?![\d,%]|\.\d|x\b|\s?(?:thousand|million|billion)\b)")),
]

_FIGURE = re.compile(
    r"""
    (?<![\w.,])                                  # not inside a word or a longer number
    (?P<open>\()?
    (?P<sign>[-−–])?
    (?P<cur>[$£€])?\s?
    (?P<num>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)
    (?:(?P<suffix>mm|bn|k|m|b|x|%)(?![A-Za-z]))? # a scale or unit counts only when attached
    (?:\s(?P<word>thousand|million|billion)\b)?
    (?P<close>\))?
    """,
    re.X | re.I,
)
_N_TO_ONE = re.compile(
    r"(?P<n>\d+(?:\.\d+)?)(?P<x>x)?(?P<tail>\s*(?:to|:)\s*1(?:\.0+)?(?:x)?)(?!\d|[.,]\d|\w)", re.I
)


@dataclass(frozen=True)
class Figure:
    value: Decimal
    raw: str
    start: int
    end: int
    kind: str  # amount | ratio | percent


def to_decimal(text: str) -> Decimal | None:
    try:
        return Decimal(text.replace(",", ""))
    except (InvalidOperation, AttributeError):
        return None


def same_number(a: Decimal, b: Decimal) -> bool:
    """Equal within a relative tolerance of one part in a million."""
    scale = max(Decimal(1), abs(a), abs(b))
    return abs(a - b) <= Decimal("0.000001") * scale


def blank_non_figures(text: str) -> str:
    """Replace dates, identifiers, references and similar with spaces, keeping positions."""
    for _name, pattern in _NOT_FIGURES:
        text = pattern.sub(lambda m: " " * len(m.group(0)), text)
    return text


def _drop_to_one(text: str, known_ratios: Iterable[Decimal]) -> str:
    """In "1.25 to 1.00" drop the trailing "to 1.00" only when 1.25 is a ratio we already know."""
    ratios = list(known_ratios)

    def repl(m: re.Match[str]) -> str:
        n = to_decimal(m.group("n"))
        if n is not None and any(same_number(n, r) for r in ratios):
            return m.group("n") + "x" + " " * (len(m.group(0)) - len(m.group("n")) - 1)
        return m.group(0)

    return _N_TO_ONE.sub(repl, text)


def extract_figures(text: str, known_ratios: Iterable[Decimal] = ()) -> list[Figure]:
    """Every figure in the text after non-figures are blanked. Never raises."""
    cleaned = _drop_to_one(blank_non_figures(text), known_ratios)
    figures: list[Figure] = []
    for m in _FIGURE.finditer(cleaned):
        value = to_decimal(m.group("num"))
        if value is None:
            continue
        suffix = (m.group("suffix") or "").lower()
        word = (m.group("word") or "").lower()
        kind = "amount"
        if suffix == "x":
            kind = "ratio"
        elif suffix == "%":
            kind = "percent"
        elif suffix:
            value *= _SCALES[suffix]
        if word:
            value *= _SCALES[word]
        balanced = bool(m.group("open")) and bool(m.group("close"))
        # (1,200) is negative; (1.25x) and (12.5%) are a positive ratio or percentage in brackets
        negative = bool(m.group("sign")) or (balanced and kind == "amount")
        if negative:
            value = -value
        figures.append(Figure(value=value, raw=m.group(0).strip(), start=m.start(), end=m.end(), kind=kind))
    return figures


@dataclass(frozen=True)
class Untraceable:
    figure: Figure
    reason: str = "figure_untraceable"


def untraceable_figures(
    text: str, allowed: Iterable[Decimal], known_ratios: Iterable[Decimal] = ()
) -> list[Untraceable]:
    """Figures in the text that match nothing in `allowed`.

    A percentage matches either its printed value or that value divided by one hundred.
    A figure also matches when its absolute value matches and the text printed it unsigned.
    """
    allowed_list = list(allowed)
    ratios = list(known_ratios)
    problems: list[Untraceable] = []
    for fig in extract_figures(text, ratios):
        candidates = [fig.value]
        if fig.kind == "percent":
            candidates.append(fig.value / Decimal(100))
        pool = allowed_list + ratios
        ok = any(same_number(c, a) for c in candidates for a in pool)
        if not ok and fig.value >= 0:
            # prose often prints an outflow or a loss without its sign: "capex of 1,200"
            ok = any(same_number(c, abs(a)) for c in candidates for a in pool)
        if not ok:
            problems.append(Untraceable(fig))
    return problems


_PRINTED = re.compile(
    r"^\s*(?P<open>\()?\s*(?P<sign>[-−–])?\s*(?P<cur>[$£€])?\s*(?P<sign2>[-−–])?\s*"
    r"(?P<num>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)\s*(?P<unit>%|x)?\s*(?P<close>\))?\s*$"
)
_DASHES = {"-", "—", "–", "−", "$-", "$—", "$ -", "$ —"}


@dataclass(frozen=True)
class PrintedFigure:
    value: Decimal
    unit: str  # "" | "%" | "x"
    is_dash: bool = False


def parse_printed_figure(text: str) -> PrintedFigure | None:
    """Parse one figure exactly as printed in a statement cell.

    "(1,200)" is negative; "$ 4,500" is positive; a lone dash means zero. Returns None for anything
    that is not a single clean figure, so the caller refuses rather than guesses.
    """
    stripped = text.strip()
    if stripped in _DASHES:
        return PrintedFigure(Decimal(0), "", is_dash=True)
    m = _PRINTED.match(stripped)
    if m is None:
        return None
    if bool(m.group("open")) != bool(m.group("close")):
        return None  # unbalanced bracket: refuse, do not let the figure vanish or flip
    value = to_decimal(m.group("num"))
    if value is None:
        return None
    if m.group("open") or m.group("sign") or m.group("sign2"):
        value = -value
    return PrintedFigure(value, m.group("unit") or "")
