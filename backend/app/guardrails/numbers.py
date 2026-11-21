"""Find and normalise the figures in a piece of text, and check each against an allowed set.

Pure code: no I/O. Every rule here has a test for what it must refuse and a test for what it
must still allow (see docs/lessons/number-normalisation-traps.md).
"""
import re
import unicodedata
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
# Every pattern is deliberately narrow: it must not be able to hide an amount. A reference takes
# a short section number, never a number with a comma, a unit or seven digits ("Item 4,500,000",
# "Schedule 2.75x"); a year is 1980-2049 and needs a word of time in front of it ("EBITDA of
# 2050" is an amount); an identifier never ends in a decimal ("x-3.25").
_YEAR = r"(?:19[89]\d|20[0-4]\d)"
_DAY = r"(?:0?[1-9]|[12]\d|3[01])"
_SECTION_NO = r"\d{1,3}(?:\.\d{1,3})*(?:\([A-Za-z0-9]{1,4}\))*(?:-\d{1,2})?(?![\w,%]|\.\d)"
_NOT_FIGURES: list[tuple[str, re.Pattern[str]]] = [
    ("fact_ref", re.compile(r"\{\{fact:[^}]*\}\}")),
    ("uuid", re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)),
    # identifiers: calc_3f9a2b, doc_12 (snake case), run-7, B-2 (a word, a hyphen, up to three digits)
    ("identifier", re.compile(r"\b[A-Za-z]+_[0-9A-Za-z_]*\d[0-9A-Za-z_]*\b(?![.,]\d)")),
    ("hyphen_id", re.compile(r"\b(?!(?:USD|EUR|GBP|CAD|x|ratio)-)[A-Za-z]+-\d{1,3}\b(?![.,]\d|[x%])", re.I)),
    ("iso_date", re.compile(rf"\b{_YEAR}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])\b")),
    ("slash_date", re.compile(rf"\b(?:0?[1-9]|1[0-2])/{_DAY}/(?:{_YEAR}|\d{{2}})\b(?![/\d])")),
    ("month_day", re.compile(rf"\b{_MONTH}\s+{_DAY}(?:st|nd|rd|th)?(?:,?\s+{_YEAR})?\b(?![,.]?\d)", re.I)),
    ("day_month", re.compile(rf"\b{_DAY}(?:st|nd|rd|th)?\s+{_MONTH}(?:,?\s+{_YEAR})?(?!\w)", re.I)),
    ("month_year", re.compile(rf"\b{_MONTH}\s+{_YEAR}\b", re.I)),
    ("quarter", re.compile(rf"\b(?:Q[1-4]|[1-4]Q)(?:\s?-?\s?(?:FY)?\s?{_YEAR}|-?'?\d{{2}})\b", re.I)),
    ("fiscal_year", re.compile(rf"\bFY\s?'?(?:{_YEAR}|\d{{2}})\b", re.I)),
    ("version", re.compile(r"\b(?:version\s+\d{1,3}|v\d{1,3})\b(?![.,]\d)", re.I)),
    ("section_sign", re.compile(rf"§+\s*{_SECTION_NO}")),
    ("reference", re.compile(
        r"\b(?:Sections?|Articles?|Clauses?|Exhibits?|Schedules?|Annex(?:es)?|Appendi(?:x|ces)|Amendments?|"
        rf"Paragraphs?|Pages?|Notes?|Items?)\s+(?:No\.?\s*)?(?:{_SECTION_NO}|[IVXLC]+\b)", re.I)),
    ("number_label", re.compile(r"\bNo\.\s*\d{1,3}\b(?![,.]\d)")),
    ("ordinal", re.compile(r"\b\d{1,3}(?:st|nd|rd|th)\b", re.I)),
    # a list marker is one digit or letters; "(12)" is twelve in brackets, a negative amount
    ("enumeration", re.compile(
        r"(?<![\w$])\((?:[1-9]|[ivx]{1,4}|[a-z])\)(?!\s*(?:[%x]|thousand|million|billion|mm\b|bn\b|k\b))", re.I)),
    # a year: only after a word of time, with no comma, currency sign, decimal part or unit attached
    ("year", re.compile(
        r"\b(?:in|during|since|throughout|until|through|ended|ending|fiscal(?:\s+year)?|calendar(?:\s+year)?|"
        rf"year|early|late|mid|and(?:\s+again)?(?:\s+in)?)[\s-]+{_YEAR}\b"
        r"(?!\d|[,.]\d|%|x\b|\s?(?:thousand|million|billion)\b)", re.I)),
]

# The same idea for text an agent writes, where there is no reason to be generous: only a fully
# formed date, a period label, a year after a word of time, a capitalised legal reference, a
# filing name or a hyphenated length of time may contain digits. No identifiers, versions,
# ordinals, list markers, page or note numbers: each of those has been used to carry an amount
# ("up-12 percent", "Leverage v4", "the 4th turn", "(4) against (3)", "Note 4.25", "4 may").
_MONTH_CAP = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|"
    r"Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?"
)
_STRICT_NOT_FIGURES: list[tuple[str, re.Pattern[str]]] = [
    ("fact_ref", re.compile(r"\{\{fact:[^}]*\}\}")),
    ("iso_date", re.compile(rf"(?<![\w.,$-]){_YEAR}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])\b(?![\w,.-]*\d)")),
    ("date_range", re.compile(
        rf"\b{_MONTH_CAP}\s+{_DAY}(?:st|nd|rd|th)?\s+(?:to|through)\s+{_MONTH_CAP}\s+{_DAY}(?:st|nd|rd|th)?,?\s+{_YEAR}\b(?![,.]?\d)")),
    ("month_day_year", re.compile(rf"\b{_MONTH_CAP}\s+{_DAY}(?:st|nd|rd|th)?,?\s+{_YEAR}\b(?![,.]?\d)")),
    ("day_month_year", re.compile(rf"(?<![\w.,$-]){_DAY}(?:st|nd|rd|th)?\s+{_MONTH_CAP}\s+{_YEAR}\b(?![,.]?\d)")),
    ("month_day", re.compile(rf"\b(?:on|by|of|before|after|until|through|dated|ended|ending|since|from)\s+{_MONTH_CAP}\s+{_DAY}(?:st|nd|rd|th)?\b(?![,.]?\d|\s*(?:percent|%|x\b|times|million|thousand|billion))")),
    ("month_year", re.compile(rf"\b{_MONTH_CAP}\s+{_YEAR}\b(?![,.]?\d)")),
    ("quarter", re.compile(rf"\b(?:Q[1-4]|[1-4]Q)(?:\s?-?\s?(?:FY)?\s?{_YEAR}|-?'?\d{{2}})\b(?![,.]?\d)")),
    ("fiscal_year", re.compile(rf"\bFY\s?'?(?:{_YEAR}|\d{{2}})\b(?![,.]?\d)")),
    ("section_sign", re.compile(rf"§+\s*{_SECTION_NO}")),
    # a reference is one only where a reference would stand: after "under", "in", "by", "see",
    # "pursuant to" and the like, or opening a sentence. "stood at Section 4.25" is a ratio.
    ("reference", re.compile(
        r"(?:(?:^|[.;:(,]\s*)|\b(?:under|in|by|per|see|and|or|with|(?:pursuant|subject|according)\s+to)\s+)"
        rf"(?:Sections?|Articles?|Clauses?|Exhibits?|Schedules?|Annex(?:es)?|Appendi(?:x|ces))\s+(?:{_SECTION_NO}|[IVXLC]+\b)"
        r"(?!\s+(?:against|versus|vs\.?|times|turns?)\b)")),
    # where a part of the document sits ("the debt schedule on page 5"): only straight after the
    # name of a part of a document, a whole number of one to three digits, nothing after it that
    # makes it a measurement. A page after a measure ("leverage on Page 5") stays refused: a
    # reviewer used that to carry a ratio. Found in the live runs, where a note was withheld.
    ("page_reference", re.compile(
        r"\b(?:schedules?|statements?|notes?|tables?|reports?|aging|listings?|certificates?|sheets?)"
        r"\s+(?:is\s+|are\s+)?on\s+pages?\s+\d{1,3}\b(?![\w,.%]*\d|\s*(?:percent|%|x\b|times|turns?|"
        r"thousand|million|billion|bps|basis))", re.I)),
    ("amendment", re.compile(r"\b(?:Amendments?|Waivers?|Forbearance Agreements?)\s+(?:No\.?\s*)?\d{1,2}\b(?![\w,.%]*\d|\s*(?:percent|%|x\b))")),
    ("filing", re.compile(r"\b(?:Form\s+)?(?:10-K|10-Q|8-K|K-1|S-1)\b")),
    # a length of time naming a requirement or a document ("the 120-day reporting requirement",
    # "a 13-week cash flow forecast"), never a measurement ("a 74-day cycle")
    ("length_of_time", re.compile(
        r"(?<![\w.,$-])\d{1,3}-(?:day|week|month|year)\s+(?:reporting|delivery|notice|cure|grace|cash\s+flow|"
        r"forecast|budget|deadline|requirement|window|extension|waiver|standstill|forbearance)\b")),
    ("quarter_alone", re.compile(r"(?<![\w.,$-])Q[1-4]\b(?![,.]?\d|\s*(?:percent|%|x\b|times|million|thousand|billion))")),
    # the names of the standard aging buckets and customer rankings, which are not measurements
    ("aging_bucket", re.compile(
        r"\b(?:more\s+than|over|greater\s+than|at\s+least|beyond)\s+(?:30|60|90|120|150|180)\s+days\s+"
        r"(?:past\s+due|delinquent|overdue)\b")),
    ("ranking", re.compile(r"\btop-(?:5|10|20|25|50|100)\s+(?:customers?|suppliers?|vendors?|accounts?)\b", re.I)),
    # a year: only close to the present, only after a word of time. A four-digit amount that
    # happens to look like a nearby year after "in" is the one thing this cannot tell apart.
    ("year", re.compile(
        r"\b(?:in|during|since|throughout|until|through|fiscal(?:\s+year)?|calendar(?:\s+year)?|"
        r"year|early|late|mid|(?:quarter|half|months?|end|start|beginning|close)\s+of|compared\s+(?:with|to)|"
        r"versus|from)[\s-]+(?:201\d|202\d|2030)\b"
        r"(?!\d|[,.]\d|%|x\b|\s?(?:thousand|million|billion|percent)\b)", re.I)),
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


def blank_non_figures(text: str, strict: bool = False) -> str:
    """Replace dates, identifiers, references and similar with spaces, keeping positions.
    `strict` is for text an agent wrote: far fewer things are let through."""
    for _name, pattern in (_STRICT_NOT_FIGURES if strict else _NOT_FIGURES):
        text = pattern.sub(lambda m: " " * len(m.group(0)), text)
    return text


def stray_digits(text: str, known_ratios: Iterable[Decimal] = (), strict: bool = False) -> list[str]:
    """Words that still hold a digit once dates, references and well-formed figures are set
    aside: digits glued to letters or punctuation, where no figure can be read and so none can
    be traced ("USD4,500,000", "approx.3.10", "EUR12.5m"). Agent-written text may contain none."""
    cleaned = list(_drop_to_one(blank_non_figures(text, strict), known_ratios))
    for m in _FIGURE.finditer("".join(cleaned)):
        for i in range(m.start(), m.end()):
            cleaned[i] = " "
    left = "".join(cleaned)
    return [m.group(0) for m in re.finditer(r"\S+", text)
            if any(ch.isdigit() or unicodedata.category(ch) == "No" for ch in left[m.start():m.end()])]


def _drop_to_one(text: str, known_ratios: Iterable[Decimal]) -> str:
    """In "1.25 to 1.00" drop the trailing "to 1.00" only when 1.25 is a ratio we already know."""
    ratios = list(known_ratios)

    def repl(m: re.Match[str]) -> str:
        n = to_decimal(m.group("n"))
        if n is not None and any(same_number(n, r) for r in ratios):
            return m.group("n") + "x" + " " * (len(m.group(0)) - len(m.group("n")) - 1)
        return m.group(0)

    return _N_TO_ONE.sub(repl, text)


def extract_figures(text: str, known_ratios: Iterable[Decimal] = (), strict: bool = False) -> list[Figure]:
    """Every figure in the text after non-figures are blanked. Never raises."""
    cleaned = _drop_to_one(blank_non_figures(text, strict), known_ratios)
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
    text: str, allowed: Iterable[Decimal], known_ratios: Iterable[Decimal] = (), strict: bool = False
) -> list[Untraceable]:
    """Figures in the text that match nothing in `allowed`.

    A percentage matches either its printed value or that value divided by one hundred.
    A figure also matches when its absolute value matches and the text printed it unsigned.
    """
    allowed_list = list(allowed)
    ratios = list(known_ratios)
    problems: list[Untraceable] = []
    for fig in extract_figures(text, ratios, strict):
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
