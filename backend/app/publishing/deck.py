"""The PowerPoint review deck: title, portfolio summary, watch list, then two slides per borrower
(covenant table and trend chart; commentary and signals), and closing Sources slides. Tables and
charts are native. Every figure carries a reference number; each slide's notes list its sources.
"""
import io
from datetime import date
from typing import Any

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

from app.publishing import style
from app.publishing.content import RefBook, day, describe_source, is_fig
from app.publishing.style import OUTCOME_WORDS, display, table_format

SOURCES_TITLE = "Sources"
SOURCE_COLUMNS = ("Ref", "Item", "Fact", "Source")
SOURCE_ROWS = 16
CHART_SERIES = (("revenue_ttm", "Revenue"), ("ebitda", "EBITDA"))
CHART_TITLE = "Revenue and EBITDA, trailing twelve months"
W, H, MARGIN = 13.333, 7.5, 0.6


def _rgb(hex_colour: str) -> RGBColor:
    return RGBColor.from_string(hex_colour)


def note_line(n: int, record: dict[str, Any], facts: dict[str, Any]) -> str:
    d = describe_source(record, facts)
    where = f'"{d["document"]}", page {d["page"]}. ' if d["document"] else ""
    kind = "derived" if record["kind"] == "derived" else "fact"
    return f"[{n}] {d['item']}: {display(record)} | {kind} {record['id']} | {where}{d['detail']}"


def chart_line(title: str, series: str, points: list[tuple[str, int]]) -> str:
    return f'Chart "{title}", series "{series}": ' + "; ".join(f"{label} [{n}]" for label, n in points)


def source_row(n: int, record: dict[str, Any]) -> list[str]:
    kind = record["kind"]
    if kind == "derived":
        source = "Sum of the facts listed in the notes" if record["op"] == "sum" else "Count of the items listed in the notes"
    elif kind == "extracted":
        source = f'"{(record.get("document") or {}).get("title") or ""}", page {record.get("page")}'
    elif kind == "calculated":
        source = f"Calculation {(record.get('calculation') or {}).get('formula_key', '')}"
    elif kind == "system":
        source = f"System of record {record.get('connector')}"
    elif kind == "manual":
        source = f"Entered by {record.get('entered_by')}"
    else:
        source = "Synthetic ground truth, not extracted"
    return [str(n), record["label"], record["id"][:8] if kind != "derived" else "derived", source]


class _Deck:
    def __init__(self, content: dict[str, Any]):
        self.content = content
        self.refs = RefBook(content)
        self.prs = Presentation()
        self.prs.slide_width, self.prs.slide_height = Inches(W), Inches(H)
        self.blank = self.prs.slide_layouts[6]
        self.slide: Any = None
        self.notes: list[str] = []
        self.noted: set[int] = set()

    # primitives -----------------------------------------------------------------------------
    def new_slide(self, title: str, eyebrow: str = "") -> Any:
        self._close()
        self.slide = self.prs.slides.add_slide(self.blank)
        fill = self.slide.background.fill
        fill.solid()
        fill.fore_color.rgb = _rgb(style.CANVAS)
        if eyebrow:
            self.text(MARGIN, 0.35, W - 2 * MARGIN, 0.3, eyebrow.upper(), size=10, colour=style.INK_500, bold=True)
        self.text(MARGIN, 0.6, W - 2 * MARGIN, 0.7, title, size=26, bold=True)
        self.text(MARGIN, H - 0.5, 8, 0.3, f"{style.LENDER}. {style.SYNTHETIC}", size=9, colour=style.INK_500)
        box = self.slide.shapes.add_textbox(Inches(W - MARGIN - 1), Inches(H - 0.5), Inches(1), Inches(0.3))
        p = box.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.RIGHT
        fld = p._p.makeelement(qn("a:fld"), {"id": "{B6F15528-21DE-4FAA-801E-634DDDAF4B2B}", "type": "slidenum"})
        rpr = fld.makeelement(qn("a:rPr"), {"lang": "en-US", "sz": "900"})
        t = fld.makeelement(qn("a:t"), {})
        t.text = "‹#›"
        fld.append(rpr)
        fld.append(t)
        p._p.append(fld)
        self.notes, self.noted = [], set()
        return self.slide

    def _close(self) -> None:
        if self.slide is not None and self.notes:
            self.slide.notes_slide.notes_text_frame.text = "\n".join(["Sources for this slide"] + self.notes)

    def cite(self, figure: dict[str, Any]) -> int:
        n = self.refs.number(figure)
        if n not in self.noted:
            self.noted.add(n)
            self.notes.append(note_line(n, self.refs.record(figure), self.refs.facts))
        return n

    def write(self, paragraph: Any, segments: Any, *, size: float = 12, colour: str = style.INK_900,
              bold: bool = False, fmt: str | None = None) -> None:
        for seg in segments if isinstance(segments, list) else [segments]:
            if seg is None or seg == "":
                continue
            if is_fig(seg):
                run = paragraph.add_run()
                run.text = display(self.refs.record(seg), seg.get("fmt") or fmt)
                mark = paragraph.add_run()
                mark.text = str(self.cite(seg))
                mark.font.size, mark.font.color.rgb, mark.font.name = Pt(size), _rgb(style.INK_500), style.FONT
                mark._r.get_or_add_rPr().set("baseline", "30000")
            else:
                run = paragraph.add_run()
                run.text = str(seg)
            run.font.size, run.font.bold, run.font.name = Pt(size), bold, style.FONT
            run.font.color.rgb = _rgb(colour)

    def text(self, x: float, y: float, w: float, h: float, segments: Any, *, align: Any = PP_ALIGN.LEFT, **kw: Any) -> Any:
        box = self.slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        frame = box.text_frame
        frame.word_wrap = True
        frame.margin_left = frame.margin_right = frame.margin_top = frame.margin_bottom = 0
        frame.paragraphs[0].alignment = align
        self.write(frame.paragraphs[0], segments, **kw)
        return box

    def status(self, paragraph: Any, word: str, colour: str, size: float = 10) -> None:
        self.write(paragraph, "● ", size=size, colour=colour)
        self.write(paragraph, word, size=size, colour=colour, bold=True)

    def table(self, x: float, y: float, widths: list[float], headers: list[str], rows: list[list[Any]], *,
              numeric_from: int = 1, size: float = 10, row_height: float = 0.34) -> Any:
        shape = self.slide.shapes.add_table(len(rows) + 1, len(headers), Inches(x), Inches(y), Inches(sum(widths)),
                                            Inches(row_height * (len(rows) + 1)))
        table = shape.table
        tbl_pr = shape._element.graphic.graphicData.tbl.tblPr
        tbl_pr.set("bandRow", "0")
        style_id = tbl_pr.find(qn("a:tableStyleId"))
        if style_id is not None:
            style_id.text = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"  # no style, no grid
        for i, width in enumerate(widths):
            table.columns[i].width = Inches(width)
        for r in range(len(rows) + 1):
            table.rows[r].height = Inches(row_height)
            for c in range(len(headers)):
                cell = table.cell(r, c)
                cell.fill.solid()
                cell.fill.fore_color.rgb = _rgb(style.SUNKEN if r == 0 else style.SURFACE)
                cell.margin_left = cell.margin_right = Inches(0.08)
                cell.margin_top = cell.margin_bottom = Inches(0.03)
                cell.vertical_anchor = MSO_ANCHOR.MIDDLE
                tc_pr = cell._tc.get_or_add_tcPr()
                line = tc_pr.makeelement(qn("a:lnB"), {"w": "6350"})
                solid = line.makeelement(qn("a:solidFill"), {})
                solid.append(line.makeelement(qn("a:srgbClr"), {"val": style.HAIRLINE_STRONG if r == 0 else style.HAIRLINE}))
                line.append(solid)
                tc_pr.insert(0, line)
                p = cell.text_frame.paragraphs[0]
                p.alignment = PP_ALIGN.RIGHT if c >= numeric_from else PP_ALIGN.LEFT
                value = headers[c] if r == 0 else rows[r - 1][c]
                if r == 0:
                    self.write(p, value, size=size - 1, bold=True, colour=style.INK_700)
                elif isinstance(value, tuple) and value and value[0] == "status":
                    self.status(p, value[1], value[2], size=size)
                elif is_fig(value):
                    self.write(p, value, size=size, fmt=table_format(self.refs.record(value).get("unit", "usd")))
                else:
                    self.write(p, value if value not in (None, []) else "–", size=size)
        return shape

    # slides ---------------------------------------------------------------------------------
    def title_slide(self) -> None:
        end = date.fromisoformat(self.content["period_end"])
        self.new_slide(self.content["title"].split(":")[0] if self.content["scope"] != "portfolio" else "Portfolio review",
                       "Credit review")
        self.text(MARGIN, 1.5, 10, 0.5, f"Period ended {day(end)}", size=18, colour=style.INK_700)
        self.text(MARGIN, 5.6, 10, 0.4, style.LENDER, size=14, bold=True)
        self.text(MARGIN, 6.0, 12, 0.3, f"Snapshot sha256 {self.content.get('snapshot_sha256', '')}", size=9,
                  colour=style.INK_500)
        self.text(MARGIN, 2.4, 11, 1.2, "Every figure in this deck is a stored fact. The small number beside a figure "
                  "is its reference; the notes under each slide and the closing Sources slides name the fact and where "
                  "it came from.", size=13, colour=style.INK_700)

    def summary_slide(self) -> None:
        port = self.content["portfolio"]
        self.new_slide("Portfolio summary", "Portfolio")
        tile = (W - 2 * MARGIN) / len(port["summary"])
        for i, item in enumerate(port["summary"]):
            x = MARGIN + i * tile
            self.text(x, 1.55, tile - 0.15, 0.3, item["label"], size=10, colour=style.INK_500)
            self.text(x, 1.85, tile - 0.15, 0.6, item["fig"], size=20, bold=True)
        rows = [[r["borrower"], r["risk_rating"], r["outstanding"],
                 ("status", *OUTCOME_WORDS[r["worst_outcome"]]) if r["worst_outcome"] else "Not tested",
                 r["signals"], r["work_items"]] for r in port["rows"]]
        self._paged("Portfolio summary", "Portfolio", rows, 11, 2.75,
                    [4.2, 0.9, 1.9, 3.3, 0.9, 0.933], ["Borrower", "Rating", "Outstanding", "Covenants", "Signals", "Open items"])

    def _paged(self, title: str, eyebrow: str, rows: list[list[Any]], per_slide: int, first_y: float,
               widths: list[float], headers: list[str]) -> None:
        """A table that continues on further slides when it has more rows than fit."""
        for start in range(0, max(len(rows), 1), per_slide):
            if start:
                self.new_slide(f"{title}, continued", eyebrow)
            self.table(MARGIN, first_y if not start else 1.55, widths, headers, rows[start:start + per_slide],
                       numeric_from=99)
            per_slide = 14

    def watch_slide(self) -> None:
        watch = self.content["portfolio"]["watch_list"]
        self.new_slide("Watch list", "Portfolio")
        if not watch:
            self.text(MARGIN, 1.7, 11, 0.4, "No borrower meets the watch list conditions this period.", size=14,
                      colour=style.INK_700)
            return
        rows = [[w["borrower"], w["risk_rating"],
                 ("status", *OUTCOME_WORDS[w["worst_outcome"]]) if w["worst_outcome"] else "Not tested",
                 "; ".join(w["reasons"])] for w in watch]
        self._paged("Watch list", "Portfolio", rows, 9, 1.55, [3.3, 0.8, 3.0, 5.033],
                    ["Borrower", "Rating", "Covenants", "Why it is on the list"])

    def borrower_slides(self, b: dict[str, Any]) -> None:
        info = b["borrower"]
        self.new_slide(info["name"], "Covenants and trend")
        line: list[Any] = ["Risk rating ", info["risk_rating"]] if info["risk_rating"] else []
        line += [f"{'. ' if line else ''}{info['industry'].capitalize()}, {info['location']}"]
        self.text(MARGIN, 1.3, 12, 0.3, line, size=12, colour=style.INK_700)
        rows = []
        for c in b["covenants"]:
            word, colour = OUTCOME_WORDS.get(c["outcome"], (c["outcome"], style.INK_900))
            rows.append([c["covenant"], c["value"], c["threshold"], c["headroom_pct"], c["reported"],
                         ("status", word, colour)])
        y = 1.85
        if rows:
            self.table(MARGIN, y, [1.9, 0.85, 0.8, 0.8, 0.85, 1.5],
                       ["Covenant", "Calculated", "Required", "Cushion", "Certificate", "Outcome"], rows, size=9.5)
            y += 0.34 * (len(rows) + 1) + 0.35
        else:
            self.text(MARGIN, y, 6.5, 0.4, "No covenant was tested for this period.", size=12, colour=style.INK_700)
            y += 0.7
        loans = [[loan["name"], loan["outstanding"], loan["commitment"], loan["availability"]] for loan in b["loans"]]
        if loans:
            self.table(MARGIN, y, [2.6, 1.4, 1.4, 1.3], ["Loan", "Outstanding", "Commitment", "Availability"], loans,
                       size=9.5)
        self._chart(b, 7.7, 1.75, W - MARGIN - 7.7, 4.9)

        self.new_slide(f"{info['name']}: commentary and signals", "Commentary and signals")
        box = self.slide.shapes.add_textbox(Inches(MARGIN), Inches(1.5), Inches(6.9), Inches(5.2))
        frame = box.text_frame
        frame.word_wrap = True
        frame.margin_left = frame.margin_right = frame.margin_top = 0
        length = sum(len(c["body"]) for c in b["commentary"])
        size = 11 if length < 1300 else 9.5 if length < 2200 else 8
        first = True
        if not b["commentary"]:
            self.write(frame.paragraphs[0], "No commentary has been written for this review yet.", size=12,
                       colour=style.INK_700)
        for c in b["commentary"]:
            head = frame.paragraphs[0] if first else frame.add_paragraph()
            first = False
            head.space_before = Pt(6)
            self.write(head, c["section"].replace("_", " ").capitalize() + "   ", size=size, bold=True)
            if c["status"] == "approved":
                self.status(head, "Approved", style.GREEN, size=size - 2)
            else:
                self.status(head, style.DRAFT_LABEL, style.AMBER, size=size - 2)
            if c["written_by_agent"]:
                self.write(head, "   Drafted by the Review Agent", size=size - 2, colour=style.IRIS)
            self.write(frame.add_paragraph(), c["segments"], size=size)
        x = 7.9
        self.text(x, 1.5, 4.8, 0.3, "Early warning signals", size=12, bold=True)
        shown = b["signals"][:8]
        if shown:
            rows = [[s["label"] + (f": {s['subject']}" if s["subject"] else ""),
                     ("status", s["severity"].capitalize(), style.SEVERITY_COLOURS.get(s["severity"], style.INK_500))]
                    for s in shown]
            self.table(x, 1.9, [3.6, 1.233], ["Signal", "Severity"], rows, numeric_from=9, size=9, row_height=0.32)
            y = 1.9 + 0.32 * (len(rows) + 1) + 0.15
            if len(b["signals"]) > len(shown):
                self.text(x, y, 4.8, 0.3, "Further signals are listed in the review memo.", size=9, colour=style.INK_500)
                y += 0.3
        else:
            self.text(x, 1.9, 4.8, 0.3, "No signal fired for this period.", size=10, colour=style.INK_700)
            y = 2.3
        if b["work_items"] and y < 5.6:
            self.text(x, y + 0.1, 4.8, 0.3, "Open work items", size=12, bold=True)
            items = b["work_items"][:4]
            box = self.slide.shapes.add_textbox(Inches(x), Inches(y + 0.45), Inches(4.83), Inches(1.5))
            box.text_frame.word_wrap = True
            box.text_frame.margin_left = box.text_frame.margin_top = 0
            for i, w in enumerate(items):
                p = box.text_frame.paragraphs[0] if i == 0 else box.text_frame.add_paragraph()
                self.write(p, w["title"], size=9, colour=style.INK_700)

    def _chart(self, b: dict[str, Any], x: float, y: float, w: float, h: float) -> None:
        periods = [date.fromisoformat(p) for p in b["trend"]["periods"]]
        rows = {r["metric"]: r for r in b["trend"]["rows"]}
        series = [(label, rows[name]) for name, label in CHART_SERIES if name in rows]
        if not series:
            return
        labels = [f"{p:%b %Y}" for p in periods]
        data = CategoryChartData(number_format='#,##0.0,,')
        data.categories = labels
        for label, row in series:
            values = [float(self.refs.record(c)["value"]) if c else None for c in row["cells"]]
            data.add_series(label, values)
            self.notes.append(chart_line(CHART_TITLE, label, [(labels[i], self.refs.number(c))
                                                              for i, c in enumerate(row["cells"]) if c]))
            for c in row["cells"]:
                if c:
                    self.cite(c)
        self.text(x, y - 0.05, w, 0.3, CHART_TITLE, size=12, bold=True)
        self.text(x, y + 0.25, w, 0.25, "US dollars, millions. By quarter end.", size=9, colour=style.INK_500)
        frame = self.slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(x), Inches(y + 0.55), Inches(w),
                                            Inches(h - 0.55), data)
        chart = frame.chart
        chart.font.size, chart.font.name = Pt(9), style.FONT
        chart.font.color.rgb = _rgb(style.INK_700)
        chart.has_legend = True
        chart.legend.position, chart.legend.include_in_layout = XL_LEGEND_POSITION.BOTTOM, False
        chart.has_title = False
        plot = chart.plots[0]
        plot.gap_width, plot.overlap = 60, -10
        for s, colour in zip(plot.series, (style.INK_700, style.INK_400), strict=False):
            s.format.fill.solid()
            s.format.fill.fore_color.rgb = _rgb(colour)
        value_axis = chart.value_axis
        value_axis.has_major_gridlines = True
        value_axis.major_gridlines.format.line.color.rgb = _rgb(style.HAIRLINE)
        value_axis.format.line.fill.background()
        value_axis.tick_labels.number_format, value_axis.tick_labels.number_format_is_linked = '#,##0.0,,', False
        chart.category_axis.format.line.color.rgb = _rgb(style.HAIRLINE_STRONG)

    def sources_slides(self) -> None:
        listing = self.refs.listing()
        per_slide = SOURCE_ROWS * 2
        for start in range(0, max(len(listing), 1), per_slide):
            self.new_slide(SOURCES_TITLE if start == 0 else f"{SOURCES_TITLE}, continued", "Sources")
            self.notes.append("Full fact ids, documents, pages and calculation inputs are in the notes under each "
                              "slide and in the frozen snapshot.")
            chunk = listing[start:start + per_slide]
            for col, part in enumerate((chunk[:SOURCE_ROWS], chunk[SOURCE_ROWS:])):
                if part:
                    rows = [source_row(n, record) for n, record, _ in part]
                    self.table(MARGIN + col * 6.15, 1.45, [0.45, 2.7, 0.8, 2.03], list(SOURCE_COLUMNS), rows,
                               numeric_from=9, size=7, row_height=0.29)

    def build(self) -> tuple[bytes, set[str]]:
        self.title_slide()
        self.summary_slide()
        self.watch_slide()
        for b in self.content["borrowers"]:
            self.borrower_slides(b)
        self.sources_slides()
        self._close()
        self.prs.core_properties.title = self.content["title"]
        self.prs.core_properties.author = style.LENDER
        out = io.BytesIO()
        self.prs.save(out)
        return out.getvalue(), {sid for sid in self.refs.numbers if sid in self.content["facts"]}


def render_deck(content: dict[str, Any]) -> tuple[bytes, set[str]]:
    return _Deck(content).build()
