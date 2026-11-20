"""Printed layout of the vc-1 statements: label, kind and order of every line. Own copy; never read from backend/app."""
from __future__ import annotations

# (kind, key or heading). kind: head | line | total | grand
INCOME = (
    ("head", "Revenue"), ("line", "is.subscription_revenue"), ("line", "is.services_revenue"), ("total", "is.total_revenue"),
    ("line", "is.cost_of_revenue"), ("total", "is.vc_gross_profit"),
    ("head", "Operating expenses"), ("line", "is.rnd"), ("line", "is.sales_marketing"), ("line", "is.gna"),
    ("line", "is.vc_depreciation_amortization"), ("total", "is.vc_operating_loss"),
    ("line", "is.vc_interest"), ("line", "is.vc_other_income"), ("grand", "is.vc_net_loss"),
)
BALANCE = (
    ("head", "Assets"), ("line", "bs.cash_unrestricted"), ("line", "bs.cash_restricted"), ("total", "bs.vc_total_cash"),
    ("line", "bs.short_term_investments"), ("line", "bs.accounts_receivable"), ("line", "bs.other_current_assets"),
    ("line", "bs.capitalised_software"), ("line", "bs.vc_other_intangibles"), ("line", "bs.other_noncurrent_assets"),
    ("grand", "bs.vc_total_assets"),
    ("head", "Liabilities"), ("line", "bs.accounts_payable"), ("line", "bs.accrued_liabilities"),
    ("line", "bs.deferred_revenue_current"), ("line", "bs.deferred_revenue_noncurrent"),
    ("line", "bs.venture_debt_current"), ("line", "bs.venture_debt_noncurrent"), ("line", "bs.convertible_notes"),
    ("line", "bs.safes"), ("line", "bs.vc_other_liabilities"), ("total", "bs.vc_total_liabilities"),
    ("head", "Stockholders' equity"), ("line", "bs.preferred_equity"), ("line", "bs.common_equity"),
    ("total", "bs.vc_total_equity"), ("grand", "bs.vc_total_liabilities_and_equity"),
)
CASHFLOW = (
    ("head", "Operating activities"), ("line", "cf.vc_operating_cash_flow"),
    ("head", "Investing activities"), ("line", "cf.vc_capex"), ("line", "cf.capitalised_software_spend"),
    ("head", "Financing activities"), ("line", "cf.equity_raised"), ("line", "cf.debt_raised"),
    ("line", "cf.vc_other_financing"), ("grand", "cf.vc_net_change_in_cash"),
)
LABELS = {
    "is.subscription_revenue": "Subscription revenue", "is.services_revenue": "Services revenue",
    "is.total_revenue": "Total revenue", "is.cost_of_revenue": "Cost of revenue", "is.vc_gross_profit": "Gross profit",
    "is.rnd": "Research and development", "is.sales_marketing": "Sales and marketing",
    "is.gna": "General and administrative", "is.vc_depreciation_amortization": "Depreciation and amortization",
    "is.vc_operating_loss": "Operating income (loss)", "is.vc_interest": "Interest expense",
    "is.vc_other_income": "Other income (expense), net", "is.vc_net_loss": "Net income (loss)",
    "bs.cash_unrestricted": "Cash in operating accounts", "bs.cash_restricted": "Cash pledged or restricted",
    "bs.vc_total_cash": "Total cash", "bs.short_term_investments": "Short-term investments",
    "bs.accounts_receivable": "Accounts receivable, net", "bs.other_current_assets": "Other current assets",
    "bs.capitalised_software": "Capitalised software, net", "bs.vc_other_intangibles": "Other intangibles, net",
    "bs.other_noncurrent_assets": "Other assets", "bs.vc_total_assets": "Total assets",
    "bs.accounts_payable": "Accounts payable", "bs.accrued_liabilities": "Accrued liabilities",
    "bs.deferred_revenue_current": "Deferred revenue, current", "bs.deferred_revenue_noncurrent": "Deferred revenue, non-current",
    "bs.venture_debt_current": "Venture debt, current portion", "bs.venture_debt_noncurrent": "Venture debt, net of current portion",
    "bs.convertible_notes": "Convertible notes", "bs.safes": "SAFEs", "bs.vc_other_liabilities": "Other liabilities",
    "bs.vc_total_liabilities": "Total liabilities", "bs.preferred_equity": "Preferred stock",
    "bs.common_equity": "Common stock and accumulated deficit", "bs.vc_total_equity": "Total stockholders' equity",
    "bs.vc_total_liabilities_and_equity": "Total liabilities and stockholders' equity",
    "cf.vc_operating_cash_flow": "Net cash used in operating activities", "cf.vc_capex": "Purchases of property and equipment",
    "cf.capitalised_software_spend": "Capitalised software development", "cf.equity_raised": "Proceeds from issuance of preferred stock",
    "cf.debt_raised": "Proceeds from venture debt", "cf.vc_other_financing": "Other financing",
    "cf.vc_net_change_in_cash": "Net change in cash",
}
OUTFLOWS = frozenset({"cf.vc_capex", "cf.capitalised_software_spend"})  # stored positive, printed in brackets
