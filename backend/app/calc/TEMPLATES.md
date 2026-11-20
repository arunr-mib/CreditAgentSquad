# Spreading templates and standard sections

Every line of `ci-1` (commercial and industrial) and `vc-1` (venture-backed) carries a `section`
from the generic names below, the conventional layout of a bank spread: income statement from
sales down to net profit, balance sheet by current and long-term position, and a cash flow in
operating, investing and financing sections. Section names are generic public accounting terms.
`TemplateLine.section` must be one of the names in this table (checked by
`backend/tests/calc/test_template_vc.py`). A computed line sits in the section it closes.

| Section | Statement | `ci-1` lines | `vc-1` lines |
|---|---|---|---|
| Sales | is | `is.revenue` | `is.subscription_revenue`, `is.services_revenue`, `is.total_revenue` |
| Cost of Sales | is | `is.cogs` | `is.cost_of_revenue` |
| Gross Profit | is | `is.gross_profit` | `is.vc_gross_profit` |
| Operating Expenses | is | `is.sga`, `is.depreciation_amortization`, `is.other_operating_expense`, `is.nonrecurring_expense` | `is.rnd`, `is.sales_marketing`, `is.gna`, `is.vc_depreciation_amortization` |
| Operating Profit | is | `is.operating_income` | `is.vc_operating_loss` |
| Interest | is | `is.interest_expense` | `is.vc_interest` |
| Other Income and Expense | is | `is.other_income_net` | `is.vc_other_income` |
| Profit Before Tax | is | `is.pretax_income` | - |
| Taxes | is | `is.income_tax_expense` | - |
| Net Profit | is | `is.net_income` | `is.vc_net_loss` |
| Current Assets | bs | `bs.cash`, `bs.accounts_receivable`, `bs.inventory`, `bs.other_current_assets`, `bs.total_current_assets` | `bs.cash_unrestricted`, `bs.cash_restricted`, `bs.vc_total_cash`, `bs.short_term_investments`, `bs.accounts_receivable`, `bs.other_current_assets` |
| Non-current Assets | bs | `bs.net_ppe`, `bs.intangibles`, `bs.other_noncurrent_assets` | `bs.capitalised_software`, `bs.vc_other_intangibles`, `bs.other_noncurrent_assets` |
| Balance Sheet Totals | bs | `bs.total_assets`, `bs.total_liabilities`, `bs.total_liabilities_and_equity` | `bs.vc_total_assets`, `bs.vc_total_liabilities`, `bs.vc_total_liabilities_and_equity` |
| Current Liabilities | bs | `bs.accounts_payable`, `bs.accrued_liabilities`, `bs.revolver`, `bs.cpltd`, `bs.other_current_liabilities`, `bs.total_current_liabilities` | `bs.accounts_payable`, `bs.accrued_liabilities`, `bs.deferred_revenue_current`, `bs.venture_debt_current` |
| Long-term Debt | bs | `bs.long_term_debt`, `bs.subordinated_debt` | `bs.venture_debt_noncurrent`, `bs.convertible_notes` |
| Other Non-current Liabilities | bs | `bs.other_noncurrent_liabilities` | `bs.deferred_revenue_noncurrent`, `bs.safes`, `bs.vc_other_liabilities` |
| Equity | bs | `bs.total_equity` | `bs.preferred_equity`, `bs.common_equity`, `bs.vc_total_equity` |
| Operating Activities | cf | `cf.net_income`, `cf.depreciation_amortization`, `cf.change_in_working_capital`, `cf.other_operating`, `cf.cfo` | `cf.vc_operating_cash_flow` |
| Investing Activities | cf | `cf.capex`, `cf.other_investing`, `cf.cfi` | `cf.vc_capex`, `cf.capitalised_software_spend` |
| Financing Activities | cf | `cf.revolver_net`, `cf.term_debt_proceeds`, `cf.term_debt_repayments`, `cf.distributions`, `cf.other_financing`, `cf.cff` | `cf.equity_raised`, `cf.debt_raised`, `cf.vc_other_financing` |
| Net Change in Cash | cf | `cf.net_change_in_cash` | `cf.vc_net_change_in_cash` |
| Supplemental | sup | `sup.cash_interest_paid`, `sup.cash_taxes_paid`, `sup.scheduled_principal`, `sup.financed_capex` | `sup.cash_interest_paid`, `sup.scheduled_principal` |
| Memo Items | is | - | `is.vc_stock_based_compensation` (optional memo) |
| SaaS Metrics | saas | - | `saas.mrr`, `saas.arr`, `saas.customers`, `saas.net_new_arr` (optional), `saas.net_revenue_retention` (optional) |

## Optional lines

A line marked `optional` in `calc/template.py` sits outside every total, so it changes no footing.
A statement need not print it: when it is not printed the line has no fact at all (unmeasured is
null, never zero), and it is not an error. It is never filed as a verified zero when the reader
lists it as absent. `vc-1` has three: `is.vc_stock_based_compensation` (a memo of the stock-based
compensation already inside the operating expense lines), `saas.net_new_arr` and
`saas.net_revenue_retention`.

## Periods: flows are year to date

Flow lines (income statement, cash flow, supplemental) are stored as fiscal year to date: a
nine-month column is nine months of flow. Point-in-time lines (balance sheet, SaaS metrics) are
stored at the period end. A trailing-three-month figure (`t3m`) is not stored; it is derived from
differences of year-to-date figures at the period end and three months earlier (and across the
fiscal year end when the window crosses it). A monthly pack must therefore state year-to-date
columns (month columns are not converted to year to date by the spreading step), otherwise `t3m`
measures (runway, net burn) cannot be computed and the test is "cannot be tested", never zero.
