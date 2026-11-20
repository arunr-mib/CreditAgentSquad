"""Spreading templates `ci-1` and `vc-1` as data, its subtotals and its checks (spec section 4).

Values are whole US dollars, unscaled. Stored value = presentation_sign x printed value;
expenses and outflows are stored positive. Stated totals arrive as `stated.<key>`.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass, field
from decimal import Decimal

from . import errors as E
from .decimal_utils import CALC_CONTEXT, ZERO, is_decimal
from .errors import CalcError

TEMPLATE_ID = "ci-1"
STATED_PREFIX = "stated."
STATEMENTS = ("is", "bs", "cf", "sup", "saas")
POINT_IN_TIME = ("bs", "saas")
ALLOWED_SCALES = (1, 1000)


@dataclass(frozen=True)
class TemplateLine:
    key: str
    label: str
    statement: str  # is | bs | cf | sup | saas | bb
    computed: bool = False
    presentation_sign: int = 1
    flow: bool = True  # True: fiscal year to date flow; False: point in time
    formula: tuple[tuple[int, str], ...] = ()  # (sign, component key) for computed lines
    section: str = ""  # conventional spread section, one of those in TEMPLATES.md


def _line(key: str, label: str, section: str, *, sign: int = 1) -> TemplateLine:
    statement = key.split(".", 1)[0]
    return TemplateLine(key, label, statement, presentation_sign=sign,
                        flow=statement not in POINT_IN_TIME, section=section)


def _total(key: str, label: str, section: str, *terms: str) -> TemplateLine:
    statement = key.split(".", 1)[0]
    formula = tuple((-1, t[1:]) if t.startswith("-") else (1, t.lstrip("+")) for t in terms)
    return TemplateLine(key, label, statement, computed=True, flow=statement not in POINT_IN_TIME,
                        formula=formula, section=section)


# Shared by ci-1 and vc-1: the same object in both templates (a registry test enforces identity).
_SUP_CASH_INTEREST_PAID = _line("sup.cash_interest_paid", "Cash paid for interest", "Supplemental")
_SUP_CASH_TAXES_PAID = _line("sup.cash_taxes_paid", "Cash paid for income taxes", "Supplemental")
_SUP_SCHEDULED_PRINCIPAL = _line("sup.scheduled_principal", "Scheduled principal payments on term debt", "Supplemental")

CI_LINES: tuple[TemplateLine, ...] = (
    # Income statement (flow, fiscal year to date)
    _line("is.revenue", "Net revenue", "Sales"),
    _line("is.cogs", "Cost of goods sold", "Cost of Sales"),
    _total("is.gross_profit", "Gross profit", "Gross Profit", "is.revenue", "-is.cogs"),
    _line("is.sga", "Selling, general and administrative", "Operating Expenses"),
    _line("is.depreciation_amortization", "Depreciation and amortization", "Operating Expenses"),
    _line("is.other_operating_expense", "Other operating expense", "Operating Expenses"),
    _line("is.nonrecurring_expense", "Restructuring and other non-recurring charges", "Operating Expenses"),
    _total(
        "is.operating_income", "Operating income", "Operating Profit",
        "is.gross_profit", "-is.sga", "-is.depreciation_amortization",
        "-is.other_operating_expense", "-is.nonrecurring_expense",
    ),
    _line("is.interest_expense", "Interest expense", "Interest"),
    _line("is.other_income_net", "Other income (expense), net", "Other Income and Expense"),
    _total(
        "is.pretax_income", "Income before taxes", "Profit Before Tax",
        "is.operating_income", "-is.interest_expense", "is.other_income_net",
    ),
    _line("is.income_tax_expense", "Income tax expense", "Taxes"),
    _total("is.net_income", "Net income", "Net Profit", "is.pretax_income", "-is.income_tax_expense"),
    # Balance sheet (point in time)
    _line("bs.cash", "Cash and equivalents", "Current Assets"),
    _line("bs.accounts_receivable", "Accounts receivable, net", "Current Assets"),
    _line("bs.inventory", "Inventory", "Current Assets"),
    _line("bs.other_current_assets", "Other current assets", "Current Assets"),
    _total(
        "bs.total_current_assets", "Total current assets", "Current Assets",
        "bs.cash", "bs.accounts_receivable", "bs.inventory", "bs.other_current_assets",
    ),
    _line("bs.net_ppe", "Property and equipment, net", "Non-current Assets"),
    _line("bs.intangibles", "Goodwill and intangibles", "Non-current Assets"),
    _line("bs.other_noncurrent_assets", "Other assets", "Non-current Assets"),
    _total(
        "bs.total_assets", "Total assets", "Balance Sheet Totals",
        "bs.total_current_assets", "bs.net_ppe", "bs.intangibles", "bs.other_noncurrent_assets",
    ),
    _line("bs.accounts_payable", "Accounts payable", "Current Liabilities"),
    _line("bs.accrued_liabilities", "Accrued liabilities", "Current Liabilities"),
    _line("bs.revolver", "Line of credit", "Current Liabilities"),
    _line("bs.cpltd", "Current portion of long-term debt", "Current Liabilities"),
    _line("bs.other_current_liabilities", "Other current liabilities", "Current Liabilities"),
    _total(
        "bs.total_current_liabilities", "Total current liabilities", "Current Liabilities",
        "bs.accounts_payable", "bs.accrued_liabilities", "bs.revolver", "bs.cpltd",
        "bs.other_current_liabilities",
    ),
    _line("bs.long_term_debt", "Long-term debt, net of current portion", "Long-term Debt"),
    _line("bs.subordinated_debt", "Subordinated debt", "Long-term Debt"),
    _line("bs.other_noncurrent_liabilities", "Other liabilities", "Other Non-current Liabilities"),
    _total(
        "bs.total_liabilities", "Total liabilities", "Balance Sheet Totals",
        "bs.total_current_liabilities", "bs.long_term_debt", "bs.subordinated_debt",
        "bs.other_noncurrent_liabilities",
    ),
    _line("bs.total_equity", "Total equity", "Equity"),
    _total(
        "bs.total_liabilities_and_equity", "Total liabilities and equity", "Balance Sheet Totals",
        "bs.total_liabilities", "bs.total_equity",
    ),
    # Cash flow (flow, fiscal year to date, indirect)
    _line("cf.net_income", "Net income", "Operating Activities"),
    _line("cf.depreciation_amortization", "Depreciation and amortization", "Operating Activities"),
    _line("cf.change_in_working_capital", "Changes in working capital", "Operating Activities"),
    _line("cf.other_operating", "Other operating items", "Operating Activities"),
    _total(
        "cf.cfo", "Net cash from operating activities", "Operating Activities",
        "cf.net_income", "cf.depreciation_amortization", "cf.change_in_working_capital",
        "cf.other_operating",
    ),
    _line("cf.capex", "Purchases of property and equipment", "Investing Activities", sign=-1),
    _line("cf.other_investing", "Other investing", "Investing Activities"),
    _total("cf.cfi", "Net cash from investing", "Investing Activities", "-cf.capex", "cf.other_investing"),
    _line("cf.revolver_net", "Net borrowings on line of credit", "Financing Activities"),
    _line("cf.term_debt_proceeds", "Proceeds from long-term debt", "Financing Activities"),
    _line("cf.term_debt_repayments", "Repayments of long-term debt", "Financing Activities", sign=-1),
    _line("cf.distributions", "Distributions to owners", "Financing Activities", sign=-1),
    _line("cf.other_financing", "Other financing", "Financing Activities"),
    _total(
        "cf.cff", "Net cash from financing", "Financing Activities",
        "cf.revolver_net", "cf.term_debt_proceeds", "-cf.term_debt_repayments",
        "-cf.distributions", "cf.other_financing",
    ),
    _total("cf.net_change_in_cash", "Net change in cash", "Net Change in Cash", "cf.cfo", "cf.cfi", "cf.cff"),
    # Supplemental (from the notes page)
    _SUP_CASH_INTEREST_PAID,
    _SUP_CASH_TAXES_PAID,
    _SUP_SCHEDULED_PRINCIPAL,
    _line("sup.financed_capex", "Capital expenditures financed with purchase-money debt", "Supplemental"),
)

VC_LINES: tuple[TemplateLine, ...] = (
    # Income statement (flow, fiscal year to date; monthly reporters file every month)
    _line("is.subscription_revenue", "Subscription revenue", "Sales"),
    _line("is.services_revenue", "Services revenue", "Sales"),
    _total("is.total_revenue", "Total revenue", "Sales", "is.subscription_revenue", "is.services_revenue"),
    _line("is.cost_of_revenue", "Cost of revenue", "Cost of Sales"),
    _total("is.vc_gross_profit", "Gross profit", "Gross Profit", "is.total_revenue", "-is.cost_of_revenue"),
    _line("is.rnd", "Research and development", "Operating Expenses"),
    _line("is.sales_marketing", "Sales and marketing", "Operating Expenses"),
    _line("is.gna", "General and administrative", "Operating Expenses"),
    _line("is.vc_depreciation_amortization", "Depreciation and amortization", "Operating Expenses"),
    _total("is.vc_operating_loss", "Operating income (loss)", "Operating Profit",
           "is.vc_gross_profit", "-is.rnd", "-is.sales_marketing", "-is.gna", "-is.vc_depreciation_amortization"),
    _line("is.vc_interest", "Interest expense", "Interest"),
    _line("is.vc_other_income", "Other income (expense), net", "Other Income and Expense"),
    _total("is.vc_net_loss", "Net income (loss)", "Net Profit",
           "is.vc_operating_loss", "-is.vc_interest", "is.vc_other_income"),
    # Balance sheet (point in time)
    _line("bs.cash_unrestricted", "Cash in operating accounts", "Current Assets"),
    _line("bs.cash_restricted", "Cash pledged or restricted", "Current Assets"),
    _total("bs.vc_total_cash", "Total cash", "Current Assets", "bs.cash_unrestricted", "bs.cash_restricted"),
    _line("bs.short_term_investments", "Short-term investments", "Current Assets"),
    _line("bs.accounts_receivable", "Accounts receivable, net", "Current Assets"),
    _line("bs.other_current_assets", "Other current assets", "Current Assets"),
    _line("bs.capitalised_software", "Capitalised software, net", "Non-current Assets"),
    _line("bs.vc_other_intangibles", "Other intangibles, net", "Non-current Assets"),
    _line("bs.other_noncurrent_assets", "Other assets", "Non-current Assets"),
    _total("bs.vc_total_assets", "Total assets", "Balance Sheet Totals",
           "bs.vc_total_cash", "bs.short_term_investments", "bs.accounts_receivable",
           "bs.other_current_assets", "bs.capitalised_software", "bs.vc_other_intangibles",
           "bs.other_noncurrent_assets"),
    _line("bs.accounts_payable", "Accounts payable", "Current Liabilities"),
    _line("bs.accrued_liabilities", "Accrued liabilities", "Current Liabilities"),
    _line("bs.deferred_revenue_current", "Deferred revenue, current", "Current Liabilities"),
    _line("bs.deferred_revenue_noncurrent", "Deferred revenue, non-current", "Other Non-current Liabilities"),
    _line("bs.venture_debt_current", "Venture debt, current portion", "Current Liabilities"),
    _line("bs.venture_debt_noncurrent", "Venture debt, net of current portion", "Long-term Debt"),
    _line("bs.convertible_notes", "Convertible notes", "Long-term Debt"),
    _line("bs.safes", "SAFEs", "Other Non-current Liabilities"),
    _line("bs.vc_other_liabilities", "Other liabilities", "Other Non-current Liabilities"),
    _total("bs.vc_total_liabilities", "Total liabilities", "Balance Sheet Totals",
           "bs.accounts_payable", "bs.accrued_liabilities", "bs.deferred_revenue_current",
           "bs.deferred_revenue_noncurrent", "bs.venture_debt_current", "bs.venture_debt_noncurrent",
           "bs.convertible_notes", "bs.safes", "bs.vc_other_liabilities"),
    _line("bs.preferred_equity", "Preferred stock", "Equity"),
    _line("bs.common_equity", "Common stock and accumulated deficit", "Equity"),
    _total("bs.vc_total_equity", "Total stockholders' equity", "Equity", "bs.preferred_equity", "bs.common_equity"),
    _total("bs.vc_total_liabilities_and_equity", "Total liabilities and stockholders' equity",
           "Balance Sheet Totals", "bs.vc_total_liabilities", "bs.vc_total_equity"),
    # Cash flow (flow)
    _line("cf.vc_operating_cash_flow", "Net cash used in operating activities", "Operating Activities"),
    _line("cf.vc_capex", "Purchases of property and equipment", "Investing Activities", sign=-1),
    _line("cf.capitalised_software_spend", "Capitalised software development", "Investing Activities", sign=-1),
    _line("cf.equity_raised", "Proceeds from issuance of preferred stock", "Financing Activities"),
    _line("cf.debt_raised", "Proceeds from venture debt", "Financing Activities"),
    _line("cf.vc_other_financing", "Other financing", "Financing Activities"),
    _total("cf.vc_net_change_in_cash", "Net change in cash", "Net Change in Cash",
           "cf.vc_operating_cash_flow", "-cf.vc_capex", "-cf.capitalised_software_spend",
           "cf.equity_raised", "cf.debt_raised", "cf.vc_other_financing"),
    # SaaS metrics (point in time, from the MRR/ARR report)
    _SUP_CASH_INTEREST_PAID,
    _SUP_SCHEDULED_PRINCIPAL,
    _line("saas.mrr", "Monthly recurring revenue", "SaaS Metrics"),
    _line("saas.arr", "Annual recurring revenue", "SaaS Metrics"),
    _line("saas.customers", "Customers", "SaaS Metrics"),
)

LINES = CI_LINES  # alias kept so existing imports of the ci-1 tuple keep working

TEMPLATES: dict[str, tuple[TemplateLine, ...]] = {"ci-1": CI_LINES, "vc-1": VC_LINES}
_LINES_BY_TEMPLATE: dict[str, dict[str, TemplateLine]] = {
    tid: {line.key: line for line in lines} for tid, lines in TEMPLATES.items()
}


def template_lines(template_id: str) -> tuple[TemplateLine, ...]:
    if template_id not in TEMPLATES:
        raise ValueError(f"unknown template {template_id!r}")
    return TEMPLATES[template_id]


def in_template(key: str, template_id: str) -> bool:
    return key in _LINES_BY_TEMPLATE.get(template_id, {})


# `LINE_BY_KEY` stays the ci-1 index (existing callers rely on it); `ALL_LINE_BY_KEY` spans every
# template and is what `line_info`, `known_labels` and `stored_value` search.
LINE_BY_KEY: dict[str, TemplateLine] = _LINES_BY_TEMPLATE["ci-1"]
ALL_LINE_BY_KEY: dict[str, TemplateLine] = {}
for _lines in TEMPLATES.values():
    for _l in _lines:
        if _l.key in ALL_LINE_BY_KEY and ALL_LINE_BY_KEY[_l.key] != _l:
            raise RuntimeError(f"line {_l.key} differs between templates")
        ALL_LINE_BY_KEY[_l.key] = _l

# Other names a line is commonly printed under. A row whose label is neither the template's own
# nor listed here is put to a person once (see app/guardrails/labels.py); add to this list only
# names that can mean nothing else.
SYNONYMS: dict[str, tuple[str, ...]] = {
    "is.revenue": ("Net sales", "Revenue", "Revenues", "Sales", "Total revenue", "Net revenues"),
    "is.cogs": ("Cost of sales", "Cost of services", "Cost of revenue", "Cost of goods sold and services"),
    "is.sga": ("Selling, general and administrative expenses", "General and administrative",
               "Selling, general & administrative"),
    "is.depreciation_amortization": ("Depreciation", "Depreciation and amortization expense"),
    "is.interest_expense": ("Interest expense, net",),
    "is.pretax_income": ("Income before income taxes", "Income before tax", "Pretax income"),
    "is.income_tax_expense": ("Provision for income taxes", "Income taxes", "Income tax provision"),
    "is.net_income": ("Net income (loss)", "Net earnings"),
    "is.operating_income": ("Income from operations", "Operating income (loss)", "Operating profit"),
    "bs.cash": ("Cash and cash equivalents", "Cash"),
    "bs.accounts_receivable": ("Accounts receivable", "Trade receivables", "Trade accounts receivable, net"),
    "bs.inventory": ("Inventories", "Inventory, net", "Inventories, net"),
    "bs.net_ppe": ("Property, plant and equipment, net", "Property and equipment", "Net property and equipment"),
    "bs.intangibles": ("Goodwill and intangible assets", "Goodwill and other intangibles", "Intangible assets, net"),
    "bs.other_noncurrent_assets": ("Other noncurrent assets", "Other long-term assets"),
    "bs.accounts_payable": ("Trade accounts payable", "Trade payables"),
    "bs.accrued_liabilities": ("Accrued expenses", "Accrued expenses and other liabilities"),
    "bs.revolver": ("Revolving line of credit", "Revolving credit facility", "Line of credit borrowings"),
    "bs.cpltd": ("Current maturities of long-term debt", "Current portion of term debt"),
    "bs.long_term_debt": ("Long-term debt", "Long-term debt, less current portion",
                          "Long-term debt, less current maturities", "Term debt, net of current portion"),
    "bs.subordinated_debt": ("Subordinated notes", "Subordinated notes payable"),
    "bs.other_noncurrent_liabilities": ("Other noncurrent liabilities", "Other long-term liabilities"),
    "bs.total_equity": ("Total stockholders' equity", "Total shareholders' equity", "Total members' equity",
                        "Total partners' capital", "Total owners' equity"),
    "bs.total_liabilities_and_equity": (
        "Total liabilities and stockholders' equity", "Total liabilities and shareholders' equity",
        "Total liabilities and members' equity", "Total liabilities and partners' capital"),
    "cf.net_income": ("Net income (loss)", "Net earnings"),
    "cf.distributions": ("Distributions to members", "Distributions to shareholders", "Dividends paid",
                         "Distributions paid", "Dividends and distributions"),
    "cf.capex": ("Capital expenditures", "Purchases of property and equipment",
                 "Purchases of property, plant and equipment"),
    # vc-1. "Contract liabilities" is deliberately not mapped to deferred revenue: that stays a
    # question to a person.
    "is.rnd": ("Research and development expense", "R&D"),
    "is.gna": ("General and administrative expense",),
    "cf.capitalised_software_spend": ("Capitalized software development costs",),
}


# Lines that are never negative once stored (an expense or an outflow is stored as a positive
# amount). A negative value here means the figure was printed in brackets where none are
# expected, or the sign convention was misread: a person decides, code does not guess.
NEVER_NEGATIVE = frozenset({
    "is.revenue", "is.cogs", "is.sga", "is.depreciation_amortization", "is.interest_expense",
    "bs.cash", "bs.accounts_receivable", "bs.inventory", "bs.net_ppe", "bs.intangibles",
    "bs.accounts_payable", "bs.accrued_liabilities", "bs.revolver", "bs.cpltd", "bs.long_term_debt",
    "bs.subordinated_debt", "cf.depreciation_amortization", "cf.capex", "cf.term_debt_proceeds",
    "cf.term_debt_repayments", "cf.distributions", "sup.cash_interest_paid", "sup.cash_taxes_paid",
    "sup.scheduled_principal", "sup.financed_capex",
    # vc-1
    "is.subscription_revenue", "is.services_revenue", "is.cost_of_revenue", "is.rnd",
    "is.sales_marketing", "is.gna", "bs.cash_unrestricted", "bs.cash_restricted",
    "bs.capitalised_software", "bs.deferred_revenue_current", "bs.deferred_revenue_noncurrent",
    "cf.vc_capex", "cf.capitalised_software_spend", "saas.mrr", "saas.arr", "saas.customers",
})


def known_labels(key: str) -> tuple[str, ...]:
    """Every name a line is known by: the template's label first, then its synonyms."""
    return (ALL_LINE_BY_KEY[key].label, *SYNONYMS.get(key, ()))



# Facts the expression engine may read that are not template lines. Availability is produced
# by `borrowing_base` and stored by the caller as a calculated, point-in-time fact.
EXTRA_LINES: dict[str, TemplateLine] = {
    "bb.availability": TemplateLine("bb.availability", "Availability", "bb", flow=False),
}


def line_info(key: str) -> TemplateLine | None:
    """The line for a key the engine can read, or None if the key is unknown."""
    return ALL_LINE_BY_KEY.get(key) or EXTRA_LINES.get(key)


def stored_value(key: str, printed: Decimal) -> Decimal:
    """Stored value = presentation_sign x printed value (parentheses already parsed as negative)."""
    return ALL_LINE_BY_KEY[key].presentation_sign * printed


def _dependents(key: str, template_id: str = TEMPLATE_ID) -> set[str]:
    """Computed lines of a template that depend, directly or through other totals, on `key`."""
    found: set[str] = set()
    frontier = {key}
    while frontier:
        nxt = {line.key for line in template_lines(template_id) if line.computed and any(k in frontier for _, k in line.formula)}
        frontier = nxt - found
        found |= nxt
    return found


@dataclass
class StatementResult:
    values: dict[str, Decimal] = field(default_factory=dict)  # inputs, absent zeros and computed
    computed: dict[str, Decimal] = field(default_factory=dict)  # computed lines only
    errors: list[CalcError] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass(frozen=True)
class CheckResult:
    check: str  # footing | balance | tie | cash_roll | restatement
    key: str
    status: str  # pass | fail | not_checked
    actual: Decimal | None = None
    expected: Decimal | None = None
    difference: Decimal | None = None  # actual - expected
    tolerance: Decimal | None = None


@dataclass
class CheckReport:
    values: dict[str, Decimal] = field(default_factory=dict)
    computed: dict[str, Decimal] = field(default_factory=dict)
    checks: list[CheckResult] = field(default_factory=list)
    errors: list[CalcError] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _selected(statements: Iterable[str] | None) -> tuple[str, ...]:
    if statements is None:
        return STATEMENTS
    chosen = tuple(statements)
    for name in chosen:
        if name not in STATEMENTS:
            raise ValueError(f"unknown statement {name!r}")
    return chosen


def compute_statement(
    inputs: Mapping[str, Decimal],
    *,
    absent: Collection[str] = (),
    statements: Iterable[str] | None = None,
    template_id: str = TEMPLATE_ID,
) -> StatementResult:
    """Compute every computed line of the chosen statements from input lines.

    `absent` lines count as zero here; whether they are *allowed* to is decided by
    `check_statement`. `stated.*` keys are ignored. A missing input is an error naming the
    line, and the totals that depend on it are left out rather than computed from zero.
    """
    lines = template_lines(template_id)
    by_key = _LINES_BY_TEMPLATE[template_id]
    chosen = _selected(statements)
    result = StatementResult()
    absent_set = set(absent)

    for key in sorted(absent_set):
        line = by_key.get(key)
        if line is None:
            result.errors.append(CalcError(E.UNKNOWN_KEY, f"absent line {key} is not in template {template_id}", key=key))
        elif line.computed:
            result.errors.append(CalcError(E.INVALID_VALUE, f"computed line {key} cannot be marked absent", key=key))
        elif key in inputs:
            result.errors.append(CalcError(E.INVALID_VALUE, f"line {key} is both supplied and marked absent", key=key))

    bad: set[str] = set()
    for key, value in inputs.items():
        if isinstance(key, str) and key.startswith(STATED_PREFIX):
            stated_key = key[len(STATED_PREFIX):]
            if stated_key not in by_key or not by_key[stated_key].computed:
                result.errors.append(CalcError(E.UNKNOWN_KEY, f"{key} is not a stated total of template {template_id}", key=key))
            elif not is_decimal(value):
                result.errors.append(_bad_value(key, value))
            continue
        line = by_key.get(key)
        if line is None:
            result.errors.append(CalcError(E.UNKNOWN_KEY, f"line {key} is not in template {template_id}", key=key))
        elif line.computed:
            result.errors.append(
                CalcError(E.COMPUTED_LINE_SUPPLIED, f"{key} is computed; supply the printed total as stated.{key}", key=key)
            )
        elif not is_decimal(value):
            result.errors.append(_bad_value(key, value))
            bad.add(key)

    for line in lines:
        if line.statement not in chosen:
            continue
        if not line.computed:
            if line.key in bad:
                continue
            if line.key in inputs and line.key not in absent_set:
                result.values[line.key] = inputs[line.key]
            elif line.key in absent_set and line.key not in inputs:
                result.values[line.key] = ZERO
            elif line.key not in inputs:
                result.errors.append(CalcError(E.MISSING_INPUT, f"missing input {line.key}", key=line.key))
            continue
        if all(component in result.values for _, component in line.formula):
            total = ZERO
            for sign, component in line.formula:
                total = CALC_CONTEXT.add(total, sign * result.values[component])
            result.values[line.key] = total
            result.computed[line.key] = total
    return result


def _bad_value(key: str, value: object) -> CalcError:
    if isinstance(value, float):
        return CalcError(E.FLOAT_NOT_ALLOWED, f"{key} is a float; values must be Decimal", key=key)
    return CalcError(E.INVALID_VALUE, f"{key} must be a finite Decimal, got {type(value).__name__}", key=key)


def _compare(check: str, key: str, actual: Decimal, expected: Decimal, tolerance: Decimal) -> CheckResult:
    difference = actual - expected
    status = "pass" if abs(difference) <= tolerance else "fail"
    return CheckResult(check, key, status, actual, expected, difference, tolerance)


def _check_scale(scale: int) -> None:
    if isinstance(scale, bool) or not isinstance(scale, int):
        raise TypeError("scale must be an int")
    if scale not in ALLOWED_SCALES:
        raise ValueError(f"scale must be one of {ALLOWED_SCALES}")


_FAIL_CODES = {
    "footing": E.DOES_NOT_FOOT,
    "balance": E.DOES_NOT_BALANCE,
    "tie": E.DOES_NOT_TIE,
    "cash_roll": E.CASH_ROLL_MISMATCH,
}

# Per-template identities. vc-1 has no cash-flow ties yet.
_TIES: dict[str, tuple[tuple[str, str], ...]] = {
    "ci-1": (("cf.net_income", "is.net_income"), ("cf.depreciation_amortization", "is.depreciation_amortization")),
    "vc-1": (),
}
_BALANCE: dict[str, tuple[str, str]] = {
    "ci-1": ("bs.total_assets", "bs.total_liabilities_and_equity"),
    "vc-1": ("bs.vc_total_assets", "bs.vc_total_liabilities_and_equity"),
}
_CASH_ROLL: dict[str, tuple[str, str]] = {  # (net change in cash, balance-sheet cash)
    "ci-1": ("cf.net_change_in_cash", "bs.cash"),
    "vc-1": ("cf.vc_net_change_in_cash", "bs.vc_total_cash"),
}


def cash_roll_keys(template_id: str) -> tuple[str, str]:
    """(net change in cash, balance-sheet cash) for the template: the cash roll's two lines."""
    return _CASH_ROLL[template_id]


def balance_keys(template_id: str) -> tuple[str, str]:
    """(total assets, total liabilities and equity) for the template."""
    return _BALANCE[template_id]


def check_statement(
    inputs: Mapping[str, Decimal],
    *,
    scale: int,
    prior_fye_cash: Decimal | None,
    absent: Collection[str] = (),
    statements: Iterable[str] | None = None,
    template_id: str = TEMPLATE_ID,
) -> CheckReport:
    """Compute the statement and run the section 4 checks.

    Tolerance is 1 dollar x number of components x scale. For footing the components are
    the terms of the total's formula; for the other identities they are the terms on the
    right-hand side (one for balance and the ties, two for the cash roll).

    A failed check is an error. An `absent` line stands only if a stated total that depends
    on it was checked and every footing check in its statement passed.
    """
    _check_scale(scale)
    if prior_fye_cash is not None and not is_decimal(prior_fye_cash):
        raise TypeError("prior_fye_cash must be a Decimal or None")
    lines = template_lines(template_id)
    by_key = _LINES_BY_TEMPLATE[template_id]
    chosen = _selected(statements)
    computed = compute_statement(inputs, absent=absent, statements=chosen, template_id=template_id)
    report = CheckReport(values=computed.values, computed=computed.computed, errors=list(computed.errors))
    values = report.values
    unit = Decimal(scale)

    for line in lines:
        if not line.computed or line.statement not in chosen:
            continue
        stated = inputs.get(STATED_PREFIX + line.key)
        if line.key not in values or not is_decimal(stated):
            report.checks.append(CheckResult("footing", line.key, "not_checked"))
            continue
        report.checks.append(_compare("footing", line.key, values[line.key], stated, unit * len(line.formula)))

    assets_key, l_and_e_key = _BALANCE[template_id]
    if assets_key in values and l_and_e_key in values:
        report.checks.append(_compare("balance", assets_key, values[assets_key], values[l_and_e_key], unit))
    elif "bs" in chosen:
        report.checks.append(CheckResult("balance", assets_key, "not_checked"))

    for cf_key, is_key in _TIES[template_id]:
        if cf_key in values and is_key in values:
            report.checks.append(_compare("tie", cf_key, values[cf_key], values[is_key], unit))
        elif "cf" in chosen:
            report.checks.append(CheckResult("tie", cf_key, "not_checked"))

    if "cf" in chosen:
        change_key, cash_key = _CASH_ROLL[template_id]
        if change_key in values and cash_key in values and prior_fye_cash is not None:
            report.checks.append(
                _compare("cash_roll", change_key, values[change_key], values[cash_key] - prior_fye_cash, unit * 2)
            )
        else:
            report.checks.append(CheckResult("cash_roll", change_key, "not_checked"))

    for check in report.checks:
        if check.status == "fail":
            report.errors.append(
                CalcError(
                    _FAIL_CODES[check.check],
                    f"{check.check} check failed for {check.key}: {check.actual} against {check.expected}",
                    key=check.key,
                    detail={"actual": check.actual, "expected": check.expected,
                            "difference": check.difference, "tolerance": check.tolerance},
                )
            )

    footing = {c.key: c for c in report.checks if c.check == "footing"}
    for key in sorted(set(absent)):
        line = by_key.get(key)
        if line is None or line.computed or key in inputs:
            continue  # already reported by compute_statement
        section = [c for k, c in footing.items() if by_key[k].statement == line.statement]
        covered = any(footing[k].status == "pass" for k in _dependents(key, template_id) if k in footing)
        if any(c.status == "fail" for c in section):
            reason = f"the {line.statement} section does not foot, so {key} cannot be recorded as absent"
        elif not covered:
            reason = f"no stated total covering {key} was checked, so it cannot be recorded as absent"
        else:
            continue
        report.errors.append(CalcError(E.ABSENT_NOT_VERIFIED, reason, key=key))
    return report


def check_comparative(
    comparative: Mapping[str, Decimal],
    confirmed: Mapping[str, Decimal],
    *,
    scale: int,
) -> list[CheckResult]:
    """Compare a prior-period comparative column with the previously confirmed spread.

    Returns one `restatement` check per comparative line: `fail` means restated (raise a
    restatement exception), `not_checked` means nothing confirmed exists for that line.
    Tolerance is 1 dollar x scale.
    """
    _check_scale(scale)
    checks: list[CheckResult] = []
    for key, value in comparative.items():
        if not is_decimal(value):
            raise TypeError(f"comparative value for {key} must be a Decimal")
        prior = confirmed.get(key)
        if prior is None:
            checks.append(CheckResult("restatement", key, "not_checked", actual=value))
            continue
        if not is_decimal(prior):
            raise TypeError(f"confirmed value for {key} must be a Decimal")
        checks.append(_compare("restatement", key, value, prior, Decimal(scale)))
    return checks
