"""Ground-truth financial model for the synthetic book.

A borrower is simulated quarter by quarter from an opening balance sheet at
2022-12-31. Every balance and flow is a `Decimal` rounded to the borrower's
reporting scale (whole dollars or whole thousands) before it enters a
statement, so every printed figure is exactly derivable from the truth.

The statements are consistent by construction:

* balance sheet lines are set directly, flows are derived from their changes;
* the line of credit is the plug that holds cash at its target;
* equity moves only by net income less distributions.

`check_periods` re-verifies every identity from the published figures alone.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

D = Decimal
ZERO = D(0)

FIRST_SIM_YEAR = 2023
FIRST_TRUTH_YEAR = 2024
LAST_YEAR = 2026
LAST_QUARTER = 3
QUARTER_END = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}


@dataclass(frozen=True)
class Line:
    key: str
    label: str
    statement: str  # income_statement | balance_sheet | cash_flow | supplemental
    computed: bool
    sign: int  # presentation sign: stored = sign x printed


TEMPLATE: tuple[Line, ...] = (
    Line("is.revenue", "Net revenue", "income_statement", False, 1),
    Line("is.cogs", "Cost of goods sold", "income_statement", False, 1),
    Line("is.gross_profit", "Gross profit", "income_statement", True, 1),
    Line("is.sga", "Selling, general and administrative", "income_statement", False, 1),
    Line("is.depreciation_amortization", "Depreciation and amortization", "income_statement", False, 1),
    Line("is.other_operating_expense", "Other operating expense", "income_statement", False, 1),
    Line(
        "is.nonrecurring_expense",
        "Restructuring and other non-recurring charges",
        "income_statement",
        False,
        1,
    ),
    Line("is.operating_income", "Operating income", "income_statement", True, 1),
    Line("is.interest_expense", "Interest expense", "income_statement", False, 1),
    Line("is.other_income_net", "Other income (expense), net", "income_statement", False, 1),
    Line("is.pretax_income", "Income before taxes", "income_statement", True, 1),
    Line("is.income_tax_expense", "Income tax expense", "income_statement", False, 1),
    Line("is.net_income", "Net income", "income_statement", True, 1),
    Line("bs.cash", "Cash and equivalents", "balance_sheet", False, 1),
    Line("bs.accounts_receivable", "Accounts receivable, net", "balance_sheet", False, 1),
    Line("bs.inventory", "Inventory", "balance_sheet", False, 1),
    Line("bs.other_current_assets", "Other current assets", "balance_sheet", False, 1),
    Line("bs.total_current_assets", "Total current assets", "balance_sheet", True, 1),
    Line("bs.net_ppe", "Property and equipment, net", "balance_sheet", False, 1),
    Line("bs.intangibles", "Goodwill and intangibles", "balance_sheet", False, 1),
    Line("bs.other_noncurrent_assets", "Other assets", "balance_sheet", False, 1),
    Line("bs.total_assets", "Total assets", "balance_sheet", True, 1),
    Line("bs.accounts_payable", "Accounts payable", "balance_sheet", False, 1),
    Line("bs.accrued_liabilities", "Accrued liabilities", "balance_sheet", False, 1),
    Line("bs.revolver", "Line of credit", "balance_sheet", False, 1),
    Line("bs.cpltd", "Current portion of long-term debt", "balance_sheet", False, 1),
    Line("bs.other_current_liabilities", "Other current liabilities", "balance_sheet", False, 1),
    Line("bs.total_current_liabilities", "Total current liabilities", "balance_sheet", True, 1),
    Line("bs.long_term_debt", "Long-term debt, net of current portion", "balance_sheet", False, 1),
    Line("bs.subordinated_debt", "Subordinated debt", "balance_sheet", False, 1),
    Line("bs.other_noncurrent_liabilities", "Other liabilities", "balance_sheet", False, 1),
    Line("bs.total_liabilities", "Total liabilities", "balance_sheet", True, 1),
    Line("bs.total_equity", "Total equity", "balance_sheet", False, 1),
    Line("bs.total_liabilities_and_equity", "Total liabilities and equity", "balance_sheet", True, 1),
    Line("cf.net_income", "Net income", "cash_flow", False, 1),
    Line("cf.depreciation_amortization", "Depreciation and amortization", "cash_flow", False, 1),
    Line("cf.change_in_working_capital", "Changes in working capital", "cash_flow", False, 1),
    Line("cf.other_operating", "Other operating items", "cash_flow", False, 1),
    Line("cf.cfo", "Net cash from operating activities", "cash_flow", True, 1),
    Line("cf.capex", "Purchases of property and equipment", "cash_flow", False, -1),
    Line("cf.other_investing", "Other investing", "cash_flow", False, 1),
    Line("cf.cfi", "Net cash from investing", "cash_flow", True, 1),
    Line("cf.revolver_net", "Net borrowings on line of credit", "cash_flow", False, 1),
    Line("cf.term_debt_proceeds", "Proceeds from long-term debt", "cash_flow", False, 1),
    Line("cf.term_debt_repayments", "Repayments of long-term debt", "cash_flow", False, -1),
    Line("cf.distributions", "Distributions to owners", "cash_flow", False, -1),
    Line("cf.other_financing", "Other financing", "cash_flow", False, 1),
    Line("cf.cff", "Net cash from financing", "cash_flow", True, 1),
    Line("cf.net_change_in_cash", "Net change in cash", "cash_flow", True, 1),
    Line("sup.cash_interest_paid", "Cash paid for interest", "supplemental", False, 1),
    Line("sup.cash_taxes_paid", "Cash paid for income taxes", "supplemental", False, 1),
    Line("sup.scheduled_principal", "Scheduled principal payments on term debt", "supplemental", False, 1),
    Line(
        "sup.financed_capex",
        "Capital expenditures financed with purchase-money debt",
        "supplemental",
        False,
        1,
    ),
)
LINES: dict[str, Line] = {line.key: line for line in TEMPLATE}
FLOW_KEYS = tuple(k for k in LINES if k.split(".")[0] in ("is", "cf", "sup"))
POINT_KEYS = tuple(k for k in LINES if k.startswith("bs."))

# Computed lines, in dependency order: key -> list of (sign, component key).
FORMULAS: dict[str, tuple[tuple[int, str], ...]] = {
    "is.gross_profit": ((1, "is.revenue"), (-1, "is.cogs")),
    "is.operating_income": (
        (1, "is.gross_profit"),
        (-1, "is.sga"),
        (-1, "is.depreciation_amortization"),
        (-1, "is.other_operating_expense"),
        (-1, "is.nonrecurring_expense"),
    ),
    "is.pretax_income": ((1, "is.operating_income"), (-1, "is.interest_expense"), (1, "is.other_income_net")),
    "is.net_income": ((1, "is.pretax_income"), (-1, "is.income_tax_expense")),
    "bs.total_current_assets": (
        (1, "bs.cash"),
        (1, "bs.accounts_receivable"),
        (1, "bs.inventory"),
        (1, "bs.other_current_assets"),
    ),
    "bs.total_assets": (
        (1, "bs.total_current_assets"),
        (1, "bs.net_ppe"),
        (1, "bs.intangibles"),
        (1, "bs.other_noncurrent_assets"),
    ),
    "bs.total_current_liabilities": (
        (1, "bs.accounts_payable"),
        (1, "bs.accrued_liabilities"),
        (1, "bs.revolver"),
        (1, "bs.cpltd"),
        (1, "bs.other_current_liabilities"),
    ),
    "bs.total_liabilities": (
        (1, "bs.total_current_liabilities"),
        (1, "bs.long_term_debt"),
        (1, "bs.subordinated_debt"),
        (1, "bs.other_noncurrent_liabilities"),
    ),
    "bs.total_liabilities_and_equity": ((1, "bs.total_liabilities"), (1, "bs.total_equity")),
    "cf.cfo": (
        (1, "cf.net_income"),
        (1, "cf.depreciation_amortization"),
        (1, "cf.change_in_working_capital"),
        (1, "cf.other_operating"),
    ),
    "cf.cfi": ((-1, "cf.capex"), (1, "cf.other_investing")),
    "cf.cff": (
        (1, "cf.revolver_net"),
        (1, "cf.term_debt_proceeds"),
        (-1, "cf.term_debt_repayments"),
        (-1, "cf.distributions"),
        (1, "cf.other_financing"),
    ),
    "cf.net_change_in_cash": ((1, "cf.cfo"), (1, "cf.cfi"), (1, "cf.cff")),
}


def apply_formulas(values: dict[str, Decimal]) -> None:
    """Fill every computed line from its inputs (in place)."""
    for key, parts in FORMULAS.items():
        values[key] = sum((sign * values[comp] for sign, comp in parts), ZERO)


def period_end(year: int, quarter: int) -> date:
    month, day = QUARTER_END[quarter]
    return date(year, month, day)


@dataclass
class QuarterAdj:
    """Scenario adjustments for one quarter, added to the borrower's base drivers."""

    growth: Decimal = ZERO  # added to year-on-year revenue growth
    margin: Decimal = ZERO  # added to gross margin
    sga: Decimal = ZERO  # added to SG&A as a share of revenue
    dso: Decimal = ZERO  # days
    dio: Decimal = ZERO
    dpo: Decimal = ZERO
    nonrecurring: Decimal = ZERO  # dollars of restructuring and other non-recurring charges
    financed_capex: Decimal = ZERO  # dollars of capex financed with a new purchase-money note
    extra_capex: Decimal = ZERO
    prepayment: Decimal = ZERO  # voluntary term loan prepayment


@dataclass
class ModelParams:
    borrower_id: str
    seed: int
    scale: int  # 1000 = statements in thousands, 1 = whole dollars
    revenue_2023: Decimal
    seasonality: tuple[Decimal, Decimal, Decimal, Decimal]
    growth: Decimal
    gross_margin: Decimal
    sga_pct: Decimal
    other_opex_pct: Decimal
    other_income_pct: Decimal
    tax_rate: Decimal
    dist_floor: Decimal  # share of net income always distributed
    dist_cap: Decimal  # most that is distributed
    dso: Decimal
    dio: Decimal
    dpo: Decimal
    oca_pct: Decimal
    accrued_pct: Decimal  # of annualised SG&A
    ocl_pct: Decimal
    ppe_pct: Decimal
    capex_pct: Decimal
    intangibles_pct: Decimal
    onca_pct: Decimal
    oncl_pct: Decimal
    cash_pct: Decimal
    has_revolver: bool
    revolver_pct: Decimal  # target line usage as a share of annualised revenue
    term_pct: Decimal  # opening term loan as a share of 2023 revenue
    term_amort_years: int
    sub_debt_pct: Decimal
    revolver_rate: Decimal = D("0.0775")
    term_rate: Decimal = D("0.0710")
    sub_rate: Decimal = D("0.1150")
    onca_drift: Decimal = ZERO  # quarterly growth in other assets, as a share of opening
    adjustments: dict[tuple[int, int], QuarterAdj] = field(default_factory=dict)


@dataclass
class Quarter:
    year: int
    quarter: int
    flows: dict[str, Decimal]  # discrete quarter, input lines only
    balances: dict[str, Decimal]  # quarter end, input lines only
    memo: dict[str, Decimal]


@dataclass
class Period:
    period_end: date
    months: int
    fiscal_year: int
    quarter: int
    quality: str
    scale: int
    values: dict[str, Decimal]
    memo: dict[str, Decimal]


@dataclass
class _Note:
    balance: Decimal
    payment: Decimal


def simulate(p: ModelParams) -> tuple[dict[str, Decimal], list[Quarter]]:
    """Return the opening balance sheet (2022-12-31) and the discrete quarters."""
    rng = random.Random(f"{p.seed}:{p.borrower_id}:model")
    unit = D(p.scale)

    def rq(x: Decimal) -> Decimal:
        return (x / unit).quantize(D(1), rounding=ROUND_HALF_UP) * unit

    def noise(spread: int, denom: int) -> Decimal:
        return D(rng.randint(-spread, spread)) / D(denom)

    rev0 = p.revenue_2023
    cogs0 = rev0 * (1 - p.gross_margin)
    revolver = rq(rev0 * p.revolver_pct) if p.has_revolver else ZERO
    notes = []
    term0 = rq(rev0 * p.term_pct)
    if term0 > 0:
        notes.append(_Note(term0, rq(term0 / D(p.term_amort_years * 4))))
    sub = rq(rev0 * p.sub_debt_pct)
    interest0 = (revolver * p.revolver_rate + term0 * p.term_rate + sub * p.sub_rate) / 4
    accrued_int = rq(interest0 / 3)
    ebt0 = rev0 * (p.gross_margin - p.sga_pct - p.other_opex_pct) / 4 - interest0
    tax_payable = rq(max(ebt0, ZERO) * p.tax_rate * D("0.8"))
    bal = {
        "bs.cash": rq(rev0 * p.cash_pct),
        "bs.accounts_receivable": rq(rev0 * p.dso / 365),
        "bs.inventory": rq(cogs0 * p.dio / 365),
        "bs.other_current_assets": rq(rev0 * p.oca_pct),
        "bs.net_ppe": rq(rev0 * p.ppe_pct),
        "bs.intangibles": rq(rev0 * p.intangibles_pct),
        "bs.other_noncurrent_assets": rq(rev0 * p.onca_pct),
        "bs.accounts_payable": rq(cogs0 * p.dpo / 365),
        "bs.accrued_liabilities": rq(rev0 * p.sga_pct * p.accrued_pct) + accrued_int,
        "bs.revolver": revolver,
        "bs.cpltd": sum((min(n.balance, 4 * n.payment) for n in notes), ZERO),
        "bs.other_current_liabilities": rq(rev0 * p.ocl_pct) + tax_payable,
        "bs.subordinated_debt": sub,
        "bs.other_noncurrent_liabilities": rq(rev0 * p.oncl_pct),
    }
    bal["bs.long_term_debt"] = term0 - bal["bs.cpltd"]
    assets = sum(
        bal[k]
        for k in (
            "bs.cash",
            "bs.accounts_receivable",
            "bs.inventory",
            "bs.other_current_assets",
            "bs.net_ppe",
            "bs.intangibles",
            "bs.other_noncurrent_assets",
        )
    )
    liabilities = sum(
        bal[k]
        for k in (
            "bs.accounts_payable",
            "bs.accrued_liabilities",
            "bs.revolver",
            "bs.cpltd",
            "bs.other_current_liabilities",
            "bs.long_term_debt",
            "bs.subordinated_debt",
            "bs.other_noncurrent_liabilities",
        )
    )
    bal["bs.total_equity"] = assets - liabilities
    if bal["bs.total_equity"] <= 0:
        raise ValueError(f"{p.borrower_id}: opening equity is not positive")
    paid_in = rq(bal["bs.total_equity"] * D("0.35"))
    retained = bal["bs.total_equity"] - paid_in
    opening = dict(bal)
    oncl_step = rq(bal["bs.other_noncurrent_liabilities"] * D("0.012"))
    onca_step = rq(bal["bs.other_noncurrent_assets"] * p.onca_drift)
    da_rate = p.capex_pct * D("0.92") / p.ppe_pct if p.ppe_pct > 0 else ZERO

    quarters: list[Quarter] = []
    revenue: dict[tuple[int, int], Decimal] = {}
    for year in range(FIRST_SIM_YEAR, LAST_YEAR + 1):
        for q in range(1, 5):
            if year == LAST_YEAR and q > LAST_QUARTER:
                break
            adj = p.adjustments.get((year, q), QuarterAdj())
            g_noise, m_noise, d_noise = noise(120, 10000), noise(35, 10000), noise(15, 10)
            if year == FIRST_SIM_YEAR:
                rev = rq(rev0 / 4 * p.seasonality[q - 1])
            else:
                rev = rq(revenue[(year - 1, q)] * (1 + p.growth + g_noise + adj.growth))
            revenue[(year, q)] = rev
            prev = bal
            cogs = rq(rev * (1 - (p.gross_margin + m_noise + adj.margin)))
            sga = rq(rev * (p.sga_pct + adj.sga))
            da = rq(prev["bs.net_ppe"] * da_rate / 4)
            other_opex = rq(rev * p.other_opex_pct)
            nonrecurring = rq(adj.nonrecurring)
            term_prev = prev["bs.cpltd"] + prev["bs.long_term_debt"]
            interest = rq(
                (
                    prev["bs.revolver"] * p.revolver_rate
                    + term_prev * p.term_rate
                    + prev["bs.subordinated_debt"] * p.sub_rate
                )
                / 4
            )
            other_income = rq(rev * p.other_income_pct)
            pretax = rev - cogs - sga - da - other_opex - nonrecurring - interest + other_income
            tax = rq(pretax * p.tax_rate) if pretax > 0 else ZERO
            net_income = pretax - tax

            financed = rq(adj.financed_capex)
            capex = rq(rev * p.capex_pct) + rq(adj.extra_capex) + financed
            new_accrued_int = rq(interest / 3)
            bal = {
                "bs.accounts_receivable": rq(rev * 4 * (p.dso + d_noise + adj.dso) / 365),
                "bs.inventory": rq(cogs * 4 * (p.dio + adj.dio) / 365) if p.dio > 0 else ZERO,
                "bs.other_current_assets": rq(rev * 4 * p.oca_pct),
                "bs.net_ppe": prev["bs.net_ppe"] + capex - da,
                "bs.intangibles": prev["bs.intangibles"],
                "bs.other_noncurrent_assets": prev["bs.other_noncurrent_assets"] + onca_step,
                "bs.accounts_payable": rq(cogs * 4 * (p.dpo + adj.dpo) / 365),
                "bs.accrued_liabilities": rq(sga * 4 * p.accrued_pct) + new_accrued_int,
                "bs.other_current_liabilities": rq(rev * 4 * p.ocl_pct) + tax,
                "bs.subordinated_debt": prev["bs.subordinated_debt"],
                "bs.other_noncurrent_liabilities": prev["bs.other_noncurrent_liabilities"] + oncl_step,
            }
            # Term debt: scheduled payments, any prepayment, then any new purchase-money note.
            scheduled = ZERO
            for note in notes:
                pay = min(note.payment, note.balance)
                note.balance -= pay
                scheduled += pay
            prepayment = ZERO
            if adj.prepayment > 0 and notes:
                prepayment = min(rq(adj.prepayment), notes[0].balance)
                notes[0].balance -= prepayment
            if financed > 0:
                notes.append(_Note(financed, rq(financed / 20)))
            term_total = sum((n.balance for n in notes), ZERO)
            bal["bs.cpltd"] = sum((min(n.balance, 4 * n.payment) for n in notes), ZERO)
            bal["bs.long_term_debt"] = term_total - bal["bs.cpltd"]

            working_capital = (
                -(bal["bs.accounts_receivable"] - prev["bs.accounts_receivable"])
                - (bal["bs.inventory"] - prev["bs.inventory"])
                - (bal["bs.other_current_assets"] - prev["bs.other_current_assets"])
                + (bal["bs.accounts_payable"] - prev["bs.accounts_payable"])
                + (bal["bs.accrued_liabilities"] - prev["bs.accrued_liabilities"])
                + (bal["bs.other_current_liabilities"] - prev["bs.other_current_liabilities"])
            )
            other_operating = oncl_step
            other_investing = -onca_step
            cfo = net_income + da + working_capital + other_operating
            cfi = -capex + other_investing
            repayments = scheduled + prepayment
            before_owners = prev["bs.cash"] + cfo + cfi + financed - repayments
            target_cash = rq(rev * 4 * p.cash_pct)
            target_revolver = rq(rev * 4 * p.revolver_pct) if p.has_revolver else ZERO
            # Owners take what is left after holding cash and the line at their targets,
            # within a floor and a cap set as shares of net income.
            excess = before_owners - target_cash + (target_revolver - prev["bs.revolver"])
            earned = max(net_income, ZERO)
            distributions = rq(min(max(excess, earned * p.dist_floor), earned * p.dist_cap))
            pre_plug = before_owners - distributions
            if p.has_revolver:
                new_revolver = max(ZERO, prev["bs.revolver"] + (target_cash - pre_plug))
            else:
                new_revolver = ZERO
            revolver_net = new_revolver - prev["bs.revolver"]
            bal["bs.revolver"] = new_revolver
            bal["bs.cash"] = pre_plug + revolver_net
            if bal["bs.cash"] <= 0:
                raise ValueError(f"{p.borrower_id}: cash is not positive in {year} Q{q}")
            retained_before = retained
            retained = retained + net_income - distributions
            bal["bs.total_equity"] = paid_in + retained

            flows = {
                "is.revenue": rev,
                "is.cogs": cogs,
                "is.sga": sga,
                "is.depreciation_amortization": da,
                "is.other_operating_expense": other_opex,
                "is.nonrecurring_expense": nonrecurring,
                "is.interest_expense": interest,
                "is.other_income_net": other_income,
                "is.income_tax_expense": tax,
                "cf.net_income": net_income,
                "cf.depreciation_amortization": da,
                "cf.change_in_working_capital": working_capital,
                "cf.other_operating": other_operating,
                "cf.capex": capex,
                "cf.other_investing": other_investing,
                "cf.revolver_net": revolver_net,
                "cf.term_debt_proceeds": financed,
                "cf.term_debt_repayments": repayments,
                "cf.distributions": distributions,
                "cf.other_financing": ZERO,
                "sup.cash_interest_paid": interest - (new_accrued_int - accrued_int),
                "sup.cash_taxes_paid": tax - (tax - tax_payable),
                "sup.scheduled_principal": scheduled,
                "sup.financed_capex": financed,
            }
            accrued_int, tax_payable = new_accrued_int, tax
            memo = {
                "equity.paid_in_capital": paid_in,
                "equity.retained_earnings": retained,
                "equity.retained_earnings_before": retained_before,
                "debt.term_total": term_total,
                "debt.next_twelve_months_principal": bal["bs.cpltd"],
            }
            quarters.append(Quarter(year, q, flows, dict(bal), memo))
    return opening, quarters


def build_periods(opening: dict[str, Decimal], quarters: list[Quarter], scale: int) -> list[Period]:
    """Accumulate discrete quarters into fiscal-year-to-date periods."""
    periods: list[Period] = []
    ytd: dict[str, Decimal] = {}
    cash_at_year_start = opening["bs.cash"]
    for qtr in quarters:
        if qtr.quarter == 1:
            ytd = dict.fromkeys(qtr.flows, ZERO)
            if periods:
                cash_at_year_start = periods[-1].values["bs.cash"]
        for key, amount in qtr.flows.items():
            ytd[key] += amount
        values = {**ytd, **qtr.balances}
        apply_formulas(values)
        memo = {
            "equity.paid_in_capital": qtr.memo["equity.paid_in_capital"],
            "equity.retained_earnings": qtr.memo["equity.retained_earnings"],
            "cash.beginning_of_year": cash_at_year_start,
            "debt.term_total": qtr.memo["debt.term_total"],
        }
        periods.append(
            Period(
                period_end=period_end(qtr.year, qtr.quarter),
                months=qtr.quarter * 3,
                fiscal_year=qtr.year,
                quarter=qtr.quarter,
                quality="audited" if qtr.quarter == 4 else "internal",
                scale=scale,
                values={line.key: values[line.key] for line in TEMPLATE},
                memo=memo,
            )
        )
    return periods


def check_periods(periods: list[Period]) -> list[str]:
    """Verify the template checks from published figures only. Returns a list of failures."""
    problems: list[str] = []
    by_end = {p.period_end: p for p in periods}
    for p in periods:
        v, tag = p.values, f"{p.period_end.isoformat()}"
        for key, parts in FORMULAS.items():
            if v[key] != sum((sign * v[comp] for sign, comp in parts), ZERO):
                problems.append(f"{tag}: {key} does not foot")
        if v["bs.total_assets"] != v["bs.total_liabilities_and_equity"]:
            problems.append(f"{tag}: balance sheet does not balance")
        if v["cf.net_income"] != v["is.net_income"]:
            problems.append(f"{tag}: cf.net_income differs from is.net_income")
        if v["cf.depreciation_amortization"] != v["is.depreciation_amortization"]:
            problems.append(f"{tag}: depreciation differs between statements")
        for key, amount in v.items():
            if amount % p.scale != 0:
                problems.append(f"{tag}: {key} is not a whole multiple of the scale")
        if p.memo["equity.paid_in_capital"] + p.memo["equity.retained_earnings"] != v["bs.total_equity"]:
            problems.append(f"{tag}: equity components do not sum to total equity")
        prior = by_end.get(date(p.fiscal_year - 1, 12, 31))
        if prior is None:
            continue
        pv = prior.values
        if v["cf.net_change_in_cash"] != v["bs.cash"] - pv["bs.cash"]:
            problems.append(f"{tag}: cash flow does not tie to the change in cash")
        if p.memo["cash.beginning_of_year"] != pv["bs.cash"]:
            problems.append(f"{tag}: beginning cash differs from prior year end")
        rolled = prior.memo["equity.retained_earnings"] + v["is.net_income"] - v["cf.distributions"]
        if p.memo["equity.retained_earnings"] != rolled + v["cf.other_financing"]:
            problems.append(f"{tag}: retained earnings do not roll forward")
        if v["bs.revolver"] != pv["bs.revolver"] + v["cf.revolver_net"]:
            problems.append(f"{tag}: line of credit does not roll forward")
        term, prior_term = v["bs.cpltd"] + v["bs.long_term_debt"], pv["bs.cpltd"] + pv["bs.long_term_debt"]
        if term != prior_term + v["cf.term_debt_proceeds"] - v["cf.term_debt_repayments"]:
            problems.append(f"{tag}: term debt does not roll forward")
        if v["sup.scheduled_principal"] > v["cf.term_debt_repayments"]:
            problems.append(f"{tag}: scheduled principal exceeds repayments")
        if v["sup.financed_capex"] != v["cf.term_debt_proceeds"]:
            problems.append(f"{tag}: financed capex differs from term debt proceeds")
        ppe = pv["bs.net_ppe"] + v["cf.capex"] - v["is.depreciation_amortization"]
        if v["bs.net_ppe"] != ppe:
            problems.append(f"{tag}: property and equipment does not roll forward")
        if p.months == 12 and pv["bs.cpltd"] > 0 and v["sup.scheduled_principal"] > pv["bs.cpltd"] + v["sup.financed_capex"]:
            problems.append(f"{tag}: scheduled principal exceeds the prior current portion")
    return problems
