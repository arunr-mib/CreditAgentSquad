"""Check that text an agent says it read is really on the page it cites.

A page is a list of words with boxes: [x0, y0, x1, y1, "word"], in reading order, in PDF points.
Pure code: no I/O. The model's own number is never trusted; the figure is parsed from the page.
"""
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.guardrails.numbers import extract_figures, parse_printed_figure, same_number

Word = Sequence  # [x0, y0, x1, y1, text]
Box = tuple[float, float, float, float]
_MAX_WORDS = 40
_CURRENCY = str.maketrans("", "", "$£€")
_FOLD = str.maketrans({
    "‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-",
    "−": "-", " ": " ",
})


def _squash(text: str) -> str:
    """Remove whitespace and currency signs, fold typographic quotes and dashes."""
    return "".join(unicodedata.normalize("NFKC", text).translate(_FOLD).translate(_CURRENCY).split())


@dataclass(frozen=True)
class Located:
    bbox: Box
    first: int
    last: int


def locate(words: Sequence[Word], printed: str) -> list[Located]:
    """Every place where `printed` appears as a run of whole words on the page."""
    target = _squash(printed)
    if not target:
        return []
    squashed = [_squash(str(w[4])) for w in words]
    found: list[Located] = []
    for i in range(len(words)):
        acc = ""
        for j in range(i, min(i + _MAX_WORDS, len(words))):
            acc += squashed[j]
            if not acc:
                continue  # a word that was only a currency sign
            if acc == target:
                if squashed[i] == "" and i + 1 <= j:
                    break  # the same run will be found starting at the next word
                xs0 = min(float(words[k][0]) for k in range(i, j + 1))
                ys0 = min(float(words[k][1]) for k in range(i, j + 1))
                xs1 = max(float(words[k][2]) for k in range(i, j + 1))
                ys1 = max(float(words[k][3]) for k in range(i, j + 1))
                found.append(Located((xs0, ys0, xs1, ys1), i, j))
                break
            if not target.startswith(acc):
                break
    return found


def same_row(a: Box, b: Box) -> bool:
    overlap = min(a[3], b[3]) - max(a[1], b[1])
    return overlap >= 0.5 * min(a[3] - a[1], b[3] - b[1])


def _inside(inner: Box, outer: Box, slack: float = 1.0) -> bool:
    return (inner[0] >= outer[0] - slack and inner[1] >= outer[1] - slack
            and inner[2] <= outer[2] + slack and inner[3] <= outer[3] + slack)


def column_aligned(figure: Box, header: Box, tolerance: float = 12.0) -> bool:
    """A figure belongs to a column when it sits under the header: boxes overlap sideways, or
    their right edges or centres line up within the tolerance."""
    if figure[1] < header[1] - 1.0:
        return False  # the figure is above the header
    overlap = min(figure[2], header[2]) - max(figure[0], header[0])
    if overlap > 0:
        return True
    centre_f, centre_h = (figure[0] + figure[2]) / 2, (header[0] + header[2]) / 2
    return abs(figure[2] - header[2]) <= tolerance or abs(centre_f - centre_h) <= tolerance


def row_label(words: Sequence[Word], figure: Box, label_gap: float | None = None) -> str:
    """The label of the row a figure sits on, read from the page by code: the words on the same
    row to the left of the figure, without the cells of other columns. The reader's own choice
    of label text is never used for this, because a reader can pick a fragment that hides what
    the row is ("net of current portion" for long-term debt).

    A number inside the label ("invoices more than 90 days past invoice date", "term loan due
    2027") belongs to it: it follows the word before it at an ordinary word space. A cell of
    another column stands apart from what precedes it.
    """
    left = sorted((w for w in words
                   if same_row((float(w[0]), float(w[1]), float(w[2]), float(w[3])), figure)
                   and float(w[2]) <= figure[0] + 1.0), key=lambda w: float(w[0]))
    if label_gap is not None:
        left = _first_cell(left, label_gap * (figure[3] - figure[1]))
    end = len(left)
    while end > 0:
        text = str(left[end - 1][4]).strip()
        gap = float(left[end - 1][0]) - float(left[end - 2][2]) if end > 1 else _CELL_GAP + 1
        is_cell = text in _DASH_CELLS or text in "$£€" or parse_printed_figure(text) is not None
        after_sign = end > 1 and str(left[end - 2][4]).strip() in ("$", "£", "€")
        if is_cell and (gap > _CELL_GAP or after_sign or text in "$£€" or text in _DASH_CELLS):
            end -= 1
            continue
        break
    label = [str(w[4]).strip() for w in left[:end]]
    return " ".join(t for t in label if any(ch.isalnum() for ch in t))


_INDEX_CELL = re.compile(r"^(?:\(?\d{1,2}\)?\.?|\(?[A-Za-z]\)|[A-Za-z]\.)$")


def _first_cell(left: list, gap: float) -> list:
    """The first cell of a row's words, split at gaps wider than `gap`; an index cell is skipped."""
    cells: list[list] = [[left[0]]] if left else []
    for prev, word in zip(left, left[1:], strict=False):
        if float(word[0]) - float(prev[2]) > gap:
            cells.append([])
        cells[-1].append(word)
    for position, cell in enumerate(cells):
        if len(cell) == 1 and _INDEX_CELL.match(str(cell[0][4]).strip()) and position + 1 < len(cells):
            continue
        return cell
    return left


_CELL_GAP = 8.0  # points: a figure set further than this from the word before it is a column cell
_DASH_CELLS = {"-", "—", "–", "−"}


# ---- which column is the period: decided from the page, never from what the reader reports ----

_MONTH_NAMES = ("january", "february", "march", "april", "may", "june", "july", "august", "september",
                "october", "november", "december")
_LONG_DATE = re.compile(r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b")
_SLASH_DATE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
_MONTH_DAY = re.compile(r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?\b")
_YEAR_TOKEN = re.compile(r"(?<![\d,.$])\b((?:19|20)\d{2})\b(?![\d,.%])")
_WORD_MONTHS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
                "nine": 9, "ten": 10, "eleven": 11, "twelve": 12}
_NUMBER_WORDS = "|".join(_WORD_MONTHS)
_DURATION = re.compile(
    r"\b(" + _NUMBER_WORDS + r"|\d{1,2})[\s-]+months?(?:\s+period)?\s+end(?:ed|ing)\b"
    r"|\b(quarter|year)s?\s+end(?:ed|ing)\b"
    r"|\b(?:the\s+)?(month)\s+(?:end(?:ed|ing)\b|of\b)", re.I)
_DURATION_MONTHS = {**_WORD_MONTHS, **{str(n): n for n in range(1, 13)}, "quarter": 3, "year": 12, "month": 1}
# words a column header may carry besides its date and still be the period's own column
_HEADER_WORDS = re.compile(
    r"\b(?:un)?audited\b|\bactual\b|\bas\s+of\b|\bat\b|\bfor\s+the\b|\bperiod\b|\bended\b|\bending\b|"
    r"\byear[\s-]to[\s-]date\b|\bytd\b|\bfiscal\b|\byears?\b|\bquarters?\b|\bmonths?\b|\bthe\b|[(),.:$]|"
    r"\bin\s+thousands\b|\b(?:" + _NUMBER_WORDS + r")\b", re.I)
_ALIGN = 3.0       # points: right edges this close are one column
_INDENT = 40.0     # points: a row starting this close to the label margin is a label row, not a header
_RUN_GAP = 12.0    # points: a wider gap between words starts a new header phrase


def _month(name: str) -> int | None:
    key = name.lower()[:3]
    return next((i for i, full in enumerate(_MONTH_NAMES, start=1) if full.startswith(key)), None) if len(key) == 3 else None


def dates_in(text: str) -> list[date]:
    """Dates written out in the text ("September 30, 2026", "Sept. 30, 2026", "9/30/2026")."""
    found: list[date] = []
    for name, day, year in _LONG_DATE.findall(text):
        month = _month(name)
        if month is not None:
            try:
                found.append(date(int(year), month, int(day)))
            except ValueError:
                pass
    for month, day, year in _SLASH_DATE.findall(text):
        try:
            found.append(date(int(year), int(month), int(day)))
        except ValueError:
            pass
    return found


def durations_in(text: str) -> set[int]:
    """Lengths of period the text states, in months ("nine months ended", "year ended")."""
    return {_DURATION_MONTHS[(a or b or c).lower()] for a, b, c in _DURATION.findall(text)
            if (a or b or c).lower() in _DURATION_MONTHS}


def _box(word: Word) -> Box:
    return float(word[0]), float(word[1]), float(word[2]), float(word[3])


def _is_figure(text: str) -> bool:
    return parse_printed_figure(text) is not None


def _rows(words: Sequence[Word]) -> list[list[Word]]:
    rows: list[list[Word]] = []
    for word in sorted(words, key=lambda w: (float(w[1]), float(w[0]))):
        for row in rows:
            if same_row(_box(row[0]), _box(word)):
                row.append(word)
                break
        else:
            rows.append([word])
    return [sorted(row, key=lambda w: float(w[0])) for row in rows]


def column_for_period(words: Sequence[Word], figure: Box, period_end: date, months: int = 0) -> str | None:
    """None when the figure sits in the one column whose own header names `period_end` (and, for
    a flow, a period of `months`); otherwise the reason it cannot be placed.

    The columns are the figures on the figure's own row. Each column's header is read from the
    rows above the table that carry no row label: text standing over one column belongs to it,
    text standing over several belongs to all of them, and titles are context. A column is the
    period when its own header gives the date, or gives the year under a title or spanning
    header that gives the month and day. Two columns for the same date ("three months ended",
    "nine months ended") are told apart by the length of period, or not at all.
    """
    rows = _rows(words)
    row = next((r for r in rows if any(same_row(_box(w), figure) for w in r)), None)
    if row is None:
        return "the figure's row could not be read"
    margin = float(row[0][0])
    # the columns are those of the whole page, not of this row alone: a row with one cell blank
    # would otherwise look like a one-column table
    # (taken from rows that carry at least two figures, so a year in a title is not a column)
    columns = sorted({round(float(w[2]), 1) for r in rows
                      if float(r[0][0]) <= margin + _INDENT and not _is_figure(str(r[0][4]))
                      and sum(1 for w in r[1:] if _is_figure(str(w[4]))) >= 2
                      for w in r[1:] if _is_figure(str(w[4])) and float(w[0]) > margin + 1}
                     | {round(float(w[2]), 1) for w in row if _is_figure(str(w[4])) and float(w[0]) > margin + 1})
    merged: list[float] = []
    for edge in columns:
        if not merged or edge - merged[-1] > _ALIGN:
            merged.append(edge)
    columns = merged
    mine = next((i for i, edge in enumerate(columns) if abs(edge - figure[2]) <= _ALIGN), None)
    if mine is None:
        return "the figure is not in a column of figures"

    def labelled(r: list[Word]) -> bool:
        return float(r[0][0]) <= margin + _INDENT

    def aligned(w: Word) -> int | None:
        return next((i for i, edge in enumerate(columns) if abs(float(w[2]) - edge) <= _ALIGN), None)

    lefts = {i: edge for i, edge in enumerate(columns)}
    for r in rows:
        if not labelled(r) or _is_figure(str(r[0][4])):
            continue
        for w in r[1:]:
            i = aligned(w)
            if i is not None and _is_figure(str(w[4])):
                lefts[i] = min(lefts[i], float(w[0]))
    bands = [(lefts[i] - 6.0, columns[i] + _ALIGN) for i in range(len(columns))]

    own = ["" for _ in columns]
    spanning = ["" for _ in columns]
    context: list[str] = []   # titles and loose text, nearest first
    headings: list[str] = []  # titles between the figure and its column headers: they head its block
    above = [r for r in rows if float(r[0][3]) <= figure[1] + 1.0 and not any(same_row(_box(w), figure) for w in r)]
    collecting, done = False, False
    for r in reversed(above):  # nearest row first
        if labelled(r):
            if collecting:
                done = True  # the header block of this table has ended; everything further up is context
            if not any(_is_figure(str(w[4])) and aligned(w) is not None for w in r[1:]):
                text = " ".join(str(w[4]) for w in r)  # a title; rows of figures are not context
                context.append(text)
                if not collecting:
                    headings.append(text)
            continue
        if done:
            context.append(" ".join(str(w[4]) for w in r))
            continue
        runs: list[list[Word]] = []
        for w in r:
            if runs and float(w[0]) - float(runs[-1][-1][2]) <= _RUN_GAP:
                runs[-1].append(w)
            else:
                runs.append([w])
        if not collecting and not any(float(run[-1][2]) > left and float(run[0][0]) < right
                                      for run in runs for left, right in bands):
            # a sub-heading set in from the margin, over no column: it heads a section of the
            # table, not a column
            text = " ".join(str(w[4]) for w in r)
            context.append(text)
            headings.append(text)
            continue
        collecting = True
        for run in runs:
            x0, x1, text = float(run[0][0]), float(run[-1][2]), " ".join(str(w[4]) for w in run)
            over = [i for i, (left, right) in enumerate(bands) if x1 > left and x0 < right]
            if len(over) == 1:
                own[over[0]] = f"{text} {own[over[0]]}".strip()  # rows are visited bottom-up
            elif over:
                for i in over:
                    spanning[i] = f"{text} {spanning[i]}".strip()
            else:
                context.append(text)
    # What stands nearest above a figure governs it. A heading between the figure and its column
    # headers ("Three months ended ...", or the prior year's block stacked under the current
    # one) heads the block the figure is in, whatever the top of the page says.
    for text in headings:
        stated_dates, stated_lengths = dates_in(text), durations_in(text)
        if stated_dates and period_end not in stated_dates:
            return "the figure sits under a heading for a different date"
        if months and stated_lengths and months not in stated_lengths:
            return "the figure sits under a heading for a different length of period"
        if stated_dates or stated_lengths:
            break
    dated_title = next((t for t in context if dates_in(t) or _MONTH_DAY.search(t)), "")
    length_title = next((t for t in context if durations_in(t)), "")

    def is_period(i: int) -> bool:
        # a column headed budget, forecast, pro forma, restated or variance is not the period's
        # figures, whatever date stands over it
        leftover = _HEADER_WORDS.sub(" ", _LONG_DATE.sub(" ", _SLASH_DATE.sub(" ", _DURATION.sub(" ", own[i]))))
        if re.search(r"[A-Za-z%]", _YEAR_TOKEN.sub(" ", leftover)):
            return False
        own_dates = dates_in(own[i])
        if own_dates:
            return set(own_dates) == {period_end}
        around = f"{spanning[i]} {dated_title}"
        years = {int(y) for y in _YEAR_TOKEN.findall(own[i])}
        if years:
            month_days = {(_month(name), int(day)) for name, day in _MONTH_DAY.findall(around)}
            return years == {period_end.year} and (period_end.month, period_end.day) in month_days
        if own[i].strip():
            return False  # a header that is neither a date nor a year: not understood
        return len(columns) == 1 and period_end in dates_in(around)

    def length_fits(i: int) -> bool | None:
        """True or False when the column's header states a length of period; None when silent."""
        stated = durations_in(f"{spanning[i]} {own[i]}")
        return None if not stated else stated == {months}

    dated = [i for i in range(len(columns)) if is_period(i)]
    if months:
        if any(length_fits(i) is False for i in dated if i == mine):
            return "the column is for a different length of period than the one requested"
        fitting = [i for i in dated if length_fits(i) is not False]
        if len(fitting) > 1:
            stated = [i for i in fitting if length_fits(i)]
            fitting = stated if len(stated) == 1 else fitting
        dated = fitting
        if dated == [mine] and length_fits(mine) is None:
            in_title = durations_in(length_title)
            if in_title and months not in in_title:
                return "the page is for a different length of period than the one requested"
    if not dated:
        return f"no column on the page is headed {period_end:%B %-d, %Y}"
    if len(dated) > 1:
        return f"more than one column is headed {period_end:%B %-d, %Y} and they cannot be told apart"
    if dated != [mine]:
        return f"the figure is not in the column headed {period_end:%B %-d, %Y}"
    return None


@dataclass(frozen=True)
class CellCheck:
    status: str  # verified | unparseable | not_found | label_mismatch | column_unconfirmed | ambiguous
    value: Decimal | None = None
    unit: str = ""
    bbox: Box | None = None
    occurrences: int = 0
    detail: str = ""
    row_label: str = ""  # the row's label as code read it from the page

    @property
    def ok(self) -> bool:
        return self.status == "verified"


def verify_cell(
    words: Sequence[Word],
    *,
    printed_figure: str,
    printed_label: str | None = None,
    column_header: str | None = None,
    column_anchor: str | None = None,
    period_end: date | None = None,
    months: int = 0,
    label_gap: float | None = None,
) -> CellCheck:
    """Verify one statement cell: the figure as printed, on the row of its label, under its column.

    Returns the value parsed from the printed text. Anything unclear is refused with a reason.
    `column_anchor` is the part of the header that fixes the column (the period's date); when
    given, the figure must sit under that, not merely under a header wide enough to span two
    columns.
    """
    parsed = parse_printed_figure(printed_figure)
    if parsed is None:
        return CellCheck("unparseable", detail=f"cannot read {printed_figure!r} as one figure")
    candidates = locate(words, printed_figure)
    if not candidates:
        return CellCheck("not_found", detail=f"{printed_figure!r} is not on the cited page")

    if printed_label is not None:
        labels = locate(words, printed_label)
        if not labels:
            return CellCheck("label_mismatch", detail=f"label {printed_label!r} is not on the cited page")
        on_row = [c for c in candidates
                  if any(same_row(c.bbox, lab.bbox) and c.bbox[0] >= lab.bbox[2] - 2.0 for lab in labels)]
        if not on_row:
            return CellCheck("label_mismatch", occurrences=len(candidates),
                             detail=f"{printed_figure!r} is not on the row labelled {printed_label!r}")
        candidates = on_row

    if period_end is not None:
        # the column is decided from the page; the header the reader reported plays no part
        reasons = {c.first: column_for_period(words, c.bbox, period_end, months) for c in candidates}
        in_column = [c for c in candidates if reasons[c.first] is None]
        if not in_column:
            return CellCheck("column_unconfirmed", value=parsed.value, unit=parsed.unit, bbox=candidates[0].bbox,
                             occurrences=len(candidates), detail=reasons[candidates[0].first] or "")
        candidates = in_column
    elif column_header is not None:
        headers = locate(words, column_header)
        if column_anchor is not None and headers:
            anchors = locate(words, column_anchor)
            headers = [a for a in anchors if any(_inside(a.bbox, h.bbox) for h in headers)]
        in_column = [c for c in candidates if any(column_aligned(c.bbox, h.bbox) for h in headers)]
        if not in_column:
            return CellCheck("column_unconfirmed", value=parsed.value, unit=parsed.unit,
                             bbox=candidates[0].bbox, occurrences=len(candidates),
                             detail=f"cannot confirm {printed_figure!r} sits under {column_header!r}")
        candidates = in_column

    if len(candidates) > 1 and printed_label is not None:
        # the same figure on two rows whose labels share words ("Inventory availability" and
        # "Inventory availability before sublimit"): the row whose whole label was reported wins
        exact = [c for c in candidates
                 if _squash(row_label(words, c.bbox, label_gap)).lower() == _squash(printed_label).lower()]
        candidates = exact or candidates
    label = row_label(words, candidates[0].bbox, label_gap)
    if len(candidates) > 1 and printed_label is not None and (column_header is not None or period_end is not None):
        return CellCheck("ambiguous", value=parsed.value, unit=parsed.unit, bbox=candidates[0].bbox,
                         occurrences=len(candidates), detail="more than one matching cell", row_label=label)
    return CellCheck("verified", value=parsed.value, unit=parsed.unit, bbox=candidates[0].bbox,
                     occurrences=len(candidates), row_label=label)


def _prose(text: str) -> str:
    folded = unicodedata.normalize("NFKC", text).translate(_FOLD)
    return re.sub(r"\s+", " ", folded).strip().lower()


def quote_on_page(page_text: str, quote: str) -> bool:
    """True when the quote appears verbatim on the page, ignoring line breaks, case and
    typographic variants of quotes and dashes. An empty quote is never verified."""
    q, text = _prose(quote), _prose(page_text)
    if not q:
        return False
    start = text.find(q)
    while start != -1:
        if _whole(text, start, start + len(q)):
            return True
        start = text.find(q, start + 1)
    return False


def _whole(text: str, start: int, end: int) -> bool:
    """The match does not begin or end inside a word or a number: "0 to 1.00" is not a quote of
    "1.20 to 1.00", and "2,000,000" is not a quote of "12,000,000"."""
    before, after = text[start - 1] if start else " ", text[end] if end < len(text) else " "
    first, last = text[start], text[end - 1]
    if first.isalnum() and (before.isalnum() or (first.isdigit() and before in ".," and start >= 2 and text[start - 2].isdigit())):
        return False
    if last.isalnum() and (after.isalnum() or (last.isdigit() and after in ".," and end + 1 < len(text) and text[end + 1].isdigit())):
        return False
    return True


def number_in_quote(value: Decimal, quote: str, known_ratios: Sequence[Decimal] = ()) -> bool:
    """True when the quote states this number (a percentage may be given as 85% for 0.85)."""
    for fig in extract_figures(quote, known_ratios):
        if same_number(fig.value, value) or same_number(abs(fig.value), abs(value)):
            return True
        if fig.kind == "percent" and same_number(fig.value / Decimal(100), value):
            return True
    return False
