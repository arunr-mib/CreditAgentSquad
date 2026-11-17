"""Check that text an agent says it read is really on the page it cites.

A page is a list of words with boxes: [x0, y0, x1, y1, "word"], in reading order, in PDF points.
Pure code: no I/O. The model's own number is never trusted; the figure is parsed from the page.
"""
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
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


@dataclass(frozen=True)
class CellCheck:
    status: str  # verified | unparseable | not_found | label_mismatch | column_unconfirmed | ambiguous
    value: Decimal | None = None
    unit: str = ""
    bbox: Box | None = None
    occurrences: int = 0
    detail: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "verified"


def verify_cell(
    words: Sequence[Word],
    *,
    printed_figure: str,
    printed_label: str | None = None,
    column_header: str | None = None,
) -> CellCheck:
    """Verify one statement cell: the figure as printed, on the row of its label, under its column.

    Returns the value parsed from the printed text. Anything unclear is refused with a reason.
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

    if column_header is not None:
        headers = locate(words, column_header)
        in_column = [c for c in candidates if any(column_aligned(c.bbox, h.bbox) for h in headers)]
        if not in_column:
            return CellCheck("column_unconfirmed", value=parsed.value, unit=parsed.unit,
                             bbox=candidates[0].bbox, occurrences=len(candidates),
                             detail=f"cannot confirm {printed_figure!r} sits under {column_header!r}")
        candidates = in_column

    if len(candidates) > 1 and printed_label is not None and column_header is not None:
        return CellCheck("ambiguous", value=parsed.value, unit=parsed.unit, bbox=candidates[0].bbox,
                         occurrences=len(candidates), detail="more than one matching cell")
    return CellCheck("verified", value=parsed.value, unit=parsed.unit, bbox=candidates[0].bbox,
                     occurrences=len(candidates))


def _prose(text: str) -> str:
    folded = unicodedata.normalize("NFKC", text).translate(_FOLD)
    return re.sub(r"\s+", " ", folded).strip().lower()


def quote_on_page(page_text: str, quote: str) -> bool:
    """True when the quote appears verbatim on the page, ignoring line breaks, case and
    typographic variants of quotes and dashes. An empty quote is never verified."""
    q = _prose(quote)
    return bool(q) and q in _prose(page_text)


def number_in_quote(value: Decimal, quote: str, known_ratios: Sequence[Decimal] = ()) -> bool:
    """True when the quote states this number (a percentage may be given as 85% for 0.85)."""
    for fig in extract_figures(quote, known_ratios):
        if same_number(fig.value, value) or same_number(abs(fig.value), abs(value)):
            return True
        if fig.kind == "percent" and same_number(fig.value / Decimal(100), value):
            return True
    return False
