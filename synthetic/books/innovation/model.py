"""Monthly truth model for a venture-backed SaaS client (template vc-1).

Twenty-two months are simulated (January 2025 to October 2026) from an opening balance sheet at 2024-12-31; the
last eighteen (May 2025 to October 2026) are published. Everything is whole dollars (`int`), so every printed
figure is exactly derivable from the truth.

Construction runs backwards from the owner's October 2026 figures:

* net burn is chosen first (`burn_path`), with the last three months summing to exactly three times the target;
* net burn = capex + capitalised software spend - operating cash flow (spec 5), so operating cash flow follows;
* total cash is walked back from October 2026 (cash moves by -net burn plus financing inflows); unrestricted cash
  is total cash less the restricted balance;
* working-capital balances are drivers of revenue; net income is then what makes the cash flow identity hold,
  operating expenses are what make net income hold, and accumulated deficit rolls with net income.

The balance sheet therefore balances by construction; `check_periods` re-verifies it from the published figures.
"""

from __future__ import annotations

import calendar
import random
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from synthetic.books.innovation.roster import DEFAULT_SEED, ClientSpec

D = Decimal


def month_end(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


MONTHS: tuple[date, ...] = tuple(month_end(2025, m) for m in range(1, 13)) + tuple(
    month_end(2026, m) for m in range(1, 11)
)
N = len(MONTHS)  # 22 simulated months
LAST = N - 1  # October 2026
PUBLISHED_FROM = 4  # May 2025
OPENING_END = date(2024, 12, 31)
JULY_2026 = MONTHS.index(month_end(2026, 7))
JUNE_2026 = MONTHS.index(month_end(2026, 6))


def rnd(x) -> int:
    return int(D(x).quantize(D(1), rounding=ROUND_HALF_UP))


IS_IN = (
    "is.subscription_revenue", "is.services_revenue", "is.cost_of_revenue", "is.rnd", "is.sales_marketing",
    "is.gna", "is.vc_depreciation_amortization", "is.vc_interest", "is.vc_other_income",
)  # fmt: skip
CF_IN = (
    "cf.vc_operating_cash_flow", "cf.vc_capex", "cf.capitalised_software_spend", "cf.equity_raised",
    "cf.debt_raised", "cf.vc_other_financing",
)  # fmt: skip
SUP = ("sup.cash_interest_paid", "sup.scheduled_principal")
BS_IN = (
    "bs.cash_unrestricted", "bs.cash_restricted", "bs.short_term_investments", "bs.accounts_receivable",
    "bs.other_current_assets", "bs.capitalised_software", "bs.vc_other_intangibles", "bs.other_noncurrent_assets",
    "bs.accounts_payable", "bs.accrued_liabilities", "bs.deferred_revenue_current", "bs.deferred_revenue_noncurrent",
    "bs.venture_debt_current", "bs.venture_debt_noncurrent", "bs.convertible_notes", "bs.safes",
    "bs.vc_other_liabilities", "bs.preferred_equity", "bs.common_equity",
)  # fmt: skip
SAAS = ("saas.mrr", "saas.arr", "saas.customers")
# Subtotals in dependency order: key -> ((sign, component), ...). The generator's own copy of the vc-1 identities.
FORMULAS: dict[str, tuple[tuple[int, str], ...]] = {
    "is.total_revenue": ((1, "is.subscription_revenue"), (1, "is.services_revenue")),
    "is.vc_gross_profit": ((1, "is.total_revenue"), (-1, "is.cost_of_revenue")),
    "is.vc_operating_loss": (
        (1, "is.vc_gross_profit"), (-1, "is.rnd"), (-1, "is.sales_marketing"), (-1, "is.gna"),
        (-1, "is.vc_depreciation_amortization"),
    ),  # fmt: skip
    "is.vc_net_loss": ((1, "is.vc_operating_loss"), (-1, "is.vc_interest"), (1, "is.vc_other_income")),
    "bs.vc_total_cash": ((1, "bs.cash_unrestricted"), (1, "bs.cash_restricted")),
    "bs.vc_total_assets": (
        (1, "bs.vc_total_cash"), (1, "bs.short_term_investments"), (1, "bs.accounts_receivable"),
        (1, "bs.other_current_assets"), (1, "bs.capitalised_software"), (1, "bs.vc_other_intangibles"),
        (1, "bs.other_noncurrent_assets"),
    ),  # fmt: skip
    "bs.vc_total_liabilities": (
        (1, "bs.accounts_payable"), (1, "bs.accrued_liabilities"), (1, "bs.deferred_revenue_current"),
        (1, "bs.deferred_revenue_noncurrent"), (1, "bs.venture_debt_current"), (1, "bs.venture_debt_noncurrent"),
        (1, "bs.convertible_notes"), (1, "bs.safes"), (1, "bs.vc_other_liabilities"),
    ),  # fmt: skip
    "bs.vc_total_equity": ((1, "bs.preferred_equity"), (1, "bs.common_equity")),
    "bs.vc_total_liabilities_and_equity": ((1, "bs.vc_total_liabilities"), (1, "bs.vc_total_equity")),
    "cf.vc_net_change_in_cash": (
        (1, "cf.vc_operating_cash_flow"), (-1, "cf.vc_capex"), (-1, "cf.capitalised_software_spend"),
        (1, "cf.equity_raised"), (1, "cf.debt_raised"), (1, "cf.vc_other_financing"),
    ),  # fmt: skip
}
ALL_KEYS = (
    IS_IN + ("is.total_revenue", "is.vc_gross_profit", "is.vc_operating_loss", "is.vc_net_loss") + BS_IN
    + ("bs.vc_total_cash", "bs.vc_total_assets", "bs.vc_total_liabilities", "bs.vc_total_equity",
       "bs.vc_total_liabilities_and_equity") + CF_IN + ("cf.vc_net_change_in_cash",) + SUP + SAAS
)  # fmt: skip


def is_flow(key: str) -> bool:
    return key.startswith(("is.", "cf.", "sup."))


def apply_formulas(values: dict[str, int]) -> None:
    """Fill every subtotal whose components are all present (the formulas are in dependency order)."""
    for key, parts in FORMULAS.items():
        if all(component in values for _, component in parts):
            values[key] = sum(sign * values[component] for sign, component in parts)


@dataclass
class Month:
    end: date
    flows: dict[str, int]  # the discrete month: input and subtotal flow lines
    balances: dict[str, int]  # month end: balance lines, subtotals and SaaS metrics
    memo: dict[str, object]


@dataclass
class Period:
    period_end: date
    months: int  # fiscal-year-to-date months
    fiscal_year: int
    quality: str
    values: dict[str, int]  # flows are year to date; balances and SaaS metrics are at the period end
    memo: dict[str, object]


def burn_path(spec: ClientSpec, rng: random.Random) -> list[int]:
    """Monthly net burn for the 22 months; the last three sum to exactly three times the target."""
    burn = D(spec.burn)
    base = [D(1)] * N
    if spec.shape == "dip":
        # One heavy month (July 2026): the average then drops out of the October window, so October runway is
        # not lower than September's and a clean client does not trip `runway_falling`.
        base[JULY_2026] = 1 + D(3) / (D(spec.cash) / burn) + D("0.30")
    elif spec.shape == "rising":
        base = [D("1.05") ** (i - LAST) for i in range(N)]
        scale = D(3) / sum(base[LAST - 2 :])
        base = [x * scale for x in base]
    elif spec.shape == "positive":
        base = [D("-0.4") if i < 14 else D(1) for i in range(N)]  # burning modestly until February 2026 (so the trailing-twelve-month DSCR stays well above 1.25x), then generating
    wobble = [D(rng.randint(-40, 40)) / 1000 for _ in range(N)]
    net_burn = [rnd(burn * base[i] * (1 + wobble[i])) for i in range(N)]
    net_burn[LAST] = 3 * spec.burn - net_burn[LAST - 2] - net_burn[LAST - 1]
    return net_burn


def simulate(spec: ClientSpec, seed: int = DEFAULT_SEED) -> tuple[Month, list[Month]]:
    """The opening month (December 2024) and the 22 simulated months."""
    rng = random.Random(f"{seed}:{spec.id}:innovation")
    growth, margin = D(spec.growth), D(spec.gross_margin)
    net_burn = burn_path(spec, rng)
    equity, debt = [0] * N, [0] * N
    for ym, kind, amount in spec.history:
        i = MONTHS.index(month_end(int(ym[:4]), int(ym[5:])))
        (equity if kind == "equity" else debt)[i] += amount

    def mrr_at(i: int) -> int:
        if spec.scenario == "plan_miss":  # grows to June, then loses customers
            if i <= JUNE_2026:
                return rnd(D(spec.extra["jun_mrr"]) / (1 + growth) ** (JUNE_2026 - i))
            return rnd(D(spec.extra["jun_mrr"]) * D(spec.extra["after_june"][i - JUNE_2026 - 1]))
        return rnd(D(spec.mrr) / (1 + growth) ** (LAST - i))

    def customers_at(i: int) -> int:
        return rnd(D(spec.customers) / (1 + growth * D("0.6")) ** (LAST - i))

    idx = range(-1, N)  # index -1 is the opening month
    mrr = {i: mrr_at(i) for i in idx}
    svc = {i: rnd(D("0.06") * mrr[i]) for i in idx}
    rev = {i: mrr[i] + svc[i] for i in idx}  # subscription revenue is the month's MRR
    cor = {i: rnd(rev[i] * (1 - margin)) for i in idx}
    capex = {i: rnd(D("0.012") * rev[i]) for i in idx}
    capsw = {i: rnd(D(spec.capsw_frac) * rev[i]) for i in idx}

    restricted = {i: spec.pledged for i in idx}
    if spec.scenario == "restricted_account":
        restricted.update({i: spec.extra["restricted_before"] for i in range(-1, LAST)})
    total = {LAST: spec.cash + restricted[LAST]}
    for i in range(LAST, -1, -1):  # cash moves by -net burn plus financing inflows
        total[i - 1] = total[i] + net_burn[i] - equity[i] - debt[i]
    cash = {i: total[i] - restricted[i] for i in idx}

    venture = {-1: spec.venture_debt - sum(debt)}
    for i in range(N):
        venture[i] = venture[i - 1] + debt[i]
    interest = {i: rnd(D(venture[i - 1]) * D("0.105") / 12) for i in range(N)}
    other_income = {i: rnd((D(spec.sti) * D("0.04") + D(cash[i - 1]) * D("0.035")) / 12) for i in range(N)}
    receivable = {i: rnd(D(rev[i]) * 38 / 30) for i in idx}
    prepaid = {i: rnd(D("0.30") * rev[i]) for i in idx}
    payable = {i: rnd(D("0.45") * cor[i]) for i in idx}
    accrued = {i: rnd(D("0.35") * rev[i]) for i in idx}
    deferred_current = {i: rnd(D("1.6") * mrr[i]) for i in idx}
    deferred_long = {i: rnd(D("0.25") * mrr[i]) for i in idx}
    software = {-1: 12 * capsw[-1]}
    other_assets = {-1: 8 * capex[-1] + 150_000}
    amortisation, depreciation = {}, {}
    for i in range(N):
        amortisation[i] = rnd(D(software[i - 1]) / 36)
        depreciation[i] = rnd(D(other_assets[i - 1]) / 48)
        software[i] = software[i - 1] + capsw[i] - amortisation[i]
        other_assets[i] = other_assets[i - 1] + capex[i] - depreciation[i]
    intangibles = 0 if spec.id == "stripple-tech" else 120_000
    convertible = 1_000_000 if spec.id == "nimbusfield-security" else 0
    safes = 1_500_000 if spec.id == "halcyon-grid" else 0
    preferred = {-1: 30_000_000}
    for i in range(N):
        preferred[i] = preferred[i - 1] + equity[i]

    def balances(i: int) -> dict[str, int]:
        current = rnd(D(venture[i]) * D("0.25"))
        return {
            "bs.cash_unrestricted": cash[i], "bs.cash_restricted": restricted[i],
            "bs.short_term_investments": spec.sti, "bs.accounts_receivable": receivable[i],
            "bs.other_current_assets": prepaid[i], "bs.capitalised_software": software[i],
            "bs.vc_other_intangibles": intangibles, "bs.other_noncurrent_assets": other_assets[i],
            "bs.accounts_payable": payable[i], "bs.accrued_liabilities": accrued[i],
            "bs.deferred_revenue_current": deferred_current[i], "bs.deferred_revenue_noncurrent": deferred_long[i],
            "bs.venture_debt_current": current, "bs.venture_debt_noncurrent": venture[i] - current,
            "bs.convertible_notes": convertible, "bs.safes": safes, "bs.vc_other_liabilities": 80_000,
            "bs.preferred_equity": preferred[i],
        }  # fmt: skip

    opening_bal = balances(-1)
    assets = sum(opening_bal[k] for k in (
        "bs.cash_unrestricted", "bs.cash_restricted", "bs.short_term_investments", "bs.accounts_receivable",
        "bs.other_current_assets", "bs.capitalised_software", "bs.vc_other_intangibles",
        "bs.other_noncurrent_assets"))  # fmt: skip
    liabilities = sum(opening_bal[k] for k in (
        "bs.accounts_payable", "bs.accrued_liabilities", "bs.deferred_revenue_current",
        "bs.deferred_revenue_noncurrent", "bs.venture_debt_current", "bs.venture_debt_noncurrent",
        "bs.convertible_notes", "bs.safes", "bs.vc_other_liabilities"))  # fmt: skip
    common = {-1: assets - liabilities - opening_bal["bs.preferred_equity"]}  # the opening accumulated deficit
    opening_bal["bs.common_equity"] = common[-1]
    apply_formulas(opening_bal)
    opening = Month(OPENING_END, {}, {**opening_bal, "saas.mrr": mrr[-1], "saas.arr": 12 * mrr[-1],
                                       "saas.customers": customers_at(-1)}, {})  # fmt: skip

    months: list[Month] = []
    for i in range(N):
        cfo = capex[i] + capsw[i] - net_burn[i]
        d_and_a = amortisation[i] + depreciation[i]
        working_capital = (
            (payable[i] - payable[i - 1]) + (accrued[i] - accrued[i - 1])
            + (deferred_current[i] - deferred_current[i - 1]) + (deferred_long[i] - deferred_long[i - 1])
            - (receivable[i] - receivable[i - 1]) - (prepaid[i] - prepaid[i - 1])
        )  # fmt: skip
        net_income = cfo - d_and_a - working_capital
        operating_income = net_income + interest[i] - other_income[i]
        opex = rev[i] - cor[i] - d_and_a - operating_income
        if opex <= 0:
            raise ValueError(f"{spec.id} {MONTHS[i]}: operating expenses are not positive")
        r_and_d, selling = rnd(D("0.36") * opex), rnd(D("0.41") * opex)
        common[i] = common[i - 1] + net_income
        bal = balances(i)
        bal["bs.common_equity"] = common[i]
        bal.update({"saas.mrr": mrr[i], "saas.arr": 12 * mrr[i], "saas.customers": customers_at(i)})
        flows = {
            "is.subscription_revenue": mrr[i], "is.services_revenue": svc[i], "is.cost_of_revenue": cor[i],
            "is.rnd": r_and_d, "is.sales_marketing": selling, "is.gna": opex - r_and_d - selling,
            "is.vc_depreciation_amortization": d_and_a, "is.vc_interest": interest[i],
            "is.vc_other_income": other_income[i], "cf.vc_operating_cash_flow": cfo, "cf.vc_capex": capex[i],
            "cf.capitalised_software_spend": capsw[i], "cf.equity_raised": equity[i], "cf.debt_raised": debt[i],
            "cf.vc_other_financing": 0, "sup.cash_interest_paid": interest[i], "sup.scheduled_principal": 0,
        }  # fmt: skip
        apply_formulas(flows)
        apply_formulas(bal)
        memo = {
            "saas.net_new_arr": 12 * (mrr[i] - mrr[i - 1]),
            "saas.nrr_percent": 104 + (rng.randint(0, 14) if i else 0),
            "software.amortisation": amortisation[i],
        }
        months.append(Month(MONTHS[i], flows, bal, memo))
    return opening, months


def build_periods(months: list[Month]) -> list[Period]:
    """Fiscal-year-to-date periods (all 22; the first four are not published)."""
    periods: list[Period] = []
    ytd: dict[str, int] = {}
    for m in months:
        if m.end.month == 1:
            ytd = dict.fromkeys(m.flows, 0)
        for key, amount in m.flows.items():
            ytd[key] += amount
        values = {**ytd, **m.balances}
        apply_formulas(values)
        quality = "audited" if m.end == date(2025, 12, 31) else "internal"
        periods.append(Period(m.end, m.end.month, m.end.year, quality, {k: values[k] for k in ALL_KEYS}, dict(m.memo)))
    return periods


def comparative_fy2024(opening: Month, fy2025: Period) -> Period:
    """Fiscal 2024, for the comparative column of the audited statements. The simulation starts in January 2025,
    so the 2024 flows are the 2025 flows scaled by 0.62 (a company that grew about 60 percent); the December 2024
    balance sheet is the opening balance sheet."""
    values = {k: rnd(D(v) * D("0.62")) for k, v in fy2025.values.items() if is_flow(k) and k in IS_IN + CF_IN + SUP}
    values.update({k: v for k, v in opening.balances.items() if k in BS_IN + SAAS})
    apply_formulas(values)
    return Period(OPENING_END, 12, 2024, "audited", {k: values[k] for k in ALL_KEYS},
                  {"derived": "fiscal 2024 flows are fiscal 2025 flows scaled by 0.62"})


def check_periods(opening: Month, periods: list[Period]) -> list[str]:
    """Verify the identities from the published figures only. Returns a list of failures."""
    problems: list[str] = []
    by_end = {p.period_end: p for p in periods}
    start_cash = {2025: opening.balances["bs.vc_total_cash"], 2026: by_end[date(2025, 12, 31)].values["bs.vc_total_cash"]}
    for p in periods:
        v, tag = p.values, p.period_end.isoformat()
        for key, parts in FORMULAS.items():
            if v[key] != sum(sign * v[component] for sign, component in parts):
                problems.append(f"{tag}: {key} does not foot")
        if v["bs.vc_total_assets"] != v["bs.vc_total_liabilities_and_equity"]:
            problems.append(f"{tag}: balance sheet does not balance")
        if v["cf.vc_net_change_in_cash"] != v["bs.vc_total_cash"] - start_cash[p.fiscal_year]:
            problems.append(f"{tag}: cash flow does not tie to the change in cash")
        if v["saas.arr"] != 12 * v["saas.mrr"]:
            problems.append(f"{tag}: ARR is not twelve times MRR")
        for key in ("bs.cash_unrestricted", "bs.accounts_receivable", "bs.accounts_payable", "saas.mrr"):
            if v[key] < 0:
                problems.append(f"{tag}: {key} is negative")
    return problems
