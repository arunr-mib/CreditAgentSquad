"""The Excel workbook for one borrower: a spread sheet per statement with computed lines as live
formulas over the input cells, a ratios sheet with formulas, covenants, the borrowing base, and a
Sources sheet that maps every figure cell to its fact.
"""
import io
from datetime import date
from decimal import Decimal
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.calc import metrics as lib
from app.calc import template
from app.calc.periods import is_fiscal_year_end, month_end, prior_fiscal_year_end
from app.domain.metrics_service import EXTRA
from app.publishing import style
from app.publishing.content import describe_source, is_fig
from app.publishing.style import OPERATOR_WORDS, OUTCOME_WORDS, XL_FORMATS

STATEMENT_SHEETS = (("Income statement", ("is",)), ("Balance sheet", ("bs",)), ("Cash flow", ("cf", "sup")))
SOURCES_SHEET = "Sources"
SOURCE_COLUMNS = ("Sheet", "Cell", "Item", "Fact id", "Kind", "Cell holds", "Document", "Page", "Source")
MONTH_WORDS = {3: "Three months", 6: "Six months", 9: "Nine months", 12: "Full year"}
ROUND_DP = {"usd": 0, "ratio": 2, "days": 1, "pct": 4, "count": 0}
HEADER_ROW = 5

_FONT = Font(name=style.FONT, size=10, color=style.INK_900)
_BOLD = Font(name=style.FONT, size=10, bold=True, color=style.INK_900)
_TITLE = Font(name=style.FONT, size=14, bold=True, color=style.INK_900)
_MUTED = Font(name=style.FONT, size=9, color=style.INK_500)
_HEAD_FILL = PatternFill("solid", fgColor=style.SUNKEN)
_RULE = Side(style="thin", color=style.HAIRLINE_STRONG)
_HAIR = Side(style="hair", color=style.HAIRLINE_STRONG)


class _Missing(Exception):
    """A formula needs a cell that is not in the workbook."""


def _shift(day: date, months: int) -> date:
    index = day.year * 12 + day.month - 1 + months
    return month_end(index // 12, index % 12 + 1)


class _Book:
    def __init__(self, content: dict[str, Any], b: dict[str, Any]):
        self.content, self.b = content, b
        self.facts = content["facts"]
        self.wb = Workbook()
        self.wb.remove(self.wb.active)
        self.sources: list[tuple[str, str, str, str, str]] = []  # sheet, cell, item, fact id, role
        self.pos: dict[tuple[str, str], str] = {}  # (line key, period) -> 'Sheet'!A1
        self.fye = b["borrower"].get("fiscal_year_end_month") or 12

    # layout ---------------------------------------------------------------------------------
    def sheet(self, title: str, subtitle: str, widths: list[float]) -> Any:
        ws = self.wb.create_sheet(title)
        ws.sheet_view.showGridLines = False
        ws["A1"], ws["A2"] = f"{self.b['borrower']['name']}: {title.lower()}", subtitle
        ws["A3"] = f"{style.LENDER}. {style.SYNTHETIC}"
        ws["A1"].font, ws["A2"].font, ws["A3"].font = _TITLE, _MUTED, _MUTED
        for i, width in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(i)].width = width
        ws.page_setup.orientation, ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = "landscape", 1, 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.oddHeader.left.text, ws.oddHeader.right.text = style.LENDER, style.SYNTHETIC
        ws.oddFooter.left.text = f"{self.b['borrower']['name']}, {self.content['period_end']}"
        ws.oddFooter.right.text = "Page &P of &N"
        return ws

    def header(self, ws: Any, row: int, labels: list[Any], *, number_from: int = 2) -> None:
        for col, label in enumerate(labels, start=1):
            c = ws.cell(row=row, column=col, value=label)
            c.font, c.fill, c.border = _BOLD, _HEAD_FILL, Border(bottom=_RULE)
            c.alignment = Alignment(horizontal="right" if col >= number_from else "left", vertical="center",
                                    wrap_text=True)
            if isinstance(label, date):
                c.number_format = "d mmm yyyy"

    def label(self, ws: Any, row: int, text: str, *, total: bool = False, col: int = 1) -> None:
        c = ws.cell(row=row, column=col, value=text)
        c.font = _BOLD if total else _FONT

    def _style_number(self, c: Any, unit: str, total: bool) -> None:
        c.number_format = XL_FORMATS.get(unit, XL_FORMATS["usd"])
        c.font = _BOLD if total else _FONT
        c.alignment = Alignment(horizontal="right")
        if total:
            c.fill, c.border = _HEAD_FILL, Border(top=_RULE)
        else:
            c.border = Border(bottom=_HAIR)

    def literal(self, ws: Any, row: int, col: int, figure: dict[str, Any] | None, *, total: bool = False,
                number_format: str | None = None) -> str | None:
        """Write a fact's value into a cell and map the cell on the Sources sheet."""
        if not is_fig(figure):
            return None
        record = self.facts[figure["fig"]]
        c = ws.cell(row=row, column=col, value=Decimal(record["value"]))
        self._style_number(c, record["unit"], total)
        if number_format:
            c.number_format = number_format
        self.sources.append((ws.title, c.coordinate, record["label"], record["id"], "input"))
        return c.coordinate

    def formula(self, ws: Any, row: int, col: int, text: str, unit: str, item: str, fact_id: str | None, *,
                total: bool = False) -> str:
        """Write a formula and map the cell to the stored fact it must reproduce (if there is one)."""
        c = ws.cell(row=row, column=col, value="=" + text)
        self._style_number(c, unit, total)
        self.sources.append((ws.title, c.coordinate, item, fact_id or "", "formula"))
        return c.coordinate

    # sheets ---------------------------------------------------------------------------------
    def summary(self) -> None:
        b = self.b
        ws = self.sheet("Summary", f"Credit review workbook for the period ended {b['period_end']}",
                        [34, 16, 16, 18, 18, 18, 18])
        info = b["borrower"]
        rows = [("Borrower", info["name"]), ("Industry", info["industry"]), ("Location", info["location"]),
                ("Relationship manager", info["relationship_manager"]), ("Analyst", info["analyst"]),
                ("Period end", date.fromisoformat(b["period_end"])), ("Snapshot", self.content.get("snapshot_sha256", ""))]
        row = HEADER_ROW
        for name, value in rows:
            self.label(ws, row, name, total=True)
            c = ws.cell(row=row, column=2, value=value)
            c.font, c.alignment = _FONT, Alignment(horizontal="left")
            if isinstance(value, date):
                c.number_format = "d mmm yyyy"
            row += 1
        self.label(ws, row, "Risk rating", total=True)
        if self.literal(ws, row, 2, info["risk_rating"]):
            ws.cell(row=row, column=2).alignment = Alignment(horizontal="left")
        row += 2
        self.header(ws, row, ["Loan", "Type", "Maturity", "Commitment", "Outstanding", "Availability",
                              "Margin over reference rate"], number_from=3)
        for loan in b["loans"]:
            row += 1
            self.label(ws, row, loan["name"])
            self.label(ws, row, loan["type"].replace("_", " "), col=2)
            if loan["maturity"]:
                c = ws.cell(row=row, column=3, value=date.fromisoformat(loan["maturity"]))
                c.number_format, c.font, c.alignment = "d mmm yyyy", _FONT, Alignment(horizontal="right")
            self.literal(ws, row, 4, loan["commitment"])
            self.literal(ws, row, 5, loan["outstanding"])
            self.literal(ws, row, 6, loan["availability"])
            margin = next((s for s in loan["pricing"] if is_fig(s)), None)
            self.literal(ws, row, 7, margin, number_format="0.00%")
        row += 2
        for text in ("How to read this workbook",
                     "Input cells hold stored facts. Computed lines are formulas over the input cells, so the arithmetic can be followed and rechecked.",
                     "The Sources sheet lists every figure cell with its fact, and the document, page and printed text, or the calculation and its inputs.",
                     "Amounts are whole US dollars as stored. Expenses and outflows are positive, as in the spreading template."):
            self.label(ws, row, text, total=text.startswith("How"))
            row += 1

    def statements(self) -> None:
        spread = self.b["spread"]
        periods = spread["periods"]
        cells = spread["cells"]
        for title, statements in STATEMENT_SHEETS:
            flow = statements != ("bs",)
            ws = self.sheet(title, "US dollars. " + ("Fiscal year to date. " if flow else "At the period end. ")
                            + "Computed lines are formulas over the cells above them.", [46] + [15] * len(periods))
            self.header(ws, HEADER_ROW, ["Line"] + [date.fromisoformat(p["period_end"]) for p in periods])
            row = HEADER_ROW
            if flow:
                row += 1
                self.header(ws, row, [""] + [MONTH_WORDS.get(p["months"], "") for p in periods])
            ws.freeze_panes = ws.cell(row=row + 1, column=2)
            seen_sup = False
            for line in template.template_lines(spread["template"]):
                if line.statement not in statements:
                    continue
                if line.statement == "sup" and not seen_sup:
                    seen_sup = True
                    row += 2
                    self.label(ws, row, "Supplemental, from the notes", total=True)
                row += 1
                self.label(ws, row, line.label, total=line.computed)
                for i, p in enumerate(periods):
                    iso, col = p["period_end"], i + 2
                    fact_id = cells.get(line.key, {}).get(iso)
                    address = None
                    if line.computed:
                        parts = [(sign, self.pos.get((component, iso))) for sign, component in line.formula]
                        if all(ref for _, ref in parts):
                            text = "".join(("+" if sign > 0 else "-") + ref.split("!")[1] for sign, ref in parts)
                            address = self.formula(ws, row, col, text.lstrip("+"), "usd",
                                                   f"{line.label}, {iso}", fact_id, total=True)
                        elif fact_id:
                            address = self.literal(ws, row, col, {"fig": fact_id}, total=True)
                    elif fact_id:
                        address = self.literal(ws, row, col, {"fig": fact_id})
                    if address:
                        self.pos[(line.key, iso)] = f"'{title}'!{address}"

    def _cell(self, key: str, end: date) -> str:
        ref = self.pos.get((key, end.isoformat()))
        if ref is None:
            raise _Missing(f"{key} at {end}")
        return ref

    def _expr(self, node: Any, end: date) -> str:
        """An `app.calc` expression tree as an Excel formula over the statement sheets."""
        op = node["op"]
        if op == "line":
            if node["period"] == "point":
                return self._cell(node["key"], end)
            if node["period"] != "ttm":
                raise _Missing(node["period"])
            if is_fiscal_year_end(end, self.fye):
                return self._cell(node["key"], end)
            return "(" + self._cell(node["key"], end) + "+" + self._cell(node["key"], prior_fiscal_year_end(end, self.fye)) \
                + "-" + self._cell(node["key"], _shift(end, -12)) + ")"
        if op == "const":
            return str(node["value"])
        if op == "named":
            definitions = lib.metric_definitions()
            if node["name"] not in definitions:
                raise _Missing(node["name"])
            return self._expr(definitions[node["name"]], end)
        if op in ("add", "sub", "mul"):
            sign = {"add": "+", "sub": "-", "mul": "*"}[op]
            return "(" + sign.join(self._expr(a, end) for a in node["args"]) + ")"
        if op == "div":
            return "(" + self._expr(node["num"], end) + "/" + self._expr(node["den"], end) + ")"
        if op == "shift":
            return self._expr(node["arg"], _shift(end, int(node["months"])))
        raise _Missing(op)

    def ratios(self) -> None:
        trend = self.b["trend"]
        ends = [date.fromisoformat(p) for p in trend["periods"]]
        ws = self.sheet("Ratios", "Key metrics for the last eight quarters. Flow lines are trailing twelve months. "
                        "Each cell is a formula over the statement sheets, rounded as the calculation engine rounds.",
                        [38] + [15] * len(ends))
        self.header(ws, HEADER_ROW, ["Metric"] + ends)
        ws.freeze_panes = ws.cell(row=HEADER_ROW + 1, column=2)
        row = HEADER_ROW
        for metric in trend["rows"]:
            row += 1
            self.label(ws, row, metric["label"])
            name, unit = metric["metric"], metric["unit"]
            node = EXTRA[name][0] if name in EXTRA else lib.METRICS[name].expr if name in lib.METRICS else None
            for i, end in enumerate(ends):
                figure = metric["cells"][i]
                if not figure:
                    continue
                try:
                    if node is None:
                        raise _Missing(name)
                    text = f"ROUND({self._expr(node, end)},{ROUND_DP[unit]})"
                except _Missing:
                    self.literal(ws, row, i + 2, figure)
                    continue
                self.formula(ws, row, i + 2, text, unit, self.facts[figure["fig"]]["label"], figure["fig"])

    def covenants(self) -> None:
        ws = self.sheet("Covenants", "Every covenant test to date. Calculated by code from approved terms; the "
                        "certificate figure is shown beside it.", [14, 34, 14, 12, 14, 12, 14, 36])
        self.header(ws, HEADER_ROW, ["Period end", "Covenant", "Calculated", "Test", "Required", "Cushion",
                                     "Certificate", "Outcome"], number_from=3)
        ws.freeze_panes = ws.cell(row=HEADER_ROW + 1, column=3)
        row = HEADER_ROW
        for test in sorted(self.b["covenant_history"], key=lambda t: (t["period_end"], t["covenant"]), reverse=True):
            row += 1
            c = ws.cell(row=row, column=1, value=date.fromisoformat(test["period_end"]))
            c.number_format, c.font, c.alignment = "d mmm yyyy", _FONT, Alignment(horizontal="left")
            self.label(ws, row, test["covenant"], col=2)
            self.literal(ws, row, 3, test["value"])
            op = ws.cell(row=row, column=4, value=OPERATOR_WORDS.get(test["operator"], test["operator"] or ""))
            op.font, op.alignment = _FONT, Alignment(horizontal="right")
            self.literal(ws, row, 5, test["threshold"])
            self.literal(ws, row, 6, test["headroom_pct"])
            self.literal(ws, row, 7, test["reported"])
            word, colour = OUTCOME_WORDS.get(test["outcome"], (test["outcome"], style.INK_900))
            out = ws.cell(row=row, column=8, value=word)
            out.font = Font(name=style.FONT, size=10, bold=True, color=colour)
        ws.auto_filter.ref = f"A{HEADER_ROW}:H{row}"

    def borrowing_base(self) -> None:
        bb = self.b["borrowing_base"]
        if not bb:
            return
        word, _ = style.BB_OUTCOME_WORDS.get(bb["outcome"], (bb["outcome"], style.INK_900))
        ws = self.sheet("Borrowing base", f"Recalculated beside the borrower's certificate as of {bb['as_of']}. "
                        f"Result: {word.lower()}. The difference column is a formula.", [44, 18, 18, 18, 16])
        self.header(ws, HEADER_ROW, ["Line", "Recalculated", "Certificate", "Difference", "Status"])
        ws.freeze_panes = ws.cell(row=HEADER_ROW + 1, column=2)
        row = HEADER_ROW
        for line in bb["lines"]:
            row += 1
            self.label(ws, row, line["label"], total=line["total"])
            a = self.literal(ws, row, 2, line["computed"], total=line["total"])
            b = self.literal(ws, row, 3, line["certificate"], total=line["total"])
            if a and b:
                self.formula(ws, row, 4, f"{a}-{b}", "usd", f"{line['label']}, recalculated less certificate",
                             line["difference"]["fig"] if line["difference"] else None, total=line["total"])
            status = line["status"] or ""
            c = ws.cell(row=row, column=5, value={"match": "Agrees", "mismatch": "Differs"}.get(status, status.replace("_", " ")))
            c.font = Font(name=style.FONT, size=10, bold=status == "mismatch",
                          color=style.AMBER if status == "mismatch" else style.INK_700)
            c.alignment = Alignment(horizontal="right")

    def sources_sheet(self) -> set[str]:
        ws = self.sheet(SOURCES_SHEET, "Every figure cell in this workbook, with the stored fact behind it. A formula "
                        "cell names the fact its result must equal.", [18, 8, 46, 38, 12, 11, 38, 7, 90])
        self.header(ws, HEADER_ROW, list(SOURCE_COLUMNS), number_from=99)
        ws.freeze_panes = ws.cell(row=HEADER_ROW + 1, column=1)
        used: set[str] = set()
        for n, (sheet, cell, item, fact_id, role) in enumerate(self.sources, start=HEADER_ROW + 1):
            d = describe_source(self.facts[fact_id], self.facts) if fact_id else None
            if fact_id:
                used.add(fact_id)
            values = [sheet, cell, item, fact_id, d["kind"] if d else "formula", role,
                      d["document"] if d else "", d["page"] if d else "",
                      d["detail"] if d else "Derived by the formula in this cell from the input cells it names"]
            for col, value in enumerate(values, start=1):
                c = ws.cell(row=n, column=col, value=value)
                c.font = _FONT
                c.alignment = Alignment(vertical="top", wrap_text=col == 9)
        ws.auto_filter.ref = f"A{HEADER_ROW}:I{HEADER_ROW + len(self.sources)}"
        return used


def render_workbook(content: dict[str, Any], b: dict[str, Any]) -> tuple[bytes, set[str]]:
    book = _Book(content, b)
    book.summary()
    book.statements()
    book.ratios()
    book.covenants()
    book.borrowing_base()
    used = book.sources_sheet()
    book.wb.properties.title = f"{b['borrower']['name']}: credit review workbook, {b['period_end']}"
    book.wb.properties.creator = style.LENDER
    out = io.BytesIO()
    book.wb.save(out)
    return out.getvalue(), used
