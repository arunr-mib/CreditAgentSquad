"""The Word review memo: a title block, the review sections as real Word tables and headings, a
numbered source reference beside every figure, and a Sources section that lists each reference
with its fact id, document, page and printed text, or the calculation and its inputs.
"""
import io
from datetime import date
from typing import Any

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from app.publishing import style
from app.publishing.content import RefBook, day, is_fig
from app.publishing.style import BB_OUTCOME_WORDS, OPERATOR_WORDS, OUTCOME_WORDS, display, table_format

REF_STYLE = "Source Ref"
SOURCES_HEADING = "Sources"
SOURCE_COLUMNS = ("Ref", "Fact id", "Item", "Document", "Page", "Source")
SECTION_TITLES = {"summary": "Summary", "performance": "Financial performance", "covenants": "Covenants",
                  "collateral": "Collateral", "risks": "Risks", "outlook": "Outlook", "note": "Note"}
PAGE_WIDTH = Inches(6.9)


def _rgb(hex_colour: str) -> RGBColor:
    return RGBColor.from_string(hex_colour)


def _shade(cell: Any, colour: str) -> None:
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), colour)
    cell._tc.get_or_add_tcPr().append(shd)


def _borders(cell: Any, **edges: str) -> None:
    """Set cell borders: edge name -> colour; other edges are cleared."""
    borders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        el = OxmlElement(f"w:{edge}")
        if edge in edges:
            el.set(qn("w:val"), "single")
            el.set(qn("w:sz"), "4")
            el.set(qn("w:color"), edges[edge])
        else:
            el.set(qn("w:val"), "nil")
        borders.append(el)
    cell._tc.get_or_add_tcPr().append(borders)


def _field(paragraph: Any, code: str) -> None:
    """A field (PAGE, NUMPAGES) that Word fills in; it carries no stored text."""
    run = paragraph.add_run()
    for kind in ("begin", None, "end"):
        if kind:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = f" {code} "
        run._r.append(el)
    run.font.size, run.font.color.rgb = Pt(8), _rgb(style.INK_500)


class _Memo:
    def __init__(self, content: dict[str, Any]):
        self.content = content
        self.refs = RefBook(content)
        self.doc = Document()
        self._styles()
        self._page()

    # set-up ---------------------------------------------------------------------------------
    def _styles(self) -> None:
        styles = self.doc.styles
        normal = styles["Normal"]
        normal.font.name, normal.font.size, normal.font.color.rgb = style.FONT, Pt(10), _rgb(style.INK_900)
        normal.element.rPr.rFonts.set(qn("w:eastAsia"), style.FONT)
        normal.paragraph_format.space_after, normal.paragraph_format.line_spacing = Pt(6), 1.15
        for name, size, before, after in (("Title", 22, 0, 2), ("Heading 1", 14, 16, 6), ("Heading 2", 11, 10, 4)):
            s = styles[name]
            s.font.name, s.font.size, s.font.bold, s.font.color.rgb = style.FONT, Pt(size), True, _rgb(style.INK_900)
            s.element.rPr.rFonts.set(qn("w:asciiTheme"), "")
            for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
                s.element.rPr.rFonts.set(qn(attr), style.FONT)
            s.paragraph_format.space_before, s.paragraph_format.space_after = Pt(before), Pt(after)
            s.paragraph_format.keep_with_next = True
        title_ppr = styles["Title"].element.get_or_add_pPr()
        for border in title_ppr.findall(qn("w:pBdr")):
            title_ppr.remove(border)
        ref = styles.add_style(REF_STYLE, WD_STYLE_TYPE.CHARACTER)
        ref.font.superscript, ref.font.color.rgb, ref.font.bold = True, _rgb(style.INK_500), False

    def _page(self) -> None:
        section = self.doc.sections[0]
        section.orientation = WD_ORIENT.PORTRAIT
        section.left_margin = section.right_margin = Inches(0.8)
        section.top_margin, section.bottom_margin = Inches(0.9), Inches(0.8)
        borrowers = self.content["borrowers"]
        who = borrowers[0]["borrower"]["name"] if self.content["scope"] == "borrower" else self.content["title"].split(":")[0]
        period = f"period ended {day(date.fromisoformat(self.content['period_end']))}"
        for part, left, right in ((section.header, f"{who}, {period}", style.LENDER),
                                  (section.footer, style.SYNTHETIC, None)):
            p = part.paragraphs[0]
            p.style = self.doc.styles["Normal"]  # the header style brings its own tab stops
            p.paragraph_format.tab_stops.add_tab_stop(PAGE_WIDTH, WD_TAB_ALIGNMENT.RIGHT)
            run = p.add_run(left + "\t" + (right or ""))
            run.font.size, run.font.color.rgb = Pt(8), _rgb(style.INK_500)
            if right is None:
                for text, code in (("Page ", "PAGE"), (" of ", "NUMPAGES")):
                    r = p.add_run(text)
                    r.font.size, r.font.color.rgb = Pt(8), _rgb(style.INK_500)
                    _field(p, code)

    # writing --------------------------------------------------------------------------------
    def write(self, paragraph: Any, segments: list[Any] | Any, *, size: float | None = None, colour: str | None = None,
              bold: bool = False, italic: bool = False, fmt: str | None = None) -> None:
        """Text and figures into a paragraph. Each figure is followed by its reference number."""
        for seg in segments if isinstance(segments, list) else [segments]:
            if seg is None or seg == "":
                continue
            if is_fig(seg):
                record = self.refs.record(seg)
                run = paragraph.add_run(display(record, seg.get("fmt") or fmt))
                mark = paragraph.add_run(str(self.refs.number(seg)), style=REF_STYLE)
                if size:
                    mark.font.size = Pt(size)
            else:
                run = paragraph.add_run(str(seg))
            run.bold, run.italic = bold, italic
            if size:
                run.font.size = Pt(size)
            if colour:
                run.font.color.rgb = _rgb(colour)

    def para(self, segments: list[Any] | Any, **kw: Any) -> Any:
        p = self.doc.add_paragraph()
        self.write(p, segments, **kw)
        return p

    def status(self, paragraph: Any, word: str, colour: str, *, size: float = 9) -> None:
        """A dot and a word; colour carries the meaning."""
        dot = paragraph.add_run("● ")
        dot.font.color.rgb, dot.font.size = _rgb(colour), Pt(size)
        run = paragraph.add_run(word)
        run.font.color.rgb, run.font.size, run.bold = _rgb(colour), Pt(size), True

    def table(self, headers: list[str], rows: list[list[Any]], widths: list[float], *, numeric_from: int = 1,
              size: float = 9, totals: set[int] | None = None) -> Any:
        """A real Word table. A row is a list of cells; a cell is text, a figure, a list of
        segments, or ("status", word, colour)."""
        table = self.doc.add_table(rows=1, cols=len(headers))
        table.alignment, table.autofit = WD_TABLE_ALIGNMENT.CENTER, False
        for i, text in enumerate(headers):
            table.columns[i].width = Inches(widths[i])
            cell = table.rows[0].cells[i]
            cell.width = Inches(widths[i])
            _shade(cell, style.SUNKEN)
            _borders(cell, bottom=style.HAIRLINE_STRONG)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(2)
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if i >= numeric_from else WD_ALIGN_PARAGRAPH.LEFT
            self.write(p, text, size=size - 1, bold=True, colour=style.INK_700)
        header = OxmlElement("w:tblHeader")
        header.set(qn("w:val"), "true")
        table.rows[0]._tr.get_or_add_trPr().append(header)
        for n, row in enumerate(rows):
            cells = table.add_row().cells
            total = bool(totals and n in totals)
            for i, value in enumerate(row):
                cell = cells[i]
                cell.width = Inches(widths[i])
                _borders(cell, bottom=style.HAIRLINE, **({"top": style.HAIRLINE_STRONG} if total else {}))
                if total:
                    _shade(cell, style.SUNKEN)
                p = cell.paragraphs[0]
                p.paragraph_format.space_after = Pt(2)
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if i >= numeric_from else WD_ALIGN_PARAGRAPH.LEFT
                if isinstance(value, tuple) and value and value[0] == "status":
                    self.status(p, value[1], value[2], size=size)
                elif is_fig(value):
                    unit = self.refs.record(value).get("unit", "usd")
                    self.write(p, value, size=size, bold=total, fmt=table_format(unit))
                else:
                    self.write(p, value if value not in (None, []) else "–", size=size, bold=total)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)
        return table

    # sections -------------------------------------------------------------------------------
    def title_block(self, b: dict[str, Any]) -> None:
        info = b["borrower"]
        eyebrow = self.para("CREDIT REVIEW MEMO", size=8, colour=style.INK_500, bold=True)
        eyebrow.paragraph_format.space_after = Pt(0)
        self.doc.add_paragraph(info["name"], style="Title")
        end = date.fromisoformat(b["period_end"])
        self.para(f"Period ended {day(end)}. {style.LENDER}. {style.SYNTHETIC}", size=10, colour=style.INK_700)
        rows = [["Industry", info["industry"] or "", "Relationship manager", info["relationship_manager"] or ""],
                ["Location", info["location"] or "", "Analyst", info["analyst"] or ""],
                ["Risk rating", info["risk_rating"], "Review stage", b["cycle"]["stage"].replace("_", " ")],
                ["Commentary", _commentary_state(b), "", ""]]
        table = self.doc.add_table(rows=0, cols=4)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, width in enumerate((1.2, 2.25, 1.5, 1.95)):
            table.columns[i].width = Inches(width)
        for row in rows:
            cells = table.add_row().cells
            for i, value in enumerate(row):
                cells[i].width = Inches((1.2, 2.25, 1.5, 1.95)[i])
                _borders(cells[i], bottom=style.HAIRLINE)
                p = cells[i].paragraphs[0]
                p.paragraph_format.space_after = Pt(2)
                self.write(p, value, size=9, colour=style.INK_500 if i % 2 == 0 else None)
        if self.content.get("snapshot_sha256"):
            self.para(f"Snapshot sha256 {self.content['snapshot_sha256']}", size=7.5, colour=style.INK_500)

    def loans(self, b: dict[str, Any]) -> None:
        self.doc.add_heading("Borrower and loans", level=1)
        rows = [[loan["name"], day(date.fromisoformat(loan["maturity"])) if loan["maturity"] else "", loan["pricing"],
                 loan["commitment"], loan["outstanding"], loan["availability"]] for loan in b["loans"]]
        self.table(["Loan", "Maturity", "Pricing", "Commitment", "Outstanding", "Availability"], rows,
                   [1.7, 0.95, 1.2, 1.05, 1.05, 0.95], numeric_from=3)

    def commentary(self, b: dict[str, Any]) -> None:
        self.doc.add_heading("Commentary", level=1)
        if not b["commentary"]:
            self.para("No commentary has been written for this review yet.", colour=style.INK_500, italic=True)
            return
        for c in b["commentary"]:
            self.doc.add_heading(SECTION_TITLES.get(c["section"], c["section"].replace("_", " ").title()), level=2)
            label = self.doc.add_paragraph()
            label.paragraph_format.space_after, label.paragraph_format.keep_with_next = Pt(2), True
            if c["status"] == "approved":
                self.status(label, f"Approved by {c['approved_by'] or 'a reviewer'}", style.GREEN, size=8)
            else:
                self.status(label, style.DRAFT_LABEL, style.AMBER, size=8)
            by = "Drafted by the Review Agent" if c["written_by_agent"] else f"Written by {c['author']}"
            self.write(label, f"   {by}", size=8, colour=style.IRIS if c["written_by_agent"] else style.INK_500)
            self.para(c["segments"])

    def covenants(self, b: dict[str, Any]) -> None:
        self.doc.add_heading("Covenant compliance", level=1)
        self.para("Each covenant is calculated by code from the approved terms and stored facts. The borrower's "
                  "certificate is shown beside the calculation; it is evidence, not the test.",
                  size=9, colour=style.INK_700)
        for missing in b["covenants_untested"]:
            self.para(f"{missing['covenant']}: could not be tested for this period.", colour=style.AMBER)
        if not b["covenants"]:
            self.para("No covenant was tested for this period.", colour=style.INK_500, italic=True)
            return
        rows = []
        for c in b["covenants"]:
            word, colour = OUTCOME_WORDS.get(c["outcome"], (c["outcome"], style.INK_900))
            rows.append([c["covenant"], c["value"], OPERATOR_WORDS.get(c["operator"], c["operator"] or ""),
                         c["threshold"], c["headroom_pct"], c["reported"], ("status", word, colour)])
        self.table(["Covenant", "Calculated", "Test", "Required", "Cushion", "Certificate", "Outcome"], rows,
                   [1.6, 0.8, 0.6, 0.75, 0.7, 0.8, 1.65], numeric_from=1)

    def trend(self, b: dict[str, Any]) -> None:
        self.doc.add_heading("Key metrics, last eight quarters", level=1)
        periods = [date.fromisoformat(p) for p in b["trend"]["periods"]]
        self.para("Flow measures are trailing twelve months. Amounts are US dollars.", size=9, colour=style.INK_700)
        half = (len(periods) + 1) // 2
        for start, stop in ((0, half), (half, len(periods))):
            if start >= stop:
                continue
            headers = ["Metric"] + [day(p) for p in periods[start:stop]]
            rows = [[row["label"]] + row["cells"][start:stop] for row in b["trend"]["rows"]]
            n = stop - start
            self.table(headers, rows, [2.1] + [4.8 / n] * n, size=8.5)

    def changes(self, b: dict[str, Any]) -> None:
        ch = b["changes"]
        self.doc.add_heading("Changes since the prior period", level=1)
        if not ch["prior_period"]:
            self.para("There is no prior period to compare with.", colour=style.INK_500, italic=True)
            return
        prior, now = day(date.fromisoformat(ch["prior_period"])), day(date.fromisoformat(b["period_end"]))
        if ch["metrics"]:
            rows = [[m["label"], m["prior"], m["current"], m["direction"].capitalize()] for m in ch["metrics"]]
            self.table(["Metric", prior, now, "Direction"], rows, [2.9, 1.4, 1.4, 1.2], numeric_from=1)
        for c in ch["covenants"]:
            before = OUTCOME_WORDS.get(c["prior_outcome"], ("not tested",))[0].lower() if c["prior_outcome"] else "not tested"
            after = OUTCOME_WORDS.get(c["outcome"], (c["outcome"],))[0].lower()
            self.para(f"{c['covenant']}: {before} last period, {after} this period.")
        for title, labels in (("New signals this period", ch["new_signals"]), ("Signals no longer firing", ch["cleared_signals"])):
            if labels:
                self.para(f"{title}: " + "; ".join(labels) + ".")
        if not (ch["metrics"] or ch["covenants"] or ch["new_signals"] or ch["cleared_signals"]):
            self.para("Nothing changed against the prior period.", colour=style.INK_500, italic=True)

    def signals(self, b: dict[str, Any]) -> None:
        self.doc.add_heading("Early warning signals", level=1)
        if not b["signals"]:
            self.para("No signal fired for this period.", colour=style.INK_500, italic=True)
            return
        rows = []
        for s in b["signals"]:
            evidence: list[Any] = []
            for e in s["evidence"]:
                evidence += ([". "] if evidence else []) + [f"{e['label']} ", e["fig"]]
            name = s["label"] + (f": {s['subject']}" if s["subject"] else "")
            rows.append([name, ("status", s["severity"].capitalize(), style.SEVERITY_COLOURS.get(s["severity"], style.INK_500)),
                         evidence or "", s["status"].capitalize()])
        self.table(["Signal", "Severity", "Stored facts behind it", "Status"], rows, [2.6, 0.9, 2.5, 0.9], numeric_from=9)
        for s in b["signals"]:
            if s["explanation"]:
                self.para([f"{s['label']}: "] + s["explanation"], size=9)

    def borrowing_base(self, b: dict[str, Any]) -> None:
        bb = b["borrowing_base"]
        if not bb:
            return
        self.doc.add_heading("Borrowing base", level=1)
        p = self.para(f"Recalculated by code as of {day(date.fromisoformat(bb['as_of']))}, beside the borrower's certificate.   ",
                      size=9, colour=style.INK_700)
        word, colour = BB_OUTCOME_WORDS.get(bb["outcome"], (bb["outcome"], style.INK_900))
        self.status(p, word, colour)
        rows, totals = [], set()
        for n, line in enumerate(bb["lines"]):
            differs = line["status"] == "mismatch"
            rows.append([line["label"], line["computed"], line["certificate"], line["difference"],
                         ("status", "Differs", style.AMBER) if differs else
                         {"match": "Agrees"}.get(line["status"] or "", (line["status"] or "").replace("_", " "))])
            if line["total"]:
                totals.add(n)
        self.table(["Line", "Recalculated", "Certificate", "Difference", "Status"], rows, [2.7, 1.2, 1.2, 1.0, 0.8],
                   totals=totals)

    def work(self, b: dict[str, Any]) -> None:
        self.doc.add_heading("Open work items and actions", level=1)
        if b["work_items"]:
            rows = [[w["title"], ("status", w["severity"].capitalize(), style.SEVERITY_COLOURS.get(w["severity"], style.INK_500)),
                     w["question"]] for w in b["work_items"]]
            self.table(["Work item", "Severity", "Question for a person"], rows, [2.6, 0.9, 3.4], numeric_from=9)
        else:
            self.para("No work item is open.", colour=style.INK_500, italic=True)
        if b["actions"]:
            rows = [[a["title"], a["owner"] or "", day(date.fromisoformat(a["due_date"])) if a["due_date"] else "",
                     a["status"].replace("_", " ").capitalize()] for a in b["actions"]]
            self.table(["Action", "Owner", "Due", "Status"], rows, [3.3, 1.5, 1.1, 1.0], numeric_from=9)
        else:
            self.para("No action is open.", colour=style.INK_500, italic=True)

    def portfolio(self) -> None:
        port = self.content["portfolio"]
        eyebrow = self.para("REVIEW PACKAGE", size=8, colour=style.INK_500, bold=True)
        eyebrow.paragraph_format.space_after = Pt(0)
        self.doc.add_paragraph(self.content["title"], style="Title")
        self.para(f"{style.LENDER}. {style.SYNTHETIC}", colour=style.INK_700)
        self.doc.add_heading("Portfolio summary", level=1)
        self.table(["Measure", "This period"], [[s["label"], s["fig"]] for s in port["summary"]], [3.2, 1.6])
        rows = [[r["borrower"], r["risk_rating"], r["outstanding"],
                 ("status", *OUTCOME_WORDS[r["worst_outcome"]]) if r["worst_outcome"] else "Not tested",
                 r["signals"], r["work_items"]] for r in port["rows"]]
        self.table(["Borrower", "Rating", "Outstanding", "Covenants", "Signals", "Open items"], rows,
                   [2.2, 0.6, 1.2, 1.7, 0.6, 0.6], numeric_from=9)
        self.doc.add_heading("Watch list", level=1)
        if port["watch_list"]:
            self.table(["Borrower", "Why it is on the list"],
                       [[w["borrower"], "; ".join(w["reasons"])] for w in port["watch_list"]], [2.4, 4.5], numeric_from=9)
        else:
            self.para("No borrower meets the watch list conditions this period.", colour=style.INK_500, italic=True)

    def sources(self) -> None:
        self.doc.add_page_break()
        self.doc.add_heading(SOURCES_HEADING, level=1)
        self.para("Each reference number in this memo points to one stored fact. Extracted facts name the document, "
                  "page and printed text; calculated facts name the calculation and its inputs.",
                  size=9, colour=style.INK_700)
        rows = [[str(n), d["id"], d["item"], d["document"], d["page"], d["detail"]]
                for n, _record, d in self.refs.listing()]
        self.table(list(SOURCE_COLUMNS), rows, [0.35, 1.0, 1.35, 1.0, 0.4, 2.8], numeric_from=9, size=7)

    def build(self) -> tuple[bytes, set[str]]:
        borrowers = self.content["borrowers"]
        if self.content["scope"] != "borrower":
            self.portfolio()
        for i, b in enumerate(borrowers):
            if i or self.content["scope"] != "borrower":
                self.doc.add_page_break()
            self.title_block(b)
            self.commentary(b)
            self.loans(b)
            self.covenants(b)
            self.trend(b)
            self.changes(b)
            self.signals(b)
            self.borrowing_base(b)
            self.work(b)
        self.sources()
        self.doc.core_properties.title = self.content["title"]
        self.doc.core_properties.author = style.LENDER
        out = io.BytesIO()
        self.doc.save(out)
        used = {sid for sid in self.refs.numbers if sid in self.content["facts"]}
        return out.getvalue(), used


def _commentary_state(b: dict[str, Any]) -> str:
    if not b["commentary"]:
        return "None written"
    return "Approved" if all(c["status"] == "approved" for c in b["commentary"]) else style.DRAFT_LABEL


def render_memo(content: dict[str, Any]) -> tuple[bytes, set[str]]:
    return _Memo(content).build()
