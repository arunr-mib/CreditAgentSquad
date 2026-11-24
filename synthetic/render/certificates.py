"""Compliance certificates and borrowing base certificates, as delivered by the borrower."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from reportlab.lib.units import inch
from reportlab.platypus import KeepTogether, PageBreak, Spacer, Table, TableStyle

from synthetic.render import common
from synthetic.render.common import (
    BODY,
    HEADING,
    RULE,
    SMALL,
    SOFT,
    SUBTITLE,
    TITLE,
    Mark,
    accounting,
    para,
    scaled,
)
from synthetic.scenarios import LENDER, BorrowerSpec

D = Decimal


def _long(d: date) -> str:
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def _grid(first_bold: bool = True, total_rows: tuple[int, ...] = ()) -> list:
    styles = [
        ("FONT", (0, 0), (-1, -1), "Helvetica", 9),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.8),
    ]
    if first_bold:
        styles += [("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8.5), ("LINEBELOW", (0, 0), (-1, 0), 0.6, RULE)]
    for r in total_rows:
        styles += [("FONT", (0, r), (-1, r), "Helvetica-Bold", 9), ("LINEABOVE", (1, r), (-1, r), 0.6, RULE)]
    return styles


def _requirement(operator: str, unit: str, threshold: Decimal, scale: int) -> str:
    words = "Not less than" if operator == ">=" else "Not more than"
    shown = common.ratio(threshold) if unit == "ratio" else accounting(scaled(threshold, scale))
    return f"{words} {shown}"


def _actual(unit: str, value: Decimal, scale: int) -> str:
    return common.ratio(value) if unit == "ratio" else accounting(scaled(value, scale))


def render_compliance_certificate(
    path: Path, spec: BorrowerSpec, certificate: dict, covenants: list[dict], doc_date: date, title: str
) -> dict:
    end, scale = certificate["period_end"], certificate["scale"]
    reported = certificate["reported"]
    sections = {c["id"]: f"6.{i}" for i, c in enumerate(covenants, start=1)}
    by_id = {c["id"]: c for c in covenants}
    failing = [by_id[cid]["name"] for cid, r in reported.items() if not r["in_compliance"]]
    marks: dict = {}
    scale_words = "thousands of U.S. dollars" if scale == 1000 else "whole U.S. dollars"
    if failing:
        statement = (
            f"As of {_long(end)}, the Borrower was not in compliance with the following financial covenant: "
            f"{', '.join(failing)}. The Borrower was in compliance with each other financial covenant set "
            "forth in Article 6 of the Credit Agreement."
        )
        default_clause = (
            "(b) except for the covenant non-compliance described below, no Default or Event of Default has "
            "occurred and is continuing; and"
        )
    else:
        statement = (
            f"As of {_long(end)}, the Borrower was in compliance with each of the financial covenants set "
            "forth in Article 6 of the Credit Agreement."
        )
        default_clause = "(b) no Default or Event of Default has occurred and is continuing; and"
    summary = [["Covenant", "Section", "Required", "Actual", "In compliance"]]
    for cid, r in reported.items():
        test = by_id[cid]["test"]
        summary.append(
            [
                by_id[cid]["name"],
                sections[cid],
                _requirement(test["operator"], r["unit"], r["threshold"], scale),
                _actual(r["unit"], r["value"], scale),
                "Yes" if r["in_compliance"] else "No",
            ]
        )
    summary_table = Table(summary, colWidths=[2.55 * inch, 0.65 * inch, 1.55 * inch, 1.0 * inch, 0.95 * inch], hAlign="LEFT")
    summary_table.setStyle(TableStyle(_grid() + [("LINEBELOW", (0, 1), (-1, -1), 0.3, SOFT)]))
    story: list = [
        Mark(marks, "summary"),
        para("COMPLIANCE CERTIFICATE", TITLE),
        para(spec.name, SUBTITLE),
        para(f"For the fiscal quarter ended {_long(end)}", SUBTITLE),
        Spacer(1, 10),
        para(f"To: {LENDER}"),
        para(f"Date: {_long(doc_date)}"),
        para(
            f"This Compliance Certificate is delivered pursuant to Section 5.1(c) of the Credit Agreement dated "
            f"as of {_long(spec.closing_date)} (as amended, the Credit Agreement) between {spec.name} (the "
            f"Borrower) and {LENDER} (the Lender). Capitalized terms used in this certificate have the "
            "meanings given to them in the Credit Agreement."
        ),
        para(
            "The undersigned, the chief financial officer of the Borrower, certifies in that capacity that: "
            "(a) the financial statements delivered for the period fairly present, in all material respects, "
            f"the financial condition and results of operations of the Borrower; {default_clause} (c) the "
            "covenant calculations set out in Schedule 1 are true and correct."
        ),
        para(statement),
        Spacer(1, 6),
        summary_table,
        Spacer(1, 6),
        para(f"Dollar amounts in this certificate are presented in {scale_words}.", SMALL),
        Spacer(1, 18),
        para(spec.name.upper()),
        para(f"By: /s/ {certificate['signed_by']}"),
        para(f"Name: {certificate['signed_by']}"),
        para("Title: Chief Financial Officer"),
        PageBreak(),
        Mark(marks, "calculations"),
        para("Schedule 1 - Covenant Calculations", TITLE),
        para(f"{spec.name} - as of and for the four fiscal quarters ended {_long(end)}", SUBTITLE),
        para(f"(in {scale_words}, except ratios)", SMALL),
        Spacer(1, 6),
    ]
    for cid, r in reported.items():
        test = by_id[cid]["test"]
        rows = [[line["label"], accounting(scaled(line["amount"], scale))] for line in r["calculation"]]
        rows.append([by_id[cid]["name"], _actual(r["unit"], r["value"], scale)])
        rows.append(["Requirement", _requirement(test["operator"], r["unit"], r["threshold"], scale)])
        rows.append(["In compliance", "Yes" if r["in_compliance"] else "No"])
        table = Table(rows, colWidths=[4.4 * inch, 1.9 * inch], hAlign="LEFT")
        table.setStyle(
            TableStyle(_grid(first_bold=False, total_rows=(len(rows) - 3,)) + [("LEFTPADDING", (0, 0), (0, -4), 16)])
        )
        story.append(KeepTogether([para(f"Section {sections[cid]} - {by_id[cid]['name']}", HEADING), table, Spacer(1, 6)]))
    pages = common.build_pdf(path, title, f"{spec.name} | Compliance certificate {end.isoformat()}", spec.name, story)
    return {"pages": pages, "extra": {"scale": scale, "page_map": marks}}


_BB_ROWS = (
    ("head", "Accounts receivable"),
    ("gross_ar", "Gross accounts receivable per aging"),
    ("ineligible_excluded", "Less: affiliate, foreign and government accounts"),
    ("ineligible_over_age", "Less: invoices more than 90 days past invoice date"),
    ("ineligible_cross_aging", "Less: cross-aged accounts"),
    ("ineligible_contra", "Less: contra accounts"),
    ("ineligible_concentration", "Less: concentration in excess of limit"),
    ("total_ineligible_ar", "Total ineligible accounts"),
    ("eligible_ar", "Eligible Accounts"),
    ("rate_ar", "Advance rate"),
    ("ar_availability", "Accounts receivable availability"),
    ("head", "Inventory"),
    ("gross_inventory", "Gross inventory"),
    ("ineligible_inventory", "Less: ineligible inventory"),
    ("eligible_inventory", "Eligible Inventory"),
    ("rate_inventory", "Advance rate"),
    ("inventory_availability_before_sublimit", "Inventory availability before sublimit"),
    ("sublimit", "Inventory sublimit"),
    ("inventory_availability", "Inventory availability"),
    ("head", "Borrowing base and availability"),
    ("reserves", "Less: Reserves"),
    ("borrowing_base", "Borrowing Base"),
    ("commitment", "Revolving Commitment"),
    ("lesser_of_base_and_commitment", "Lesser of Borrowing Base and Revolving Commitment"),
    ("outstanding", "Revolving Loans outstanding"),
    ("letters_of_credit", "Letters of credit outstanding"),
    ("availability", "Availability (over-advance)"),
)
_BOLD_BB = ("eligible_ar", "ar_availability", "eligible_inventory", "inventory_availability", "borrowing_base", "availability")
_CATEGORY_NOTE = {"intercompany": "Affiliate", "foreign": "Foreign", "government": "Government", "trade": ""}
_INVENTORY_WORDS = {
    "raw_materials": "Raw materials",
    "work_in_process": "Work in process",
    "finished_goods": "Finished goods",
    "consigned": "Inventory held on consignment",
}


def render_borrowing_base_certificate(
    path: Path, spec: BorrowerSpec, entry: dict, bb_terms: dict, doc_date: date, title: str
) -> dict:
    end, cert = entry["period_end"], entry["certificate"]
    ar = next(c for c in bb_terms["components"] if c["collateral"] == "accounts_receivable")
    inv = next(c for c in bb_terms["components"] if c["collateral"] == "inventory")
    marks: dict = {}
    rows, bold, heads = [["", "Amount"]], [], []
    for key, label in _BB_ROWS:
        r = len(rows)
        if key == "head":
            rows.append([label, ""])
            heads.append(r)
        elif key == "rate_ar":
            rows.append([label, f"{D(ar['advance_rate']) * 100:.0f}%"])
        elif key == "rate_inventory":
            rows.append([label, f"{D(inv['advance_rate']) * 100:.0f}%"])
        elif key == "sublimit":
            rows.append([label, accounting(D(inv["sublimit"]))])
        else:
            rows.append([label, accounting(cert[key])])
            if key in _BOLD_BB:
                bold.append(r)
    summary = Table(rows, colWidths=[4.6 * inch, 1.7 * inch], hAlign="LEFT")
    summary.setStyle(
        TableStyle(
            _grid(total_rows=tuple(bold))
            + [("FONT", (0, r), (0, r), "Helvetica-Bold", 9) for r in heads]
            + [("TOPPADDING", (0, r), (-1, r), 7) for r in heads]
            + [("LEFTPADDING", (0, r), (0, r), 16) for r in range(1, len(rows)) if r not in heads]
        )
    )
    over = cert["availability"] < 0
    story: list = [
        Mark(marks, "summary"),
        para("BORROWING BASE CERTIFICATE", TITLE),
        para(spec.name, SUBTITLE),
        para(f"As of {_long(end)}", SUBTITLE),
        para("(in U.S. dollars)", SMALL),
        Spacer(1, 6),
        para(f"To: {LENDER}        Date: {_long(doc_date)}"),
        summary,
        Spacer(1, 8),
        para(
            "The undersigned certifies that the information in this Borrowing Base Certificate and the "
            "attached accounts receivable aging and inventory report is true and correct as of the date "
            "shown and has been prepared in accordance with the Credit Agreement."
            + (
                " The Borrower acknowledges that Revolving Loans outstanding exceed the Borrowing Base as of "
                "the date shown."
                if over
                else ""
            ),
            SMALL,
        ),
        para(f"By: /s/ {spec.cfo}, Chief Financial Officer", BODY),
        PageBreak(),
        Mark(marks, "ar_aging"),
        para("Accounts Receivable Aging by Customer", TITLE),
        para(f"{spec.name} - as of {_long(end)}", SUBTITLE),
        para("(in U.S. dollars; aged from invoice date)", SMALL),
        Spacer(1, 6),
    ]
    aging = [["Customer", "0-30 days", "31-60 days", "61-90 days", "Over 90 days", "Total", "Note"]]
    totals = [D(0)] * 5
    for row in entry["ar_aging"]:
        b = row["buckets"]
        values = [b["0_30"], b["31_60"], b["61_90"], b["over_90"], row["total"]]
        totals = [t + v for t, v in zip(totals, values, strict=True)]
        note = _CATEGORY_NOTE[row["category"]]
        if row["contra"] > 0:
            note = f"Contra {accounting(row['contra'])}"
        aging.append([row["customer"], *[accounting(v) for v in values], note])
    aging.append(["Total", *[accounting(t) for t in totals], ""])
    aging_table = Table(
        aging, colWidths=[2.3 * inch, 0.8 * inch, 0.78 * inch, 0.78 * inch, 0.8 * inch, 0.85 * inch, 0.9 * inch], hAlign="LEFT"
    )
    aging_table.setStyle(
        TableStyle(
            _grid(total_rows=(len(aging) - 1,))
            + [("FONT", (0, 1), (-1, -2), "Helvetica", 7.6), ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7.6),
               ("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 7.6), ("ALIGN", (6, 0), (6, -1), "LEFT"),
               ("LEFTPADDING", (6, 0), (6, -1), 8)]
        )
    )  # fmt: skip
    story += [aging_table, PageBreak(), Mark(marks, "inventory")]
    story += [
        para("Inventory Report by Category", TITLE),
        para(f"{spec.name} - as of {_long(end)}", SUBTITLE),
        para("(in U.S. dollars; lower of cost and market)", SMALL),
        Spacer(1, 6),
    ]
    stock = [["Category", "Amount"]]
    for item in entry["inventory"]:
        stock.append([_INVENTORY_WORDS[item["category"]], accounting(item["amount"])])
    stock.append(["Total inventory", accounting(sum((i["amount"] for i in entry["inventory"]), D(0)))])
    stock_table = Table(stock, colWidths=[4.6 * inch, 1.7 * inch], hAlign="LEFT")
    stock_table.setStyle(TableStyle(_grid(total_rows=(len(stock) - 1,))))
    story += [
        stock_table,
        Spacer(1, 12),
        para(
            "Work in process and inventory held on consignment are not Eligible Inventory. Inventory "
            "quantities are taken from the perpetual inventory records and were last counted at the most "
            "recent fiscal year end."
        ),
    ]
    pages = common.build_pdf(path, title, f"{spec.name} | Borrowing base certificate {end.isoformat()}", spec.name, story)
    return {"pages": pages, "extra": {"scale": 1, "page_map": marks}}
