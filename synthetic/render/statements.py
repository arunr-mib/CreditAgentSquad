"""Financial statement PDFs: annual audited statements and interim internal statements.

Every figure printed is the truth value divided by the document's scale, in accounting
format. The renderer returns, for each template line it printed, the page, the printed
label and the printed text, so that extraction can be graded exactly.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Spacer, Table, TableStyle

from synthetic.model import LINES, Period
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
    amount,
    para,
)
from synthetic.scenarios import LENDER, STATE_NAMES, BorrowerSpec

D = Decimal
GOODS_INDUSTRIES = ("manufacturing", "distribution", "food processing")

BS_ASSETS = [
    ("head", "ASSETS"), ("head", "Current assets"), ("line", "bs.cash"), ("line", "bs.accounts_receivable"),
    ("line", "bs.inventory"), ("line", "bs.other_current_assets"), ("total", "bs.total_current_assets"),
    ("line", "bs.net_ppe"), ("line", "bs.intangibles"), ("line", "bs.other_noncurrent_assets"),
    ("grand", "bs.total_assets"),
]  # fmt: skip
BS_LIABILITIES = [
    ("head", "LIABILITIES AND EQUITY"), ("head", "Current liabilities"), ("line", "bs.accounts_payable"),
    ("line", "bs.accrued_liabilities"), ("line", "bs.revolver"), ("line", "bs.cpltd"),
    ("line", "bs.other_current_liabilities"), ("total", "bs.total_current_liabilities"),
    ("line", "bs.long_term_debt"), ("line", "bs.subordinated_debt"), ("line", "bs.other_noncurrent_liabilities"),
    ("total", "bs.total_liabilities"), ("head", "Equity"), ("memo", "equity.paid_in_capital"),
    ("memo", "equity.retained_earnings"), ("total", "bs.total_equity"), ("grand", "bs.total_liabilities_and_equity"),
]  # fmt: skip
INCOME = [
    ("line", "is.revenue"), ("line", "is.cogs"), ("total", "is.gross_profit"), ("head", "Operating expenses"),
    ("line", "is.sga"), ("line", "is.depreciation_amortization"), ("line", "is.other_operating_expense"),
    ("line", "is.nonrecurring_expense"), ("total", "is.operating_income"), ("line", "is.interest_expense"),
    ("line", "is.other_income_net"), ("total", "is.pretax_income"), ("line", "is.income_tax_expense"),
    ("grand", "is.net_income"),
]  # fmt: skip
CASH_FLOW = [
    ("head", "Operating activities"), ("line", "cf.net_income"), ("line", "cf.depreciation_amortization"),
    ("line", "cf.change_in_working_capital"), ("line", "cf.other_operating"), ("total", "cf.cfo"),
    ("head", "Investing activities"), ("line", "cf.capex"), ("line", "cf.other_investing"), ("total", "cf.cfi"),
    ("head", "Financing activities"), ("line", "cf.revolver_net"), ("line", "cf.term_debt_proceeds"),
    ("line", "cf.term_debt_repayments"), ("line", "cf.distributions"), ("line", "cf.other_financing"),
    ("total", "cf.cff"), ("grand", "cf.net_change_in_cash"), ("memo", "cash.beginning_of_year"),
    ("memo", "cash.end_of_period"),
]  # fmt: skip
SUPPLEMENTAL = [
    ("always", "sup.cash_interest_paid"), ("always", "sup.cash_taxes_paid"), ("always", "sup.scheduled_principal"),
    ("always", "sup.financed_capex"),
]  # fmt: skip


def labels_for(spec: BorrowerSpec) -> dict[str, str]:
    """Printed labels. Most follow the template; a few vary by entity type and industry."""
    labels = {key: line.label for key, line in LINES.items()}
    llc = spec.legal_form == "llc"
    if spec.industry in GOODS_INDUSTRIES:
        labels["is.revenue"] = "Net sales"
    else:
        labels["is.cogs"] = "Cost of services"
    owners = "members'" if llc else "stockholders'"
    labels["bs.total_equity"] = f"Total {owners} equity"
    labels["bs.total_liabilities_and_equity"] = f"Total liabilities and {owners} equity"
    labels["cf.distributions"] = "Distributions to members" if llc else "Dividends paid"
    labels["equity.paid_in_capital"] = "Members' capital" if llc else "Common stock and additional paid-in capital"
    labels["equity.retained_earnings"] = "Undistributed earnings" if llc else "Retained earnings"
    labels["cash.beginning_of_year"] = "Cash and equivalents, beginning of period"
    labels["cash.end_of_period"] = "Cash and equivalents, end of period"
    return labels


def _long(d: date) -> str:
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def _months_words(months: int) -> str:
    return {3: "three months", 6: "six months", 9: "nine months", 12: "year"}[months]


def _lookup(period_values: dict, memo: dict, key: str) -> Decimal:
    if key == "cash.end_of_period":
        return period_values["bs.cash"]
    return period_values[key] if key in period_values else memo[key]


class _StatementBuilder:
    def __init__(self, spec: BorrowerSpec, current: Period, comparative: Period, comparative_values: dict | None):
        self.spec = spec
        self.current = current
        self.comparative = comparative
        self.cmp_values = comparative_values or comparative.values
        self.scale = current.scale
        self.labels = labels_for(spec)
        self.marks: dict[str, int] = {}
        self.section_keys: dict[str, dict[str, tuple[str, str, str]]] = {}
        self.absent: list[str] = []

    def table(self, section: str, rows: list[tuple[str, str]], headers: tuple[str, str]) -> list:
        data = [["", headers[0], headers[1]]]
        styles = [
            ("FONT", (0, 0), (-1, -1), "Helvetica", 9.5),
            ("FONT", (1, 0), (-1, 0), "Helvetica-Bold", 8.5),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
            ("LINEBELOW", (1, 0), (-1, 0), 0.6, RULE),
            ("TOPPADDING", (0, 0), (-1, -1), 2.2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6),
        ]
        printed = self.section_keys.setdefault(section, {})
        for kind, key in rows:
            r = len(data)
            if kind == "head":
                data.append([key, "", ""])
                styles += [("FONT", (0, r), (0, r), "Helvetica-Bold", 9.5), ("TOPPADDING", (0, r), (-1, r), 7)]
                continue
            sign = LINES[key].sign if key in LINES else 1
            now = _lookup(self.current.values, self.current.memo, key)
            before = _lookup(self.cmp_values, self.comparative.memo, key)
            if kind == "line" and now == 0 and before == 0:
                self.absent.append(key)  # an empty line is left off the statement, as real statements do
                continue
            label = self.labels[key]
            now_text, before_text = amount(now, self.scale, sign), amount(before, self.scale, sign)
            data.append([label, now_text, before_text])
            if key in LINES:
                printed[key] = (label, now_text, before_text)
            if kind in ("line", "memo", "always"):
                styles.append(("LEFTPADDING", (0, r), (0, r), 16))
            if kind in ("total", "grand"):
                styles += [("FONT", (0, r), (-1, r), "Helvetica-Bold", 9.5), ("LINEABOVE", (1, r), (-1, r), 0.6, RULE)]
            if kind == "grand":
                styles.append(("LINEBELOW", (1, r), (-1, r), 0.6, RULE, 0, None, None, 2, 2))  # double rule
        table = Table(data, colWidths=[3.95 * inch, 1.3 * inch, 1.3 * inch], hAlign="LEFT")
        table.setStyle(TableStyle(styles))
        return [Mark(self.marks, section), table]

    def header(self, statement: str, period_line: str) -> list:
        return [
            para(self.spec.name, TITLE),
            para(statement, SUBTITLE),
            para(period_line, SUBTITLE),
            para(common.scale_note(self.scale), SMALL),
            Spacer(1, 8),
        ]


def render_statements(path: Path, spec: BorrowerSpec, payload: dict, title: str) -> dict:
    """Render one set of statements. Returns pages, page map, printed figures and any defects."""
    current: Period = payload["current"]
    comparative: Period = payload["comparative"]
    audited: bool = payload["audited"]
    b = _StatementBuilder(spec, current, comparative, payload.get("comparative_values"))
    end, prior_end = current.period_end, comparative.period_end
    point_headers = (f"{end.strftime('%B')} {end.day},\n{end.year}", f"{prior_end.strftime('%B')} {prior_end.day},\n{prior_end.year}")
    span = _months_words(current.months)
    if audited:
        flow_line = f"For the years ended December 31, {end.year} and {prior_end.year}"
        basis = "Audited Financial Statements"
    else:
        flow_line = f"For the {span} ended {end.strftime('%B')} {end.day}, {end.year} and {prior_end.year}"
        basis = "Interim Financial Statements (Unaudited)"
    point_line = f"As of {end.strftime('%B')} {end.day}, {end.year} and {prior_end.year}"
    split_balance_sheet = spec.scenario == "missing_page"  # this borrower prints the balance sheet on two pages

    story: list = [Spacer(1, 1.6 * inch), para(spec.name, COVER_TITLE), para(basis, COVER_LINE)]
    story.append(para(flow_line if not audited else f"December 31, {end.year} and {prior_end.year}", COVER_LINE))
    story += [Spacer(1, 0.5 * inch), para(common.scale_note(current.scale).strip("()").capitalize(), COVER_LINE)]
    if audited:
        story.append(para(f"With Independent Auditor's Report of {spec.auditor}", COVER_LINE))
    else:
        story.append(para("Prepared by management. Not audited or reviewed.", COVER_LINE))
    story += [Spacer(1, 1.2 * inch), para(f"{spec.city}, {spec.state}", COVER_LINE), PageBreak()]

    if audited:
        story += _auditor_report(spec, end, prior_end)
        story.append(PageBreak())

    if split_balance_sheet:
        story += b.header("Balance Sheets - Assets", point_line)
        story += b.table("balance_sheet_assets", BS_ASSETS, point_headers)
        story.append(PageBreak())
        story += b.header("Balance Sheets - Liabilities and Equity", point_line)
        story += b.table("balance_sheet_liabilities", BS_LIABILITIES, point_headers)
    else:
        story += b.header("Balance Sheets", point_line)
        story += b.table("balance_sheet", BS_ASSETS + BS_LIABILITIES, point_headers)
    story.append(PageBreak())
    story += b.header("Statements of Income", flow_line)
    story += b.table("income_statement", INCOME, point_headers)
    story.append(PageBreak())
    story += b.header("Statements of Cash Flows", flow_line)
    story += b.table("cash_flow", CASH_FLOW, point_headers)
    story.append(PageBreak())
    if audited:
        story += _policy_notes(spec, end)
        story.append(PageBreak())
        story += b.header("Notes to Financial Statements (continued)", flow_line)
    else:
        story += b.header("Supplemental Information", flow_line)
    story += _debt_note(b, audited, point_headers)
    story.append(para("Supplemental cash flow information" if not audited else "Note 6 - Supplemental cash flow information", HEADING))
    story += b.table("supplemental", SUPPLEMENTAL, point_headers)
    story.append(Spacer(1, 10))
    story.append(
        para(
            "Scheduled principal payments are the contractual installments paid on term debt during the period "
            "and exclude voluntary prepayments. Capital expenditures financed with purchase-money debt are "
            "included in purchases of property and equipment and in proceeds from long-term debt.",
            SMALL,
        )
    )

    footer = f"{spec.name} | {'FY' + str(end.year) if audited else end.isoformat()}"
    pages = common.build_pdf(path, title, footer, spec.name, story)

    page_map = dict(b.marks)
    figures, comparative_printed, defects, unreadable = {}, {}, [], []
    omitted = payload.get("omit_section")
    pictured = payload.get("image_section")
    dropped_page = page_map[omitted] if omitted else None
    for section, keys in b.section_keys.items():
        page = page_map[section]
        if section == omitted:
            unreadable += list(keys)
            continue
        if dropped_page and page > dropped_page:
            page -= 1
        if section == pictured:
            unreadable += list(keys)
            continue
        for key, (label, now_text, before_text) in keys.items():
            figures[key] = {"page": page, "label": label, "printed": now_text}
            comparative_printed[key] = before_text
    if omitted:
        common.drop_page(path, dropped_page)
        defects.append({"type": "missing_page", "section": omitted, "printed_page_number": dropped_page})
        page_map = {s: (p - 1 if p > dropped_page else p) for s, p in page_map.items() if s != omitted}
        pages -= 1
    if pictured:
        common.rasterize_page(path, page_map[pictured])
        defects.append({"type": "image_only_page", "section": pictured, "page": page_map[pictured]})
    return {
        "pages": pages,
        "extra": {
            "scale": current.scale,
            "quality": current.quality,
            "comparative_period_end": prior_end,
            "page_map": page_map,
            "figures": figures,
            "comparative_printed": comparative_printed,
            "absent_keys": sorted(set(b.absent)),
            "unreadable_keys": unreadable,
            "defects": defects,
        },
    }


def _debt_note(b: _StatementBuilder, audited: bool, headers: tuple[str, str]) -> list:
    now, before = b.current.values, b.cmp_values
    scale = b.scale

    def row(label: str, a: Decimal, c: Decimal) -> list[str]:
        return [label, amount(a, scale), amount(c, scale)]

    term_now = now["bs.cpltd"] + now["bs.long_term_debt"]
    term_before = before["bs.cpltd"] + before["bs.long_term_debt"]
    total_now = term_now + now["bs.revolver"] + now["bs.subordinated_debt"]
    total_before = term_before + before["bs.revolver"] + before["bs.subordinated_debt"]
    data = [["", headers[0], headers[1]]]
    if now["bs.revolver"] or before["bs.revolver"]:
        data.append(row(f"Revolving line of credit - {LENDER}", now["bs.revolver"], before["bs.revolver"]))
    if term_now or term_before:
        data.append(row(f"Term notes payable - {LENDER}", term_now, term_before))
    if now["bs.subordinated_debt"] or before["bs.subordinated_debt"]:
        data.append(row("Subordinated notes payable", now["bs.subordinated_debt"], before["bs.subordinated_debt"]))
    data.append(row("Total debt outstanding", total_now, total_before))
    data.append(row("Term debt principal due within twelve months", now["bs.cpltd"], before["bs.cpltd"]))
    last = len(data) - 2
    table = Table(data, colWidths=[3.95 * inch, 1.3 * inch, 1.3 * inch], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "Helvetica", 9.5),
                ("FONT", (1, 0), (-1, 0), "Helvetica-Bold", 8.5),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("LINEBELOW", (1, 0), (-1, 0), 0.6, RULE),
                ("FONT", (0, last), (-1, last), "Helvetica-Bold", 9.5),
                ("LINEABOVE", (1, last), (-1, last), 0.6, RULE),
                ("LEFTPADDING", (0, 1), (0, -1), 16),
                ("TOPPADDING", (0, 0), (-1, -1), 2.2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6),
            ]
        )
    )
    intro = (
        f"The Company's credit facilities with {LENDER} are governed by a credit agreement that contains "
        "financial covenants and is secured by substantially all assets of the Company. Balances "
        "outstanding were as follows."
    )
    return [para("Note 5 - Debt" if audited else "Debt schedule", HEADING), para(intro), table, Spacer(1, 12)]


def _auditor_report(spec: BorrowerSpec, end: date, prior_end: date) -> list:
    owners = "Members" if spec.legal_form == "llc" else "Board of Directors and Stockholders"
    return [
        para("Independent Auditor's Report", TITLE),
        Spacer(1, 6),
        para(f"To the {owners} of {spec.name}"),
        para("Opinion", HEADING),
        para(
            f"We have audited the financial statements of {spec.name} (the Company), which comprise the "
            f"balance sheets as of December 31, {end.year} and {prior_end.year}, and the related statements of "
            "income and cash flows for the years then ended, and the related notes to the financial statements."
        ),
        para(
            "In our opinion, the accompanying financial statements present fairly, in all material respects, "
            f"the financial position of the Company as of December 31, {end.year} and {prior_end.year}, and the "
            "results of its operations and its cash flows for the years then ended in accordance with "
            "accounting principles generally accepted in the United States of America."
        ),
        para("Basis for Opinion", HEADING),
        para(
            "We conducted our audits in accordance with auditing standards generally accepted in the United "
            "States of America. Our responsibilities under those standards are further described in the "
            "Auditor's Responsibilities section of our report. We are required to be independent of the "
            "Company and to meet our other ethical responsibilities in accordance with the relevant ethical "
            "requirements relating to our audits. We believe that the audit evidence we have obtained is "
            "sufficient and appropriate to provide a basis for our audit opinion."
        ),
        para("Responsibilities of Management for the Financial Statements", HEADING),
        para(
            "Management is responsible for the preparation and fair presentation of the financial statements "
            "in accordance with accounting principles generally accepted in the United States of America, and "
            "for the design, implementation and maintenance of internal control relevant to the preparation "
            "and fair presentation of financial statements that are free from material misstatement, whether "
            "due to fraud or error."
        ),
        para("Auditor's Responsibilities for the Audit of the Financial Statements", HEADING),
        para(
            "Our objectives are to obtain reasonable assurance about whether the financial statements as a "
            "whole are free from material misstatement, whether due to fraud or error, and to issue an "
            "auditor's report that includes our opinion. Reasonable assurance is a high level of assurance "
            "but is not absolute assurance and therefore is not a guarantee that an audit will always detect "
            "a material misstatement when it exists."
        ),
        Spacer(1, 14),
        para(spec.auditor),
        para(f"{spec.city}, {spec.state}"),
    ]


def _policy_notes(spec: BorrowerSpec, end: date) -> list:
    entity = "limited liability company" if spec.legal_form == "llc" else "corporation"
    tax = (
        "The Company is treated as a partnership for federal income tax purposes. Its taxable income is "
        "reported by its members, and the provision for income taxes reflects state and local taxes only."
        if spec.legal_form == "llc"
        else "The Company accounts for income taxes under the asset and liability method. The provision for "
        "income taxes reflects federal and state taxes currently payable."
    )
    return [
        para(spec.name, TITLE),
        para("Notes to Financial Statements", SUBTITLE),
        para(f"December 31, {end.year}", SUBTITLE),
        Spacer(1, 8),
        para("Note 1 - Nature of business", HEADING),
        para(
            f"{spec.name} (the Company) is a {STATE_NAMES[spec.state]} {entity} headquartered in {spec.city}, {spec.state}. "
            f"The Company operates in the {spec.industry} industry and serves customers primarily in the "
            "United States."
        ),
        para("Note 2 - Summary of significant accounting policies", HEADING),
        para(
            "Basis of presentation. The financial statements are prepared in accordance with accounting "
            "principles generally accepted in the United States of America. The preparation of financial "
            "statements requires management to make estimates and assumptions that affect reported amounts."
        ),
        para(
            "Revenue recognition. Revenue is recognized when control of the promised goods or services is "
            "transferred to the customer, in an amount that reflects the consideration the Company expects "
            "to receive. Net revenue is presented net of returns, allowances and discounts."
        ),
        para(
            "Accounts receivable. Accounts receivable are stated net of an allowance for expected credit "
            "losses, which management estimates from historical experience and current conditions."
        ),
        para(
            "Inventory. Inventory, where held, is stated at the lower of cost, determined on a first-in, "
            "first-out basis, and net realizable value."
        ),
        para(
            "Property and equipment. Property and equipment are stated at cost less accumulated depreciation. "
            "Depreciation is computed on the straight-line method over the estimated useful lives of the assets."
        ),
        para(
            "Goodwill and intangibles. Goodwill is not amortized and is tested for impairment annually. No "
            "impairment was recognized in the periods presented."
        ),
        para("Note 3 - Income taxes", HEADING),
        para(tax),
        para("Note 4 - Commitments and contingencies", HEADING),
        para(
            "The Company is party to various claims arising in the ordinary course of business. In the opinion "
            "of management, the resolution of these matters will not have a material adverse effect on the "
            "financial position or results of operations of the Company."
        ),
    ]
