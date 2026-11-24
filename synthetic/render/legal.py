"""Credit agreements and amendments. Every section is numbered so clauses can be cited.

A paragraph that carries a cited sentence is kept on one page, and the page it lands on
is recorded, so a citation's page number is always the page the quote is printed on.
"""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import inch
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, Spacer, Table, TableStyle

from synthetic.render import common
from synthetic.render.common import RULE, Mark, style
from synthetic.scenarios import LENDER
from synthetic.terms import LegalDoc, Para, long_date

FONT, BOLD = "Times-Roman", "Times-Bold"
BODY = style("legal_body", FONT, 11, 15.4, spaceAfter=8)
INDENT = style("legal_indent", FONT, 11, 15.4, spaceAfter=8, leftIndent=26)
CENTER = style("legal_center", FONT, 11, 15.4, alignment=TA_CENTER, spaceAfter=6)
ARTICLE = style("legal_article", BOLD, 11.5, 16, alignment=TA_CENTER, spaceBefore=12, spaceAfter=9)
COVER = style("legal_cover", BOLD, 22, 28, alignment=TA_CENTER, spaceAfter=14)
COVER_LINE = style("legal_cover_line", FONT, 13, 20, alignment=TA_CENTER, spaceAfter=6)
TOC = style("legal_toc", FONT, 10.5, 14, leftIndent=26)
TOC_ARTICLE = style("legal_toc_article", BOLD, 10.5, 14, spaceBefore=7)
MARGIN = 1.15 * inch


def _paragraph(p: Para, registry: dict, prefix: str = ""):
    st = {"indent": INDENT, "center": CENTER}.get(p.style, BODY)
    flowable = Paragraph(prefix + escape(p.text), st)
    if not p.anchors:
        return flowable
    return KeepTogether([Mark(registry, p.anchors), flowable])


def render_legal(path: Path, doc: LegalDoc, borrower_name: str) -> dict:
    """Render an agreement or amendment. Returns the page count and the page of every citation anchor."""
    registry: dict = {}
    story: list = []
    if doc.toc:
        story += [
            Spacer(1, 1.7 * inch),
            Paragraph(escape(doc.title), COVER),
            Paragraph(escape(doc.subtitle), COVER_LINE),
            Spacer(1, 0.5 * inch),
            Paragraph("between", COVER_LINE),
            Paragraph(escape(doc.borrower_name), style("party", BOLD, 15, 22, alignment=TA_CENTER, spaceAfter=6)),
            Paragraph("as Borrower", COVER_LINE),
            Spacer(1, 0.2 * inch),
            Paragraph("and", COVER_LINE),
            Paragraph(escape(LENDER), style("party2", BOLD, 15, 22, alignment=TA_CENTER, spaceAfter=6)),
            Paragraph("as Lender", COVER_LINE),
            PageBreak(),
            Paragraph("TABLE OF CONTENTS", ARTICLE),
        ]
        for article in doc.articles:
            story.append(Paragraph(escape(f"ARTICLE {article.number}  {article.title}"), TOC_ARTICLE))
            for section in article.sections:
                story.append(Paragraph(escape(f"{section.number}  {section.title}"), TOC))
        story.append(Paragraph("EXHIBITS AND SCHEDULES", TOC_ARTICLE))
        for heading, _, _ in doc.exhibits:
            story.append(Paragraph(escape(heading.title().replace(" - ", " - ")), TOC))
        story.append(PageBreak())
    story.append(Paragraph(escape(doc.title), ARTICLE))
    for p in doc.preamble:
        story.append(_paragraph(p, registry))
    for article in doc.articles:
        if article.number:
            story.append(Paragraph(escape(f"ARTICLE {article.number}"), ARTICLE))
            story.append(Paragraph(escape(article.title), style("article_title", BOLD, 11.5, 16, alignment=TA_CENTER, spaceAfter=10)))
        for section in article.sections:
            dot = "" if "." in section.number else "."
            prefix = f"<b>{escape(section.number)}{dot} {escape(section.title)}.</b> "
            for i, p in enumerate(section.paras):
                story.append(_paragraph(p, registry, prefix if i == 0 else ""))
    kind = "Agreement" if doc.doc_type == "credit_agreement" else "Amendment"
    signature: list = [
        Spacer(1, 10),
        Paragraph(
            f"IN WITNESS WHEREOF, the parties have caused this {kind} to be executed by their duly authorized "
            f"officers as of {escape(long_date(doc.doc_date))}.",
            BODY,
        ),
        Spacer(1, 14),
    ]
    for party, signer, title in doc.signature_blocks:
        signature += [
            Paragraph(f"<b>{escape(party.upper())}</b>", BODY),
            Paragraph(f"By: /s/ {escape(signer)}", BODY),
            Paragraph(f"Name: {escape(signer)}", BODY),
            Paragraph(f"Title: {escape(title)}", BODY),
            Spacer(1, 16),
        ]
    if doc.toc:
        story.append(PageBreak())
        story.append(Paragraph("SIGNATURE PAGE", ARTICLE))
    story.append(KeepTogether(signature))
    for heading, paras, rows in doc.exhibits:
        story.append(PageBreak())
        story.append(Paragraph(escape(heading), ARTICLE))
        for p in paras:
            story.append(_paragraph(p, registry))
        if rows:
            width = common.content_width(MARGIN)
            first = width * (0.40 if len(rows[0]) > 3 else 0.46)
            rest = (width - first) / (len(rows[0]) - 1)
            table = Table(rows, colWidths=[first] + [rest] * (len(rows[0]) - 1), hAlign="LEFT")
            table.setStyle(
                TableStyle(
                    [
                        ("FONT", (0, 0), (-1, -1), FONT, 10),
                        ("FONT", (0, 0), (-1, 0), BOLD, 10),
                        ("LINEBELOW", (0, 0), (-1, 0), 0.6, RULE),
                        ("LINEBELOW", (0, 1), (-1, -1), 0.3, common.SOFT),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )
            story += [Spacer(1, 8), table]
    short = "Credit Agreement" if doc.doc_type == "credit_agreement" else "First Amendment to Credit Agreement"
    pages = common.build_pdf(path, f"{short} - {borrower_name}", f"{borrower_name} | {short}", LENDER, story, MARGIN)
    anchor_pages = {anchor: page for anchors, page in registry.items() for anchor in anchors}
    missing = set(doc.cites) - set(anchor_pages)
    if missing:
        raise AssertionError(f"citations without a page: {sorted(missing)}")
    return {"pages": pages, "anchor_pages": anchor_pages}
