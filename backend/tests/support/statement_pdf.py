"""Build a small, internally consistent set of statements as a PDF, and the cells a perfect
reader would report from it. Figures are printed in thousands."""
import io

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

CUR, PRIOR = "September 30, 2026", "September 30, 2025"

# (key, label, current, prior). Totals use the template's computed keys.
PAGES = {
    1: [("is.revenue", "Net revenue", "$ 48,250", "$ 45,100"),
        ("is.cogs", "Cost of goods sold", "33,775", "31,120"),
        ("is.gross_profit", "Gross profit", "14,475", "13,980"),
        ("is.sga", "Selling, general and administrative", "8,100", "7,900"),
        ("is.depreciation_amortization", "Depreciation and amortization", "1,150", "1,100"),
        ("is.other_operating_expense", "Other operating expense", "400", "380"),
        ("is.nonrecurring_expense", "Restructuring and other non-recurring charges", "620", "—"),
        ("is.operating_income", "Operating income", "4,205", "4,600"),
        ("is.interest_expense", "Interest expense", "1,200", "1,150"),
        ("is.other_income_net", "Other income (expense), net", "75", "(40)"),
        ("is.pretax_income", "Income before taxes", "3,080", "3,410"),
        ("is.income_tax_expense", "Income tax expense", "740", "820"),
        ("is.net_income", "Net income", "$ 2,340", "$ 2,590")],
    2: [("bs.cash", "Cash and equivalents", "$ 2,150", "$ 1,900"),
        ("bs.accounts_receivable", "Accounts receivable, net", "9,800", "9,100"),
        ("bs.inventory", "Inventory", "7,400", "7,000"),
        ("bs.other_current_assets", "Other current assets", "650", "600"),
        ("bs.total_current_assets", "Total current assets", "20,000", "18,600"),
        ("bs.net_ppe", "Property and equipment, net", "12,500", "12,000"),
        ("bs.intangibles", "Goodwill and intangibles", "1,500", "1,500"),
        ("bs.other_noncurrent_assets", "Other assets", "500", "450"),
        ("bs.total_assets", "Total assets", "$ 34,500", "$ 32,550"),
        ("bs.accounts_payable", "Accounts payable", "$ 6,200", "$ 5,900"),
        ("bs.accrued_liabilities", "Accrued liabilities", "1,900", "1,800"),
        ("bs.revolver", "Line of credit", "3,500", "3,000"),
        ("bs.cpltd", "Current portion of long-term debt", "1,200", "1,200"),
        ("bs.other_current_liabilities", "Other current liabilities", "400", "350"),
        ("bs.total_current_liabilities", "Total current liabilities", "13,200", "12,250"),
        ("bs.long_term_debt", "Long-term debt, net of current portion", "8,300", "9,200"),
        ("bs.other_noncurrent_liabilities", "Other liabilities", "500", "450"),
        ("bs.total_liabilities", "Total liabilities", "22,000", "21,900"),
        ("bs.total_equity", "Total equity", "12,500", "10,650"),
        ("bs.total_liabilities_and_equity", "Total liabilities and equity", "$ 34,500", "$ 32,550")],
    3: [("cf.net_income", "Net income", "$ 2,340", "$ 2,590"),
        ("cf.depreciation_amortization", "Depreciation and amortization", "1,150", "1,100"),
        ("cf.change_in_working_capital", "Changes in working capital", "(1,090)", "(600)"),
        ("cf.other_operating", "Other operating items", "50", "30"),
        ("cf.cfo", "Net cash from operating activities", "2,450", "3,120"),
        ("cf.capex", "Purchases of property and equipment", "(1,400)", "(1,250)"),
        ("cf.cfi", "Net cash from investing", "(1,400)", "(1,250)"),
        ("cf.revolver_net", "Net borrowings on line of credit", "500", "200"),
        ("cf.term_debt_repayments", "Repayments of long-term debt", "(900)", "(900)"),
        ("cf.distributions", "Distributions to owners", "(600)", "(500)"),
        ("cf.cff", "Net cash from financing", "(1,000)", "(1,200)"),
        ("cf.net_change_in_cash", "Net change in cash", "$ 50", "$ 670"),
        ("sup.cash_interest_paid", "Cash paid for interest", "1,180", "1,140"),
        ("sup.cash_taxes_paid", "Cash paid for income taxes", "700", "790"),
        ("sup.scheduled_principal", "Scheduled principal payments on term debt", "900", "900"),
        ("sup.financed_capex", "Capital expenditures financed with purchase-money debt", "—", "—")],
}
ABSENT = ["bs.subordinated_debt", "cf.other_investing", "cf.term_debt_proceeds", "cf.other_financing"]
COMPUTED = {"is.gross_profit", "is.operating_income", "is.pretax_income", "is.net_income",
            "bs.total_current_assets", "bs.total_assets", "bs.total_current_liabilities", "bs.total_liabilities",
            "bs.total_liabilities_and_equity", "cf.cfo", "cf.cfi", "cf.cff", "cf.net_change_in_cash"}
PRIOR_FYE_CASH_THOUSANDS = 2100


def build_pdf(*, scale_phrase: str = "(in thousands)") -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter, invariant=1)
    for rows in PAGES.values():
        c.setFont("Helvetica-Bold", 11)
        c.drawString(72, 740, "Harrowgate Tool & Die, Inc.")
        c.setFont("Helvetica", 9)
        if scale_phrase:
            c.drawString(72, 726, f"Unaudited, nine months ended {CUR} {scale_phrase}")
        c.drawRightString(440, 706, CUR)
        c.drawRightString(560, 706, PRIOR)
        y = 688
        for _key, label, cur, prior in rows:
            c.drawString(72, y, label)
            c.drawRightString(440, y, cur)
            c.drawRightString(560, y, prior)
            y -= 15
        c.drawString(72, 40, "SYNTHETIC - FOR DEMONSTRATION")
        c.showPage()
    c.save()
    return buf.getvalue()


def perfect_cells(column: str = "current") -> list[dict]:
    cells = []
    for page, rows in PAGES.items():
        for key, label, cur, prior in rows:
            cells.append({
                "key": ("stated." + key) if key in COMPUTED else key, "page": page,
                "printed_figure": cur if column == "current" else prior, "printed_label": label,
                "column_header": CUR if column == "current" else PRIOR})
    return cells


def perfect_answer(**overrides) -> dict:
    answer = {"scale_statement": "(in thousands)", "scale_page": 1, "cells": perfect_cells(),
              "comparative_cells": perfect_cells("comparative"), "absent_keys": list(ABSENT), "notes": []}
    answer.update(overrides)
    return answer
