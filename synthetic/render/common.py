"""Shared pieces for the PDF renderers: page template, footer, number formats, text extraction."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from xml.sax.saxutils import escape

import pymupdf
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import BaseDocTemplate, Flowable, Frame, PageTemplate, Paragraph

MARKER = "SYNTHETIC - FOR DEMONSTRATION"
D = Decimal
RULE = colors.Color(0.25, 0.25, 0.25)
SOFT = colors.Color(0.55, 0.55, 0.55)


def style(name: str, font: str = "Helvetica", size: float = 9.5, leading: float | None = None, **kw) -> ParagraphStyle:
    return ParagraphStyle(name, fontName=font, fontSize=size, leading=leading or size * 1.35, **kw)


BODY = style("body", spaceAfter=7)
SMALL = style("small", size=8, textColor=SOFT, spaceAfter=4)
TITLE = style("title", "Helvetica-Bold", 13, spaceAfter=3)
SUBTITLE = style("subtitle", size=10, spaceAfter=2)
HEADING = style("heading", "Helvetica-Bold", 10.5, spaceBefore=8, spaceAfter=5)
COVER_TITLE = style("cover_title", "Helvetica-Bold", 20, 26, alignment=TA_CENTER, spaceAfter=10)
COVER_LINE = style("cover_line", size=12, leading=18, alignment=TA_CENTER, spaceAfter=4)


def para(text: str, st: ParagraphStyle = BODY) -> Paragraph:
    return Paragraph(escape(text), st)


class Mark(Flowable):
    """A zero-size flowable that records the page it lands on."""

    def __init__(self, registry: dict, key) -> None:
        super().__init__()
        self.registry, self.key = registry, key
        self.width = self.height = 0

    def wrap(self, available_width, available_height):
        return 0, 0

    def draw(self) -> None:
        self.registry[self.key] = self.canv.getPageNumber()


class _Document(BaseDocTemplate):
    def __init__(self, path: Path, title: str, footer_left: str, author: str, margin: float) -> None:
        super().__init__(
            str(path),
            pagesize=letter,
            leftMargin=margin,
            rightMargin=margin,
            topMargin=0.85 * inch,
            bottomMargin=0.95 * inch,
            title=title,
            author=author,
            subject=MARKER,
            invariant=1,
        )
        self.footer_left = footer_left
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="body",
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)  # fmt: skip
        self.addPageTemplates([PageTemplate(id="page", frames=[frame], onPage=self._footer)])

    def _footer(self, canvas, doc) -> None:
        canvas.saveState()
        left, right = self.leftMargin, self.pagesize[0] - self.rightMargin
        y = 0.6 * inch
        canvas.setStrokeColor(SOFT)
        canvas.setLineWidth(0.4)
        canvas.line(left, y + 11, right, y + 11)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(SOFT)
        canvas.drawString(left, y, self.footer_left)
        canvas.drawRightString(right, y, f"Page {doc.page}")
        canvas.setFont("Helvetica-Bold", 7.5)
        canvas.drawCentredString((left + right) / 2, y - 11, MARKER)
        canvas.restoreState()


def build_pdf(path: Path, title: str, footer_left: str, author: str, story: list, margin: float = 0.9 * inch) -> int:
    """Render a story to `path` and return the page count."""
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = _Document(path, title, footer_left, author, margin)
    doc.build(story)
    return doc.page


def content_width(margin: float = 0.9 * inch) -> float:
    return letter[0] - 2 * margin


# --------------------------------------------------------------------------- number formats


def scaled(value: Decimal, scale: int) -> Decimal:
    """Truth value expressed in the document's scale. Truth is always a whole multiple of the scale."""
    quotient = value / scale
    if quotient != quotient.to_integral_value():
        raise ValueError(f"{value} is not a whole multiple of {scale}")
    return quotient.to_integral_value()


def accounting(units: Decimal) -> str:
    """Accounting format: thousands separators, parentheses for negatives, a dash for zero."""
    if units == 0:
        return "-"
    text = f"{abs(int(units)):,}"
    return f"({text})" if units < 0 else text


def amount(value: Decimal, scale: int, sign: int = 1) -> str:
    return accounting(scaled(value, scale) * sign)


def money(value: Decimal) -> str:
    text = f"${abs(int(value)):,}"
    return f"({text})" if value < 0 else text


def ratio(value: Decimal) -> str:
    return f"{value:.2f}x"


def scale_note(scale: int) -> str:
    return "(in thousands of U.S. dollars)" if scale == 1000 else "(in U.S. dollars)"


# --------------------------------------------------------------------------- reading PDFs back


def page_texts(path: Path) -> list[str]:
    with pymupdf.open(path) as pdf:
        return [page.get_text() for page in pdf]


def squash(text: str) -> str:
    return " ".join(text.split())


def drop_page(path: Path, page_number: int) -> None:
    """Remove one page (1-based), as if it was left out of the scan."""
    with pymupdf.open(path) as pdf:
        keep = [i for i in range(pdf.page_count) if i != page_number - 1]
        pdf.select(keep)
        data = pdf.tobytes(garbage=3, deflate=True, no_new_id=True)
    path.write_bytes(data)


def rasterize_page(path: Path, page_number: int) -> None:
    """Replace one page (1-based) with a picture of itself, so it has no text layer."""
    with pymupdf.open(path) as source:
        page = source[page_number - 1]
        picture = page.get_pixmap(dpi=110, colorspace=pymupdf.csGRAY)
        rect = page.rect
        out = pymupdf.open()
        if page_number > 1:
            out.insert_pdf(source, from_page=0, to_page=page_number - 2)
        blank = out.new_page(width=rect.width, height=rect.height)
        blank.insert_image(blank.rect, pixmap=picture)
        if page_number < source.page_count:
            out.insert_pdf(source, from_page=page_number, to_page=source.page_count - 1)
        data = out.tobytes(garbage=3, deflate=True, no_new_id=True)
        out.close()
    path.write_bytes(data)
