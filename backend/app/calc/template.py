"""Spreading template `ci-1` as data, its subtotals and its checks (spec section 4).

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
STATEMENTS = ("is", "bs", "cf", "sup")
ALLOWED_SCALES = (1, 1000)


@dataclass(frozen=True)
class TemplateLine:
    key: str
    label: str
    statement: str  # is | bs | cf | sup | bb
    computed: bool = False
    presentation_sign: int = 1
    flow: bool = True  # True: fiscal year to date flow; False: point in time
    formula: tuple[tuple[int, str], ...] = ()  # (sign, component key) for computed lines


def _line(key: str, label: str, *, sign: int = 1) -> TemplateLine:
    statement = key.split(".", 1)[0]
    return TemplateLine(key, label, statement, presentation_sign=sign, flow=statement != "bs")


def _total(key: str, label: str, *terms: str) -> TemplateLine:
    statement = key.split(".", 1)[0]
    formula = tuple((-1, t[1:]) if t.startswith("-") else (1, t.lstrip("+")) for t in terms)
    return TemplateLine(key, label, statement, computed=True, flow=statement != "bs", formula=formula)


LINES: tuple[TemplateLine, ...] = (
    # Income statement (flow, fiscal year to date)
    _line("is.revenue", "Net revenue"),
    _line("is.cogs", "Cost of goods sold"),
    _total("is.gross_profit", "Gross profit", "is.revenue", "-is.cogs"),
    _line("is.sga", "Selling, general and administrative"),
    _line("is.depreciation_amortization", "Depreciation and amortization"),
    _line("is.other_operating_expense", "Other operating expense"),
    _line("is.nonrecurring_expense", "Restructuring and other non-recurring charges"),
    _total(
        "is.operating_income", "Operating income",
        "is.gross_profit", "-is.sga", "-is.depreciation_amortization",
        "-is.other_operating_expense", "-is.nonrecurring_expense",
    ),
    _line("is.interest_expense", "Interest expense"),
    _line("is.other_income_net", "Other income (expense), net"),
    _total(
        "is.pretax_income", "Income before taxes",
        "is.operating_income", "-is.interest_expense", "is.other_income_net",
    ),
    _line("is.income_tax_expense", "Income tax expense"),
    _total("is.net_income", "Net income", "is.pretax_income", "-is.income_tax_expense"),
    # Balance sheet (point in time)
    _line("bs.cash", "Cash and equivalents"),
    _line("bs.accounts_receivable", "Accounts receivable, net"),
    _line("bs.inventory", "Inventory"),
    _line("bs.other_current_assets", "Other current assets"),
    _total(
        "bs.total_current_assets", "Total current assets",
        "bs.cash", "bs.accounts_receivable", "bs.inventory", "bs.other_current_assets",
    ),
    _line("bs.net_ppe", "Property and equipment, net"),
    _line("bs.intangibles", "Goodwill and intangibles"),
    _line("bs.other_noncurrent_assets", "Other assets"),
    _total(
        "bs.total_assets", "Total assets",
        "bs.total_current_assets", "bs.net_ppe", "bs.intangibles", "bs.other_noncurrent_assets",
    ),
    _line("bs.accounts_payable", "Accounts payable"),
    _line("bs.accrued_liabilities", "Accrued liabilities"),
    _line("bs.revolver", "Line of credit"),
    _line("bs.cpltd", "Current portion of long-term debt"),
    _line("bs.other_current_liabilities", "Other current liabilities"),
    _total(
        "bs.total_current_liabilities", "Total current liabilities",
        "bs.accounts_payable", "bs.accrued_liabilities", "bs.revolver", "bs.cpltd",
        "bs.other_current_liabilities",
    ),
    _line("bs.long_term_debt", "Long-term debt, net of current portion"),
    _line("bs.subordinated_debt", "Subordinated debt"),
    _line("bs.other_noncurrent_liabilities", "Other liabilities"),
    _total(
        "bs.total_liabilities", "Total liabilities",
        "bs.total_current_liabilities", "bs.long_term_debt", "bs.subordinated_debt",
        "bs.other_noncurrent_liabilities",
    ),
    _line("bs.total_equity", "Total equity"),
    _total(
        "bs.total_liabilities_and_equity", "Total liabilities and equity",
        "bs.total_liabilities", "bs.total_equity",
    ),
    # Cash flow (flow, fiscal year to date, indirect)
    _line("cf.net_income", "Net income"),
    _line("cf.depreciation_amortization", "Depreciation and amortization"),
    _line("cf.change_in_working_capital", "Changes in working capital"),
    _line("cf.other_operating", "Other operating items"),
    _total(
        "cf.cfo", "Net cash from operating activities",
        "cf.net_income", "cf.depreciation_amortization", "cf.change_in_working_capital",
        "cf.other_operating",
    ),
    _line("cf.capex", "Purchases of property and equipment", sign=-1),
    _line("cf.other_investing", "Other investing"),
    _total("cf.cfi", "Net cash from investing", "-cf.capex", "cf.other_investing"),
    _line("cf.revolver_net", "Net borrowings on line of credit"),
    _line("cf.term_debt_proceeds", "Proceeds from long-term debt"),
    _line("cf.term_debt_repayments", "Repayments of long-term debt", sign=-1),
    _line("cf.distributions", "Distributions to owners", sign=-1),
    _line("cf.other_financing", "Other financing"),
    _total(
        "cf.cff", "Net cash from financing",
        "cf.revolver_net", "cf.term_debt_proceeds", "-cf.term_debt_repayments",
        "-cf.distributions", "cf.other_financing",
    ),
    _total("cf.net_change_in_cash", "Net change in cash", "cf.cfo", "cf.cfi", "cf.cff"),
    # Supplemental (from the notes page)
    _line("sup.cash_interest_paid", "Cash paid for interest"),
    _line("sup.cash_taxes_paid", "Cash paid for income taxes"),
    _line("sup.scheduled_principal", "Scheduled principal payments on term debt"),
    _line("sup.financed_capex", "Capital expenditures financed with purchase-money debt"),
)

LINE_BY_KEY: dict[str, TemplateLine] = {line.key: line for line in LINES}

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
})


def known_labels(key: str) -> tuple[str, ...]:
    """Every name a line is known by: the template's label first, then its synonyms."""
    return (LINE_BY_KEY[key].label, *SYNONYMS.get(key, ()))



# Facts the expression engine may read that are not template lines. Availability is produced
# by `borrowing_base` and stored by the caller as a calculated, point-in-time fact.
EXTRA_LINES: dict[str, TemplateLine] = {
    "bb.availability": TemplateLine("bb.availability", "Availability", "bb", flow=False),
}


def line_info(key: str) -> TemplateLine | None:
    """The line for a key the engine can read, or None if the key is unknown."""
    return LINE_BY_KEY.get(key) or EXTRA_LINES.get(key)


def stored_value(key: str, printed: Decimal) -> Decimal:
    """Stored value = presentation_sign x printed value (parentheses already parsed as negative)."""
    return LINE_BY_KEY[key].presentation_sign * printed


def _dependents(key: str) -> set[str]:
    """Computed lines that depend, directly or through other totals, on `key`."""
    found: set[str] = set()
    frontier = {key}
    while frontier:
        nxt = {line.key for line in LINES if line.computed and any(k in frontier for _, k in line.formula)}
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
) -> StatementResult:
    """Compute every computed line of the chosen statements from input lines.

    `absent` lines count as zero here; whether they are *allowed* to is decided by
    `check_statement`. `stated.*` keys are ignored. A missing input is an error naming the
    line, and the totals that depend on it are left out rather than computed from zero.
    """
    chosen = _selected(statements)
    result = StatementResult()
    absent_set = set(absent)

    for key in sorted(absent_set):
        line = LINE_BY_KEY.get(key)
        if line is None:
            result.errors.append(CalcError(E.UNKNOWN_KEY, f"absent line {key} is not in template {TEMPLATE_ID}", key=key))
        elif line.computed:
            result.errors.append(CalcError(E.INVALID_VALUE, f"computed line {key} cannot be marked absent", key=key))
        elif key in inputs:
            result.errors.append(CalcError(E.INVALID_VALUE, f"line {key} is both supplied and marked absent", key=key))

    bad: set[str] = set()
    for key, value in inputs.items():
        if isinstance(key, str) and key.startswith(STATED_PREFIX):
            stated_key = key[len(STATED_PREFIX):]
            if stated_key not in LINE_BY_KEY or not LINE_BY_KEY[stated_key].computed:
                result.errors.append(CalcError(E.UNKNOWN_KEY, f"{key} is not a stated total of template {TEMPLATE_ID}", key=key))
            elif not is_decimal(value):
                result.errors.append(_bad_value(key, value))
            continue
        line = LINE_BY_KEY.get(key)
        if line is None:
            result.errors.append(CalcError(E.UNKNOWN_KEY, f"line {key} is not in template {TEMPLATE_ID}", key=key))
        elif line.computed:
            result.errors.append(
                CalcError(E.COMPUTED_LINE_SUPPLIED, f"{key} is computed; supply the printed total as stated.{key}", key=key)
            )
        elif not is_decimal(value):
            result.errors.append(_bad_value(key, value))
            bad.add(key)

    for line in LINES:
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

_TIES = (("cf.net_income", "is.net_income"), ("cf.depreciation_amortization", "is.depreciation_amortization"))


def check_statement(
    inputs: Mapping[str, Decimal],
    *,
    scale: int,
    prior_fye_cash: Decimal | None,
    absent: Collection[str] = (),
    statements: Iterable[str] | None = None,
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
    chosen = _selected(statements)
    computed = compute_statement(inputs, absent=absent, statements=chosen)
    report = CheckReport(values=computed.values, computed=computed.computed, errors=list(computed.errors))
    values = report.values
    unit = Decimal(scale)

    for line in LINES:
        if not line.computed or line.statement not in chosen:
            continue
        stated = inputs.get(STATED_PREFIX + line.key)
        if line.key not in values or not is_decimal(stated):
            report.checks.append(CheckResult("footing", line.key, "not_checked"))
            continue
        report.checks.append(_compare("footing", line.key, values[line.key], stated, unit * len(line.formula)))

    if "bs.total_assets" in values and "bs.total_liabilities_and_equity" in values:
        report.checks.append(
            _compare("balance", "bs.total_assets", values["bs.total_assets"], values["bs.total_liabilities_and_equity"], unit)
        )
    elif "bs" in chosen:
        report.checks.append(CheckResult("balance", "bs.total_assets", "not_checked"))

    for cf_key, is_key in _TIES:
        if cf_key in values and is_key in values:
            report.checks.append(_compare("tie", cf_key, values[cf_key], values[is_key], unit))
        elif "cf" in chosen:
            report.checks.append(CheckResult("tie", cf_key, "not_checked"))

    if "cf" in chosen:
        if "cf.net_change_in_cash" in values and "bs.cash" in values and prior_fye_cash is not None:
            report.checks.append(
                _compare("cash_roll", "cf.net_change_in_cash", values["cf.net_change_in_cash"],
                         values["bs.cash"] - prior_fye_cash, unit * 2)
            )
        else:
            report.checks.append(CheckResult("cash_roll", "cf.net_change_in_cash", "not_checked"))

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
        line = LINE_BY_KEY.get(key)
        if line is None or line.computed or key in inputs:
            continue  # already reported by compute_statement
        section = [c for k, c in footing.items() if LINE_BY_KEY[k].statement == line.statement]
        covered = any(footing[k].status == "pass" for k in _dependents(key) if k in footing)
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
