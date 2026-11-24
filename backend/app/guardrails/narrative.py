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
             r"millions?|billions?|trillions?|thousands|hundreds|dozens?|zero|nil")
_COUNT_NOUN = (r"facilit(?:y|ies)|loans?|borrowers?|customers?|suppliers?|vendors?|covenants?|quarters?|months?|"
               r"years?|weeks?|periods?|amendments?|waivers?|exceptions?|items?|locations?|plants?|sites?|"
               r"statements?|certificates?|documents?|reports?|tests?|signals?|lenders?|guarantors?|subsidiar(?:y|ies)|"
               r"segments?|contracts?|accounts?|occasions?|instances?|reasons?|factors?|sections?|parties|owners?|"
               r"members?|directors?|officers?|employees?|products?|lines?|projects?|properties|payments?|draws?|totals?")
_COUNT_ADJECTIVE = (r"consecutive|largest|major|principal|main|key|new|open|remaining|prior|previous|next|last|past|"
                    r"additional|other|separate|straight|successive|fiscal|calendar|interim|reporting|financial|"
                    r"compliance|late|missed|scheduled|operating|trailing|bank|template|account|summary|total")
_ALLOWED_COUNT = re.compile(
    rf"^[\s-]+(?:(?:{_COUNT_ADJECTIVE})\s+){{0,3}}(?:{_COUNT_NOUN})\b(?!\s+(?:of\s+)?(?:ebitda|revenue|debt|income|fixed|interest|service|payroll|"
    r"expenses?|sales|purchases|inventory|cover|coverage|liquidity|runway|cash))"
    rf"|^\s+of\s+(?:the|its|their|these|those|them|which)\b", re.I)
# a Roman numeral standing for a number ("leverage is IV times"); after a capitalised word it is
# part of a name ("Article IV", "Phase II")
_ROMAN = re.compile(r"(?<![A-Za-z])(?=[IVX]{2,}\b)X{0,3}(?:IX|IV|V?I{0,3})\b")
_CAPITALISED_BEFORE = re.compile(r"[A-Z][A-Za-z.]*\s+$")
# "page three", "step two": a place in a document or a sequence, not an amount
_LABEL_BEFORE = re.compile(r"\b(?:pages?|sections?|parts?|steps?|phases?|stages?|tiers?|exhibits?|schedules?|"
                           r"appendix|notes?|items?|chapters?|paragraphs?|clauses?)\s+$", re.I)
_CARDINAL_WORD = re.compile(rf"\b(?:{_CARDINAL})\b", re.I)
# "trailing twelve-month revenue", "last twelve-month EBITDA": the name of a measurement window, with the
# number hyphenated onto its unit. It says which period a figure covers and states no amount of anything;
# "twelve months of revenue" and "a six-month runway" are not this form and stay refused.
_WINDOW_BEFORE = re.compile(r"\b(?:trailing|last|latest|rolling|prior|preceding)\s+$", re.I)
_WINDOW_AFTER = re.compile(r"^-(?:month|quarter|year|week)\b(?!s)(?!\s+(?:cover|coverage|liquidity|runway|cash)\b)", re.I)
_OTHER_QUANTITY_WORDS = re.compile(
    r"\b(?:doubled?|doubling|tripled?|tripling|trebled?|trebling|quadrupled?|quintupled?|halved|halving|twice|thrice|\w+fold)\b"
    r"|\b(?:fell|rose|dropped|grew|declined|increased|decreased|climbed|slipped|down|up|by|is|was|are|were)\s+"
    r"(?:nearly\s+|about\s+|roughly\s+|almost\s+)?an?\s+(?:third|quarter|fifth|tenth|eighth)\b"
    r"|\ban?\s+(?:third|quarter|fifth|tenth|eighth)\s+(?:lower|higher|less|more|below|above|of)\b"
    r"|\b(?:teens|twenties|thirties|forties|fifties|sixties|seventies|eighties|nineties)\b"
    r"|\b(?:one|two|three|four|five|six|seven|eight|nine|ten)-to-(?:one|two|three|four|five)\b"
    r"|\bcouple\s+of\s+(?:turns?|times|points?|percent|hundred|thousand|million|billion)\b"
    r"|\((?:usd|us\$|\$)\s*(?:000s?|thousands?|millions?|mm|m|k)\)"
    r"|\b(?<!first\s)(?<!second\s)(?<!latter\s)(?<!first-)(?<!second-)hal(?:f|ves)\b"
    r"|\b(?:by|nearly|about|roughly|almost|around|approximately|over|under)\s+(?:a|one|two|three)[\s-](?:thirds?|quarters?|fifths?|tenths?)\b"
    r"|\b(?:a|one|two|three)[\s-](?:thirds?|quarters?|fifths?|tenths?)\s+of\b"
    r"|\b(?:one|two|three|four)-(?:thirds?|fifths?|tenths?)\b"
    r"|\b(?:one|two|three|four)-quarters?\b(?!\s+(?:basis|period|window|test|measurement|average|trailing|rolling)\b)"
    r"|\b(?:single|double|triple)[\s-]digits?\b|\b(?:tens|hundreds|thousands|millions|billions)\s+of\b"
    # "seven figures", "a six-figure loss", "high single figures": a size stated in words. Any other word before
    # "figures" ("the certificate figures", "reported figures") names figures and states none.
    rf"|\b(?:{_CARDINAL}|one|low|mid|high|upper|lower|several|multi|single|double|triple)[\s-]figures?\b"
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
    r"percentage\s+points?|points?|pts|bps|basis\s+points?|times|turns?|x)\b"
    r"|[-−–]\w|,?\s*(?:stated|expressed|reported|shown|presented|figures|amounts)\b"
    r"|\s+(?:per|each|every)\s+(?:day|week|month|quarter|year|share|unit)\b"
    r"|\s+an?\s+(?:day|week|month|quarter|share|unit)\b|\s+a\s+year\b(?!\s+(?:earlier|ago|before|later|prior)))", re.I)
_BRACKETED_REF = (re.compile(r"\(\s*$"), re.compile(r"^\s*\)"))


_PAGE_TAIL = r"(?![\w]|[.,]\d|\s*(?:percent|%|x\b|times|turns?|thousand|million|billion|bps|basis))"
_PAGE_REF = re.compile(r"(?P<prep>\b(?:on|in|see|from|at)\s+)?\bpages?\s+(?P<n>\d{1,3})" + _PAGE_TAIL, re.I)
# after "pages N": "to M", "through M", "-M" (M above the page before it), "and M", ", M"; one page at a time
_PAGE_MORE = re.compile(r"(?P<sep>\s+(?:to|through|and)\s+|\s*[-\u2013\u2014]\s*|,\s+(?:and\s+)?)(?P<n>\d{1,3})" + _PAGE_TAIL, re.I)
_NOTE_REF = re.compile(r"\bNotes?\s+(?P<n>\d{1,3})" + _PAGE_TAIL)
_ENDING_REF = re.compile(r"\bending\s+(?:in\s+)?(?<![\d,.])(?P<n>\d{4})(?![\w]|[.,]\d|\s*(?:percent|%|x\b|times|thousand|million|billion))", re.I)
# an account's last four digits as a statement prints them: "(ending 9001)", "ending in 9001", "account ... ending
# 9001" on one line, or a masked number ("xxxx9001", "****9001"). A bare "Ending 125000" (a rollforward amount) is
# none of these.
_ENDING_PRINTED = re.compile(
    r"\(\s*ending\s+(?:in\s+)?(\d{4})\s*\)|\bending\s+in\s+(\d{4})\b"
    r"|\b(?:account|acct\.?|a/c|card)\b[^\n]{0,40}?\bending\s+(\d{4})\b(?![,.]?\d)"
    r"|(?:x{2,}|\*{2,}|\u2022{2,})\s?(\d{4})\b(?![,.]?\d)", re.I)
_YEAR_REF = re.compile(r"(?P<lead>\b(?:\w+-(?:month|quarter|year)|comparatives?\s+(?:for|from|of))\s+)(?P<n>20[0-3]\d)\b(?![,.]?\d|\s?%|\s*(?:x\b|thousand|million|billion|percent))", re.I)
# where a reference may stand: opening the text or a clause ("Page 5 (Note 1 - ...)", "(page 5)"), or after
# a preposition that follows the name of a part of a document or a past participle ("rows on page 4",
# "Dividends paid on page 4"). A page after a measure ("leverage on page 5") is not one.
_CLAUSE_START = re.compile(r"(?:^|[.;:(,\u2013\u2014-]\s*|\b(?:in|see|under|per|and|or|of|with)\s+)$", re.I)
_PART_WORD = re.compile(
    r"\b(?:rows?|lines?|columns?|items?|entr(?:y|ies)|schedules?|statements?|tables?|sheets?|listings?|reports?|certificates?|"
    r"pages?|notes?|sections?|components?|accounts?|balances?|rollforwards?|roll-forwards?|\w+ed|paid|shown|set|"
    r"printed|found|given|reported)\s*$|\bnotes?\s+\d{1,3}\s*$|[)'\"\u2019]\s*$", re.I)


@dataclass(frozen=True)
class DocumentStructure:
    """What the printed document says about itself, built by code from its page texts: how many pages
    it has, which note headings are printed, which account endings and which years appear. A note may
    point at a place in the document only if the place exists."""

    page_count: int
    note_numbers: frozenset[int] = frozenset()
    endings: frozenset[str] = frozenset()
    years: frozenset[int] = frozenset()

    @classmethod
    def from_pages(cls, texts: Iterable[str]) -> "DocumentStructure":
        pages = list(texts)
        notes: set[int] = set()
        endings: set[str] = set()
        years: set[int] = set()
        for text in pages:
            for m in re.finditer(r"(?im)^\s*notes?\s+(\d{1,3})\b", text):
                notes.add(int(m.group(1)))
            for m in _ENDING_PRINTED.finditer(text):
                endings.add(next(g for g in m.groups() if g))
            for m in re.finditer(r"\b(20[0-3]\d)\b", text):
                years.add(int(m.group(1)))
        return cls(len(pages), frozenset(notes), frozenset(endings), frozenset(years))


@dataclass(frozen=True)
class References:
    """Places a covenant answer may name, built by code from the run: the version numbers of the
    facility's terms and the section numbers printed in a verified quote or on a page the run read."""

    versions: frozenset[int] = frozenset()
    sections: frozenset[str] = frozenset()


# a version is named with its qualifier: "terms version 2", "approved version 2", "version 2 of the terms"
_VERSION_REF = re.compile(
    r"\b(?:(?:terms|approved)\s+version\s+(?P<n>\d{1,3})\b|version\s+(?P<m>\d{1,3})\s+of\s+the\s+terms\b)"
    r"(?![.,]\d|\s*(?:x\b|%|percent|times|turns?))", re.I)
_SECTION_REF = re.compile(
    r"\b(?:Sections?|§)\s*(?P<n>\d{1,3}(?:\.\d{1,3})*)(?:\([A-Za-z0-9]{1,4}\))*(?![\w]|[.,]\d|%|\s*(?:x\b|percent|times|turns?))")
# heading shapes only: "Section 6.3", "§ 6.3", or a line that opens with a number and then a capitalised word
# ("6.3 Minimum Revenue"). A line that opens with a bare decimal ("3.25 : 1 test") names no section.
_SECTION_PRINTED = re.compile(
    r"(?:\bSections?\s+|§\s*)(\d{1,3}(?:\.\d{1,3})+)(?![\w]|[.,]\d|%)"
    r"|(?m:^)[ \t]*(\d{1,3}(?:\.\d{1,3})+)\.?[ \t]+[A-Z][a-z]")


def sections_printed(text: str) -> set[str]:
    """Section numbers a piece of document text names or heads (6.3, 9.1)."""
    return {m.group(1) or m.group(2) for m in _SECTION_PRINTED.finditer(text)}


def _blank_refs(text: str, refs: References) -> str:
    chars = list(text)
    for pattern, ok in ((_VERSION_REF, lambda g: int(g) in refs.versions), (_SECTION_REF, lambda g: g in refs.sections)):
        for m in pattern.finditer(text):
            groups = m.groupdict()
            if ok(groups.get("n") or groups.get("m")):
                for i in range(m.start(), m.end()):
                    chars[i] = " "
    return "".join(chars)


def _page_run(text: str, m: re.Match[str]) -> list[tuple[int, int]]:
    """The pages a "pages N ..." reference goes on to name, as (page, end offset): "pages 2 to 4", "pages 2, 3 and
    5". Only after the plural, and a span ("to", "through", a dash) must go up."""
    if re.search(r"pages\s+\d", m.group(0), re.I) is None:
        return []
    found: list[tuple[int, int]] = []
    last, at = int(m.group("n")), m.end()
    while (more := _PAGE_MORE.match(text, at)) is not None:
        n = int(more.group("n"))
        if "," not in more.group("sep") and "and" not in more.group("sep").lower() and n <= last:
            break
        found.append((n, more.end()))
        last, at = n, more.end()
    return found


def _blank_structure(text: str, st: DocumentStructure) -> str:
    """Blank the places in a note that point into the document and are true of it. Anything else
    stays for the figure checks to refuse."""
    spans: list[tuple[int, int]] = []
    for m in _PAGE_REF.finditer(text):
        n = int(m.group("n"))
        if not 1 <= n <= st.page_count:
            continue
        before = text[:m.start()]
        if (_PART_WORD.search(before) or _CLAUSE_START.search(before)) if m.group("prep") else _CLAUSE_START.search(before):
            run = _page_run(text, m)
            if all(1 <= page <= st.page_count for page, _ in run):
                spans.append((m.start(), run[-1][1] if run else m.end()))
    for m in _NOTE_REF.finditer(text):
        if int(m.group("n")) in st.note_numbers and _CLAUSE_START.search(text[:m.start()]):
            spans.append((m.start(), m.end()))
    for m in _ENDING_REF.finditer(text):
        if m.group("n") in st.endings:
            spans.append((m.start("n"), m.end("n")))
    for m in _YEAR_REF.finditer(text):
        if int(m.group("n")) in st.years:
            spans.append((m.start("n"), m.end("n")))
    chars = list(text)
    for a, b in spans:
        for i in range(a, b):
            chars[i] = " "
    return "".join(chars)


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
    structure: DocumentStructure | None = None,
    refs: References | None = None,
) -> list[Note]:
    """Findings for a piece of agent text. An empty list means the text may be shown.

    - every reference must be well formed and name a fact in scope;
    - every figure typed outside a reference must match `allowed_figures` (figures from quotes
      the agent cited and constants from approved terms) or a known ratio;
    - `structure` (built by code from the document's own pages) lets a note point at a page, a note
      heading, an account ending or a comparative year that the document really has;
    - `refs` (built by code from the terms versions and the pages the run read) lets text name a terms
      version or a section number that exists;
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
        # an amount of money in brackets reads as a negative; a ratio, percentage or count does not
        bracketed = (_BRACKETED_REF[0].search(before) and _BRACKETED_REF[1].match(after)
                     and (fid not in facts or facts[fid].unit == "usd"))
        if _BEFORE_REF.search(before) or _AFTER_REF.match(after) or bracketed:
            notes.append(Note("narrative", "reference_joined", "retry",
                              f"text is joined onto {token} and would change the figure it shows"))
    # everything outside the references, with compatibility forms folded (full-width and
    # superscript digits read as digits)
    ratios = list(known_ratios)
    outside = unicodedata.normalize("NFKC", _ANY_REF.sub(lambda m: " " * len(m.group(0)), text))
    if refs is not None:
        outside = _blank_refs(outside, refs)
    if structure is not None:
        # a page the document does not have is refused, whatever else allows a page number
        for m in _PAGE_REF.finditer(outside):
            for page in (int(m.group("n")), *(n for n, _ in _page_run(outside, m))):
                if not 1 <= page <= structure.page_count:
                    notes.append(Note("narrative", "figure_untraceable", "retry",
                                      "a page was named that the document does not have", subject=str(page)))
        outside = _blank_structure(outside, structure)
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
                if not _ALLOWED_COUNT.match(outside[m.end():]) and not _LABEL_BEFORE.search(outside[:m.start()])
                and not (_WINDOW_AFTER.match(outside[m.end():]) and _WINDOW_BEFORE.search(outside[:m.start()]))
                and not re.search(r"\d\s?$", outside[:m.start()])]  # "51.3 million" is already reported as a figure
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
