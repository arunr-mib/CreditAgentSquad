"""Renderers for the innovation book's documents. Reuses the shared page template in synthetic.render.common."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from reportlab.lib.units import inch
from reportlab.platypus import KeepTogether, PageBreak, Spacer, Table, TableStyle

from synthetic.books.innovation.layout import BALANCE, CASHFLOW, INCOME, LABELS, OUTFLOWS, SUPPLEMENTAL
from synthetic.render import common
from synthetic.render.common import (
    COVER_LINE,
    COVER_TITLE,
    HEADING,
    RULE,
    SMALL,
    SUBTITLE,
    TITLE,
    Mark,
    accounting,
    para,
    style,
)
from synthetic.render.statements import _auditor_report

D = Decimal
CELL = style("cell", size=8.5, leading=10.5)
LENDER = "Bank of Stoic"
WORDS = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six", 7: "Seven", 8: "Eight", 9: "Nine", 10: "Ten",
         11: "Eleven", 12: "Twelve"}


def long_date(d: date) -> str:
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def usd(value) -> str:
    v = int(value)
    return f"(${abs(v):,})" if v < 0 else f"${v:,}"


def _grid(total_rows=(), header=True, size=9):
    styles = [("FONT", (0, 0), (-1, -1), "Helvetica", size), ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
              ("VALIGN", (0, 0), (-1, -1), "BOTTOM"), ("TOPPADDING", (0, 0), (-1, -1), 2.4),
              ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6)]
    if header:
        styles += [("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8.5), ("LINEBELOW", (0, 0), (-1, 0), 0.6, RULE)]
    for r in total_rows:
        styles += [("FONT", (0, r), (-1, r), "Helvetica-Bold", size), ("LINEABOVE", (1, r), (-1, r), 0.6, RULE)]
    return styles


def _table(rows, widths, total_rows=(), header=True):
    t = Table(rows, colWidths=widths, hAlign="LEFT")
    t.setStyle(TableStyle(_grid(total_rows, header)))
    return t


class _Sheet:
    """Builds statement tables and remembers what was printed where."""

    def __init__(self, labels: dict[str, str]):
        self.labels, self.marks, self.keys = labels, {}, {}

    def table(self, section: str, layout, headers, now: dict, before: dict) -> list:
        data, styles = [["", *headers]], []
        printed = self.keys.setdefault(section, {})
        for kind, key in layout:
            r = len(data)
            if kind == "head":
                data.append([key, "", ""])
                styles += [("FONT", (0, r), (0, r), "Helvetica-Bold", 9.5), ("TOPPADDING", (0, r), (-1, r), 7)]
                continue
            sign = -1 if key in OUTFLOWS else 1
            a, b = accounting(D(now[key] * sign)), accounting(D(before[key] * sign))
            label = self.labels.get(key, LABELS[key])
            data.append([label, a, b])
            printed[key] = (label, a, b)
            if kind == "line":
                styles.append(("LEFTPADDING", (0, r), (0, r), 16))
            else:
                styles += [("FONT", (0, r), (-1, r), "Helvetica-Bold", 9.5), ("LINEABOVE", (1, r), (-1, r), 0.6, RULE)]
        t = Table(data, colWidths=[3.95 * inch, 1.3 * inch, 1.3 * inch], hAlign="LEFT")
        t.setStyle(TableStyle(_grid(header=True, size=9.5) + styles))
        return [Mark(self.marks, section), t]

    def figures(self) -> dict:
        return {k: {"page": self.marks[s], "label": lab, "printed": a}
                for s, keys in self.keys.items() for k, (lab, a, _) in keys.items()}


def _head(spec_name: str, statement: str, line: str) -> list:
    return [para(spec_name, TITLE), para(statement, SUBTITLE), para(line, SUBTITLE),
            para("(in U.S. dollars)", SMALL), Spacer(1, 8)]


def _supplemental_page(spec, sheet: _Sheet, line: str, heading: str, head_now: str, head_before: str,
                       now: dict, before: dict) -> list:
    """Cash paid for interest and scheduled principal, so a reader can map them to the sup.* lines."""
    story = _head(spec.name, heading, line)
    story += sheet.table("supplemental", SUPPLEMENTAL, (head_now, head_before), now, before)
    story += [Spacer(1, 10), para("Scheduled principal payments are the contractual installments paid on the venture term "
                                  "loan during the period and exclude voluntary prepayments. The venture term loan is "
                                  "interest-only, so none is scheduled in these periods. A dash indicates nil.", SMALL)]
    return story


def render_monthly_financials(path: Path, spec, payload: dict, title: str) -> dict:
    end, months = payload["end"], payload["months"]
    sheet = _Sheet(payload.get("labels", {}))
    ytd_head = f"{WORDS[months]} month{'s' if months > 1 else ''} ended\n{long_date(end)}"
    month_head = f"One month ended\n{long_date(end)}"
    point_head = (f"{long_date(end)}", f"{long_date(payload['prior_end'])}")
    line = f"For the month ended {long_date(end)}, with year to date"
    story = [*_head(spec.name, "Management Financial Statements (Unaudited)", line)]
    story += [para("Balance Sheet", HEADING)] + sheet.table("balance_sheet", BALANCE, point_head, payload["balances"], payload["prior"])
    story.append(PageBreak())
    story += _head(spec.name, "Statement of Operations", line)
    story += sheet.table("income_statement", INCOME, (ytd_head, month_head), payload["ytd"], payload["month"])
    story.append(PageBreak())
    story += _head(spec.name, "Statement of Cash Flows", line)
    story += sheet.table("cash_flow", CASHFLOW, (ytd_head, month_head), payload["ytd"], payload["month"])
    story.append(PageBreak())
    story += _supplemental_page(spec, sheet, line, "Supplemental cash flow information", ytd_head, month_head,
                                payload["ytd"], payload["month"])
    story.append(PageBreak())
    roll = payload["software_roll"]
    story += _head(spec.name, "Note 1 - Capitalised software", line)
    story += [_table([["", "Month ended"], ["Balance at start of month", usd(roll["opening"])],
                      ["Additions (capitalised development)", usd(roll["additions"])],
                      ["Amortisation", usd(-roll["amortisation"])], ["Balance at end of month", usd(roll["closing"])]],
                     [3.95 * inch, 1.3 * inch], total_rows=(4,)), Spacer(1, 8)]
    story.append(para("Prepared by management from the books of the Company. Not audited or reviewed. Amounts are in "
                      "whole U.S. dollars.", SMALL))
    pages = common.build_pdf(path, title, f"{spec.name} | Management financials {end.isoformat()}", spec.name, story)
    return {"pages": pages, "extra": {"scale": 1, "page_map": dict(sheet.marks), "figures": sheet.figures(),
                                      "months": months, "period_basis": "fiscal_year_to_date"}}


def render_annual_statements(path: Path, spec, payload: dict, title: str) -> dict:
    end, prior = payload["end"], payload["prior_end"]
    sheet = _Sheet({})
    head = (f"Year ended\n{long_date(end)}", f"Year ended\n{long_date(prior)}")
    point = (long_date(end), long_date(prior))
    line = f"For the years ended December 31, {end.year} and {prior.year}"
    story = [Spacer(1, 1.6 * inch), para(spec.name, COVER_TITLE), para("Audited Financial Statements", COVER_LINE),
             para(f"December 31, {end.year} and {prior.year}", COVER_LINE),
             para(f"With Independent Auditor's Report of {spec.auditor}", COVER_LINE), PageBreak()]
    story += _auditor_report(spec, end, prior) + [PageBreak()]
    story += _head(spec.name, "Balance Sheets", line) + sheet.table("balance_sheet", BALANCE, point, payload["balances"], payload["prior_balances"])
    story.append(PageBreak())
    story += _head(spec.name, "Statements of Operations", line) + sheet.table("income_statement", INCOME, head, payload["flows"], payload["prior_flows"])
    story.append(PageBreak())
    story += _head(spec.name, "Statements of Cash Flows", line) + sheet.table("cash_flow", CASHFLOW, head, payload["flows"], payload["prior_flows"])
    story.append(PageBreak())
    story += _supplemental_page(spec, sheet, line, "Note 1 - Supplemental cash flow information", *head,
                                payload["flows"], payload["prior_flows"])
    pages = common.build_pdf(path, title, f"{spec.name} | FY{end.year}", spec.name, story)
    return {"pages": pages, "extra": {"scale": 1, "quality": "audited", "page_map": dict(sheet.marks),
                                      "figures": sheet.figures(), "comparative_period_end": prior}}


def _opt(value, fmt) -> str:
    return "n/a" if value is None else fmt(value)


def render_mrr_report(path: Path, spec, payload: dict, title: str) -> dict:
    end, marks = payload["end"], {}
    w = [3.4 * inch, 1.6 * inch]
    summary = [["Metric", f"As of {long_date(end)}"], ["Monthly recurring revenue (MRR)", usd(payload["mrr"])],
               ["Annual recurring revenue (ARR)", usd(payload["arr"])], ["Net new ARR in the month", _opt(payload["net_new_arr"], usd)],
               ["Customers", f"{payload['customers']:,}"], ["Net revenue retention, trailing 12 months", _opt(payload["nrr"], lambda v: f"{v}%")]]
    bridge = [["MRR bridge", "Month ended"], ["Opening MRR", usd(payload["opening"])], ["New customers", usd(payload["new"])],
              ["Expansion", usd(payload["expansion"])], ["Contraction", usd(-payload["contraction"])],
              ["Churn", usd(-payload["churn"])], ["Closing MRR", usd(payload["mrr"])]]
    trend = [["Month", "MRR", "Customers"]] + [[m, usd(v), f"{c:,}"] for m, v, c in payload["trend"]]
    story = [Mark(marks, "summary"), para("MONTHLY RECURRING REVENUE REPORT", TITLE), para(spec.name, SUBTITLE),
             para(f"For the month ended {long_date(end)}", SUBTITLE), Spacer(1, 8), _table(summary, w), Spacer(1, 10),
             Mark(marks, "bridge"), _table(bridge, w, total_rows=(6,)), Spacer(1, 10), Mark(marks, "trend"),
             para("Trailing six months", HEADING), _table(trend, [2.0 * inch, 1.5 * inch, 1.1 * inch]),
             Spacer(1, 8), para("MRR is the contracted monthly subscription charge for active customers at month end. "
                                "ARR is twelve times MRR.", SMALL)]
    pages = common.build_pdf(path, title, f"{spec.name} | MRR report {end.isoformat()}", spec.name, story)
    figs = {"saas.mrr": {"page": marks["summary"], "label": "Monthly recurring revenue (MRR)", "printed": usd(payload["mrr"])},
            "saas.arr": {"page": marks["summary"], "label": "Annual recurring revenue (ARR)", "printed": usd(payload["arr"])},
            "saas.customers": {"page": marks["summary"], "label": "Customers", "printed": f"{payload['customers']:,}"}}
    if payload["net_new_arr"] is not None:
        figs["saas.net_new_arr"] = {"page": marks["summary"], "label": "Net new ARR in the month",
                                    "printed": usd(payload["net_new_arr"])}
    if payload["nrr"] is not None:
        figs["saas.net_revenue_retention"] = {"page": marks["summary"], "label": "Net revenue retention, trailing 12 months",
                                              "printed": f"{payload['nrr']}%"}
    return {"pages": pages, "extra": {"page_map": marks, "figures": figs}}


def render_bank_statement(path: Path, spec, payload: dict, title: str) -> dict:
    end, marks = payload["end"], {}
    first = date(end.year, end.month, 1)
    rows = [["Account", "Opening", "Credits", "Debits", "Closing"]]
    for a in payload["accounts"]:
        rows.append([f"{a['name']} (ending {a['tail']})" + (" - RESTRICTED" if a["restricted"] else ""),
                     _opt(a["opening"], usd), _opt(a["credits"], usd), _opt(a["debits"], lambda v: usd(-v)),
                     _opt(a["closing"], usd)])
    def total(restricted: bool):
        closings = [a["closing"] for a in payload["accounts"] if a["restricted"] == restricted]
        return None if any(c is None for c in closings) else sum(closings)

    free, held = total(False), total(True)
    both = None if free is None or held is None else free + held
    totals = [["Total operating accounts (unrestricted)", _opt(free, usd)],
              ["Total pledged and restricted accounts", _opt(held, usd)], ["Total balances on deposit", _opt(both, usd)]]
    story = [Mark(marks, "summary"), para("STATEMENT OF ACCOUNT", TITLE), para(f"{LENDER} - Business Banking", SUBTITLE),
             para(f"Account holder: {spec.name}", SUBTITLE),
             para(f"Statement period: {long_date(first)} to {long_date(end)}", SUBTITLE), Spacer(1, 8),
             Table(rows, colWidths=[2.9 * inch, 0.95 * inch, 0.95 * inch, 0.95 * inch, 0.95 * inch], hAlign="LEFT",
                   style=TableStyle(_grid(size=8.5))), Spacer(1, 10), Mark(marks, "totals"),
             _table([["Summary", ""], *totals], [3.4 * inch, 1.6 * inch], total_rows=(3,), header=True)]
    for note in payload["notes"]:
        story += [Spacer(1, 8), para(note, SMALL)]
    pages = common.build_pdf(path, title, f"{spec.name} | Account statement {end.isoformat()}", LENDER, story)
    figs = {}
    if free is not None:
        figs["bs.cash_unrestricted"] = {"page": marks["totals"], "label": "Total operating accounts (unrestricted)",
                                        "printed": usd(free)}
    if held is not None:
        figs["bs.cash_restricted"] = {"page": marks["totals"], "label": "Total pledged and restricted accounts",
                                      "printed": usd(held)}
    return {"pages": pages, "extra": {"page_map": marks, "figures": figs}}


def render_monthly_certificate(path: Path, spec, payload: dict, title: str) -> dict:
    end, marks = payload["end"], {}
    reported = payload["reported"]
    failing = [payload["names"][c] for c, r in reported.items() if not r["in_compliance"]]
    statement = (f"As of {long_date(end)}, the Borrower was not in compliance with: {', '.join(failing)}. The Borrower "
                 "was in compliance with each other financial covenant." if failing else
                 f"As of {long_date(end)}, the Borrower was in compliance with each of the financial covenants set "
                 "forth in Article 6 of the Credit Agreement.")
    rows = [["Covenant", "Section", "Required", "Actual", "In compliance"]]
    for i, (cid, r) in enumerate(reported.items(), start=1):
        rows.append([para(payload["names"][cid], CELL), f"6.{i}", para(r["required_text"], CELL),
                     para(r["actual_text"], CELL), "Yes" if r["in_compliance"] else "No"])
    story = [Mark(marks, "summary"), para("MONTHLY COMPLIANCE CERTIFICATE", TITLE), para(spec.name, SUBTITLE),
             para(f"For the month ended {long_date(end)}", SUBTITLE), Spacer(1, 8), para(f"To: {LENDER}"),
             para(f"Date: {long_date(payload['document_date'])}"),
             para("This certificate is delivered under Section 5.1(c) of the Credit Agreement. The undersigned, the chief "
                  "financial officer of the Borrower, certifies that the covenant calculations in Schedule 1 are true and correct."),
             para(statement), Spacer(1, 6),
             Table(rows, colWidths=[1.9 * inch, 0.5 * inch, 1.5 * inch, 2.0 * inch, 0.7 * inch], hAlign="LEFT",
                   style=TableStyle(_grid(size=8.5))), Spacer(1, 6),
             para("Dollar amounts in this certificate are presented in whole U.S. dollars.", SMALL), Spacer(1, 10), para(spec.name.upper()),
             para(f"By: /s/ {payload['signed_by']}"), para("Title: Chief Financial Officer"), PageBreak(),
             Mark(marks, "calculations"), para("Schedule 1 - Covenant Calculations", TITLE),
             para(f"{spec.name} - as of and for the month ended {long_date(end)}", SUBTITLE), Spacer(1, 6)]
    for i, (cid, r) in enumerate(reported.items(), start=1):
        calc = [[label, text] for label, text in r["calculation"]]
        calc += [[payload["names"][cid], r["actual_text"]], ["Requirement", r["required_text"]],
                 ["In compliance", "Yes" if r["in_compliance"] else "No"]]
        story.append(KeepTogether([para(f"Section 6.{i} - {payload['names'][cid]}", HEADING),
                                   _table(calc, [4.4 * inch, 1.9 * inch], total_rows=(len(calc) - 3,), header=False), Spacer(1, 6)]))
    pages = common.build_pdf(path, title, f"{spec.name} | Compliance certificate {end.isoformat()}", spec.name, story)
    return {"pages": pages, "extra": {"scale": 1, "page_map": marks}}


def render_notice(path: Path, spec, payload: dict, title: str) -> dict:
    """Term sheet and investor update: titled paragraphs and an optional table."""
    marks: dict = {}
    story = [Mark(marks, "start"), para(payload["heading"], TITLE), para(spec.name, SUBTITLE),
             para(payload["subheading"], SUBTITLE), Spacer(1, 8)]
    for head, text in payload["sections"]:
        story += [para(head, HEADING), para(text)]
    if payload.get("table"):
        story += [Spacer(1, 6), _table(payload["table"], [3.0 * inch, 1.8 * inch])]
    story.append(para(payload["closing"], SMALL))
    pages = common.build_pdf(path, title, f"{spec.name} | {payload['footer']}", spec.name, story)
    return {"pages": pages, "extra": {"page_map": marks}}


def render_export_print(path: Path, rows: list[tuple[str, int, int]]) -> dict:
    """A print of mrr_export.xlsx: no company name, no title, the sheet as it came."""
    data = [["month", "mrr_usd", "customers"]] + [[m, f"{v:,}", f"{c:,}"] for m, v, c in rows]
    story = [_table(data, [1.6 * inch, 1.4 * inch, 1.2 * inch])]
    pages = common.build_pdf(path, "mrr_export", "mrr_export.xlsx | sheet: export", "", story)
    return {"pages": pages, "extra": {"intake_form": "pdf_print_of_xlsx"}}


def write_export_workbook(path: Path, rows: list[tuple[str, int, int]]) -> str:
    """The real mrr_export.xlsx. Returns the text of its cells (hashed for the manifest)."""
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "export"
    ws.append(["month", "mrr_usd", "customers"])
    for row in rows:
        ws.append(list(row))
    ws.append([])
    ws.append(["SYNTHETIC - FOR DEMONSTRATION"])
    ws.oddFooter.center.text = "SYNTHETIC - FOR DEMONSTRATION"
    wb.properties.creator = ""
    wb.properties.title = "export"
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return "\n".join(",".join(str(c) for c in r) for r in ([["month", "mrr_usd", "customers"], *rows, [], ["SYNTHETIC - FOR DEMONSTRATION"]]))
