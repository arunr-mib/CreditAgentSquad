"""Expected results, computed with plain arithmetic.

This module is deliberately independent of `backend/app/calc`: the product's
calculation engine must reproduce these numbers, and a disagreement between
the two is investigated, never patched. Everything here is written to be
read top to bottom by a credit analyst: no expression trees, no registry.

Conventions (see synthetic/README.md):

* trailing twelve months = YTD(current) + FY(prior) - YTD(same period, prior year);
  at a fiscal year end it is the fiscal year;
* a ratio is rounded to 2 decimals half-up, a dollar amount to 0 decimals, and
  the rounded value is compared with the threshold;
* a missing input is an error (`MissingInput`), never zero; a null cap is no cap.
"""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

D = Decimal
ZERO = D(0)

SIGNAL_SEVERITY = {
    "covenant_headroom_low": "medium",
    "covenant_headroom_falling": "low",
    "revenue_ttm_decline": "medium",
    "ebitda_margin_decline": "medium",
    "dso_increase": "medium",
    "dpo_increase": "medium",
    "leverage_increase": "medium",
    "net_loss_ttm": "high",
    "cash_decline": "medium",
    "line_usage_high": "medium",
    "availability_low": "medium",
    "reporting_late": "high",
    "payment_past_due": "high",
}
SIGNAL_TRIGGER = {
    "covenant_headroom_low": "0.10",
    "revenue_ttm_decline": "-0.10",
    "ebitda_margin_decline": "-0.03",
    "dso_increase": "10",
    "dpo_increase": "15",
    "leverage_increase": "0.5",
    "net_loss_ttm": "0",
    "cash_decline": "-0.30",
    "line_usage_high": "0.90",
    "availability_low": "0.10",
    "reporting_late": "15",
    "payment_past_due": "10",
}
EXCEPTION_SEVERITY = {
    "covenant.reported_mismatch": "critical",
    "covenant.breach": "high",
    "bb.over_advance": "high",
    "signal.high": "high",
    "terms.unapproved_amendment": "high",
    "bb.certificate_mismatch": "medium",
    "intake.missing_document": "medium",
    "spread.restatement": "medium",
    "spread.does_not_foot": "medium",
    "spread.image_only": "medium",
}
RATIO_TOLERANCE = D("0.01")
DOLLAR_TOLERANCE = D("1000")


class MissingInput(Exception):
    """A figure needed for a calculation is not available."""


def round_half_up(value: Decimal, dp: int) -> Decimal:
    return value.quantize(D(1).scaleb(-dp), rounding=ROUND_HALF_UP)


class Financials:
    """Read access to a borrower's periods. Periods need `period_end`, `months`, `values`."""

    def __init__(self, periods) -> None:
        self._by_end = {p.period_end: p for p in periods}

    def _period(self, end: date):
        if end not in self._by_end:
            raise MissingInput(f"no period ending {end.isoformat()}")
        return self._by_end[end]

    def _value(self, key: str, end: date) -> Decimal:
        values = self._period(end).values
        if key not in values:
            raise MissingInput(f"{key} at {end.isoformat()}")
        return values[key]

    def point(self, key: str, end: date) -> Decimal:
        return self._value(key, end)

    def ytd(self, key: str, end: date) -> Decimal:
        return self._value(key, end)

    def ttm(self, key: str, end: date) -> Decimal:
        if self._period(end).months == 12:
            return self._value(key, end)
        prior_year_end = date(end.year - 1, 12, 31)
        same_period_prior_year = date(end.year - 1, end.month, end.day)
        return self._value(key, end) + self._value(key, prior_year_end) - self._value(key, same_period_prior_year)


# --------------------------------------------------------------------------- metrics


def ebitda_ttm(fin: Financials, end: date) -> tuple[Decimal, list[dict]]:
    parts = [
        ("Net income", fin.ttm("is.net_income", end)),
        ("Interest expense", fin.ttm("is.interest_expense", end)),
        ("Income tax expense", fin.ttm("is.income_tax_expense", end)),
        ("Depreciation and amortization", fin.ttm("is.depreciation_amortization", end)),
    ]
    total = sum((amount for _, amount in parts), ZERO)
    lines = [{"label": label, "amount": amount} for label, amount in parts]
    lines.append({"label": "EBITDA", "amount": total})
    return total, lines


def addback_amount(addback: dict, fin: Financials, end: date, ebitda: Decimal) -> Decimal:
    """Trailing-twelve-month add-back, limited by its cap. A null cap means no cap."""
    source = fin.ttm(addback["source_key"], end)
    cap = addback.get("cap")
    if cap is None:
        return source
    if cap["type"] == "amount":
        return min(source, D(cap["value"]))
    if cap["type"] == "pct_of":
        return min(source, D(cap["value"]) * ebitda)
    raise ValueError(f"unknown cap type {cap['type']}")


def adjusted_ebitda_ttm(fin: Financials, end: date, definitions: dict) -> tuple[Decimal, list[dict]]:
    ebitda, lines = ebitda_ttm(fin, end)
    total = ebitda
    for addback in definitions["ebitda"]["addbacks"]:
        amount = addback_amount(addback, fin, end, ebitda)
        total += amount
        lines.append({"label": f"Add-back: {addback['name'].replace('_', ' ')}", "amount": amount})
    lines.append({"label": "Adjusted EBITDA", "amount": total})
    return total, lines


def _earnings(base: str, fin: Financials, end: date, definitions: dict, extra: tuple[str, Decimal] | None):
    if base == "ebitda":
        total, lines = ebitda_ttm(fin, end)
    elif base == "adjusted_ebitda":
        total, lines = adjusted_ebitda_ttm(fin, end, definitions)
    else:
        raise ValueError(f"unknown earnings base {base}")
    if extra is not None:  # only ever used to reproduce a borrower's own, incorrect, calculation
        label, amount = extra
        total += amount
        lines.append({"label": label, "amount": amount})
        lines.append({"label": "EBITDA as calculated by the Borrower", "amount": total})
    return total, lines


def total_debt(fin: Financials, end: date) -> Decimal:
    return (
        fin.point("bs.revolver", end)
        + fin.point("bs.cpltd", end)
        + fin.point("bs.long_term_debt", end)
        + fin.point("bs.subordinated_debt", end)
    )


def tangible_net_worth(fin: Financials, end: date) -> Decimal:
    return fin.point("bs.total_equity", end) - fin.point("bs.intangibles", end)


# --------------------------------------------------------------------------- covenants


def covenant_value(
    covenant: dict,
    definitions: dict,
    fin: Financials,
    end: date,
    availability: Decimal | None = None,
    extra_ebitda: tuple[str, Decimal] | None = None,
) -> tuple[Decimal, list[dict]]:
    """Return the rounded covenant value and the calculation lines behind it."""
    archetype, params = covenant["archetype"], covenant["params"]
    lines: list[dict]
    if archetype == "coverage":
        base, lines = _earnings(params["numerator_base"], fin, end, definitions, extra_ebitda)
        numerator = base
        deduction_sources = {
            "unfinanced_capex": (
                "Unfinanced capital expenditures",
                lambda: fin.ttm("cf.capex", end) - fin.ttm("sup.financed_capex", end),
            ),
            "cash_taxes": ("Cash paid for income taxes", lambda: fin.ttm("sup.cash_taxes_paid", end)),
            "distributions": ("Distributions to owners", lambda: fin.ttm("cf.distributions", end)),
        }
        for name in params["deductions"]:
            label, amount_of = deduction_sources[name]
            amount = amount_of()
            numerator -= amount
            lines.append({"label": f"Less: {label}", "amount": amount})
        lines.append({"label": "Numerator", "amount": numerator})
        denominator_sources = {
            "cash_interest": ("Cash paid for interest", "sup.cash_interest_paid"),
            "interest_expense": ("Interest expense", "is.interest_expense"),
            "scheduled_principal": ("Scheduled principal payments on term debt", "sup.scheduled_principal"),
        }
        denominator = ZERO
        for name in params["denominator"]:
            label, key = denominator_sources[name]
            amount = fin.ttm(key, end)
            denominator += amount
            lines.append({"label": label, "amount": amount})
        lines.append({"label": "Denominator", "amount": denominator})
        raw = _divide(numerator, denominator)
    elif archetype == "leverage":
        debt = total_debt(fin, end)
        debt_label = "Total Debt"
        if params["debt"] == "senior_debt":
            debt -= fin.point("bs.subordinated_debt", end)
            debt_label = "Senior Debt"
        elif params["debt"] != "total_debt":
            raise ValueError(f"unknown debt measure {params['debt']}")
        earnings, earnings_lines = _earnings(params["ebitda"], fin, end, definitions, extra_ebitda)
        lines = [{"label": debt_label, "amount": debt}, *earnings_lines]
        raw = _divide(debt, earnings)
    elif archetype == "current_ratio":
        assets = fin.point("bs.total_current_assets", end)
        liabilities = fin.point("bs.total_current_liabilities", end)
        lines = [
            {"label": "Total current assets", "amount": assets},
            {"label": "Total current liabilities", "amount": liabilities},
        ]
        raw = _divide(assets, liabilities)
    elif archetype == "min_tangible_net_worth":
        equity, intangibles = fin.point("bs.total_equity", end), fin.point("bs.intangibles", end)
        raw = equity - intangibles
        lines = [
            {"label": "Total equity", "amount": equity},
            {"label": "Less: Goodwill and intangibles", "amount": intangibles},
            {"label": "Tangible Net Worth", "amount": raw},
        ]
    elif archetype == "min_liquidity":
        cash = fin.point("bs.cash", end)
        raw = cash
        lines = [{"label": "Cash and equivalents", "amount": cash}]
        if params["include_availability"]:
            if availability is None:
                raise MissingInput(f"availability at {end.isoformat()}")
            raw += availability
            lines.append({"label": "Unused availability under the Revolving Commitment", "amount": availability})
        lines.append({"label": "Liquidity", "amount": raw})
    elif archetype == "max_capex":
        raw = fin.ttm("cf.capex", end)
        lines = [{"label": "Capital Expenditures, trailing four quarters", "amount": raw}]
    elif archetype == "debt_to_tnw":
        liabilities = fin.point("bs.total_liabilities", end)
        tnw = tangible_net_worth(fin, end)
        lines = [
            {"label": "Total liabilities", "amount": liabilities},
            {"label": "Tangible Net Worth", "amount": tnw},
        ]
        raw = _divide(liabilities, tnw)
    else:
        raise ValueError(f"unknown archetype {archetype}")
    return round_half_up(raw, covenant["rounding"]["dp"]), lines


def _divide(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator <= 0:
        raise MissingInput("denominator is zero or negative")
    return numerator / denominator


def threshold_in_force(test: dict, end: date) -> Decimal:
    """The base threshold, replaced by the latest step whose date is on or before the period end."""
    threshold = D(test["threshold"])
    for step in sorted(test.get("steps", []), key=lambda s: s["from"]):
        if date.fromisoformat(step["from"]) <= end:
            threshold = D(step["value"])
    return threshold


def passes(value: Decimal, operator: str, threshold: Decimal) -> bool:
    return value >= threshold if operator == ">=" else value <= threshold


def headroom(value: Decimal, operator: str, threshold: Decimal) -> Decimal:
    """Distance from the threshold as a share of the threshold; negative when failing."""
    distance = value - threshold if operator == ">=" else threshold - value
    return round_half_up(distance / threshold, 4)


def terms_version_in_force(versions: list[dict], end: date) -> dict | None:
    """The approved or superseded version whose dates contain the period end. Proposed never governs."""
    for version in versions:
        if version["status"] not in ("approved", "superseded"):
            continue
        start = date.fromisoformat(version["effective_from"])
        finish = date.fromisoformat(version["effective_to"]) if version["effective_to"] else None
        if start <= end and (finish is None or end <= finish):
            return version
    return None


def classify(passed: bool, reported: dict | None, value: Decimal, unit: str) -> str:
    """Outcome of a covenant test against the borrower's certificate (spec section 8)."""
    if not passed:
        if reported is not None and reported["in_compliance"]:
            return "breach_reported_compliant"
        return "breach"
    if reported is None:
        return "compliant"
    tolerance = RATIO_TOLERANCE if unit == "ratio" else DOLLAR_TOLERANCE
    agrees = abs(D(reported["value"]) - value) <= tolerance and reported["in_compliance"]
    return "compliant" if agrees else "compliant_variance"


# --------------------------------------------------------------------------- borrowing base


def borrowing_base(
    terms: dict, ar_aging: list[dict], inventory: list[dict], outstanding: Decimal, letters_of_credit: Decimal
) -> dict[str, Decimal]:
    """Recalculate a borrowing base certificate line by line.

    Receivables, per customer and in this order: excluded categories (whole balance);
    invoices over the age limit; cross-aging (if the over-age share of the customer's
    balance exceeds the cross-aging percentage, the rest of the balance); contra
    (limited to what is left); concentration (what is left above the limit, where the
    limit is the concentration percentage of the total left across all customers).
    """
    ar = next(c for c in terms["components"] if c["collateral"] == "accounts_receivable")
    inv = next(c for c in terms["components"] if c["collateral"] == "inventory")
    rules = ar["eligibility"]
    if rules["max_age_days"] != 90:
        raise ValueError("the aging buckets support a 90-day age limit only")
    excluded_categories = [c for c in rules["exclude"] if c != "contra"]
    out = dict.fromkeys(
        ("ineligible_excluded", "ineligible_over_age", "ineligible_cross_aging", "ineligible_contra"), ZERO
    )
    gross = ZERO
    remaining: list[Decimal] = []
    for customer in ar_aging:
        balance = sum(customer["buckets"].values(), ZERO)
        gross += balance
        if customer["category"] in excluded_categories:
            out["ineligible_excluded"] += balance
            continue
        over_age = customer["buckets"]["over_90"]
        left = balance - over_age
        out["ineligible_over_age"] += over_age
        if over_age > D(rules["cross_aging_pct"]) * balance:
            out["ineligible_cross_aging"] += left
            left = ZERO
        if "contra" in rules["exclude"]:
            contra = min(customer["contra"], left)
            out["ineligible_contra"] += contra
            left -= contra
        remaining.append(left)
    limit = D(rules["concentration_limit_pct"]) * sum(remaining, ZERO)
    out["ineligible_concentration"] = sum((max(ZERO, left - limit) for left in remaining), ZERO)
    out["gross_ar"] = gross
    out["total_ineligible_ar"] = (
        out["ineligible_excluded"]
        + out["ineligible_over_age"]
        + out["ineligible_cross_aging"]
        + out["ineligible_contra"]
        + out["ineligible_concentration"]
    )
    out["eligible_ar"] = gross - out["total_ineligible_ar"]
    out["ar_availability"] = round_half_up(out["eligible_ar"] * D(ar["advance_rate"]), 0)

    out["gross_inventory"] = sum((item["amount"] for item in inventory), ZERO)
    out["ineligible_inventory"] = sum(
        (item["amount"] for item in inventory if item["category"] in inv["eligibility"]["exclude"]), ZERO
    )
    out["eligible_inventory"] = out["gross_inventory"] - out["ineligible_inventory"]
    uncapped = round_half_up(out["eligible_inventory"] * D(inv["advance_rate"]), 0)
    out["inventory_availability_before_sublimit"] = uncapped
    out["inventory_availability"] = min(uncapped, D(inv["sublimit"])) if inv.get("sublimit") else uncapped
    out["reserves"] = sum((D(r["amount"]) for r in terms["reserves"]), ZERO)
    out["borrowing_base"] = out["ar_availability"] + out["inventory_availability"] - out["reserves"]
    out["commitment"] = D(terms["commitment"])
    out["lesser_of_base_and_commitment"] = min(out["borrowing_base"], out["commitment"])
    out["outstanding"] = outstanding
    out["letters_of_credit"] = letters_of_credit
    out["availability"] = out["lesser_of_base_and_commitment"] - outstanding - letters_of_credit
    return {line: round_half_up(amount, 0) for line, amount in out.items()}


BB_LINES = (
    "gross_ar",
    "ineligible_excluded",
    "ineligible_over_age",
    "ineligible_cross_aging",
    "ineligible_contra",
    "ineligible_concentration",
    "total_ineligible_ar",
    "eligible_ar",
    "ar_availability",
    "gross_inventory",
    "ineligible_inventory",
    "eligible_inventory",
    "inventory_availability_before_sublimit",
    "inventory_availability",
    "reserves",
    "borrowing_base",
    "commitment",
    "lesser_of_base_and_commitment",
    "outstanding",
    "letters_of_credit",
    "availability",
)


def reconcile_borrowing_base(calculated: dict[str, Decimal], certificate: dict[str, Decimal]) -> list[dict]:
    """Lines where the borrower's certificate differs from the recalculation."""
    return [
        {"line": line, "calculated": calculated[line], "certificate": certificate[line]}
        for line in BB_LINES
        if calculated[line] != certificate[line]
    ]


# --------------------------------------------------------------------------- signals


def _year_ago(end: date) -> date:
    return date(end.year - 1, end.month, end.day)


def _measure(fn):
    """Run a measurement; an input that is not available leaves the metric unmeasured (None)."""
    try:
        return fn()
    except MissingInput:
        return None


def compute_signals(
    end: date,
    fin: Financials,
    tests_by_period: dict[date, list[dict]],
    test_periods: list[date],
    line: dict | None,
    bb_result: dict | None,
    days_late: int | None,
    past_due_days: int,
) -> list[dict]:
    """Signals for one period under rule set `signals-1`.

    Changes are measured against the same period one year earlier. A rule whose
    inputs are not all available in the borrower's periods is unmeasured and
    produces no signal. `line` is {"outstanding", "commitment"} from the system
    of record at the period end; `bb_result` is the recalculated borrowing base.
    """
    signals: list[dict] = []
    prior = _year_ago(end)

    def add(rule: str, value: Decimal, **detail) -> None:
        signals.append(
            {
                "rule": rule,
                "period_end": end,
                "severity": SIGNAL_SEVERITY[rule],
                "value": value,
                "trigger": SIGNAL_TRIGGER.get(rule),
                "detail": detail,
            }
        )

    # Covenant headroom below 10 percent, and headroom falling two periods running.
    index = test_periods.index(end)
    for test in tests_by_period.get(end, []):
        if test["headroom"] is None:
            continue
        if test["headroom"] < D("0.10"):
            add("covenant_headroom_low", test["headroom"], covenant_id=test["covenant_id"])
        if index >= 2:
            earlier = []
            for back in (test_periods[index - 2], test_periods[index - 1]):
                match = [t for t in tests_by_period.get(back, []) if t["covenant_id"] == test["covenant_id"]]
                earlier.append(match[0]["headroom"] if match else None)
            if None not in earlier and test["headroom"] < earlier[1] < earlier[0]:
                add(
                    "covenant_headroom_falling",
                    test["headroom"],
                    covenant_id=test["covenant_id"],
                    two_periods_ago=earlier[0],
                    prior_period=earlier[1],
                )

    def revenue_change() -> Decimal:
        now, before = fin.ttm("is.revenue", end), fin.ttm("is.revenue", prior)
        return (now - before) / before

    def ebitda_margin(at: date) -> Decimal:
        return ebitda_ttm(fin, at)[0] / fin.ttm("is.revenue", at)

    def dso(at: date) -> Decimal:
        return fin.point("bs.accounts_receivable", at) / fin.ttm("is.revenue", at) * 365

    def dpo(at: date) -> Decimal:
        return fin.point("bs.accounts_payable", at) / fin.ttm("is.cogs", at) * 365

    def leverage(at: date) -> Decimal:
        return _divide(total_debt(fin, at), ebitda_ttm(fin, at)[0])

    def cash_change() -> Decimal:
        now, before = fin.point("bs.cash", end), fin.point("bs.cash", prior)
        return (now - before) / before

    change = _measure(revenue_change)
    if change is not None and change < D("-0.10"):
        add("revenue_ttm_decline", round_half_up(change, 4))
    change = _measure(lambda: ebitda_margin(end) - ebitda_margin(prior))
    if change is not None and change < D("-0.03"):
        add("ebitda_margin_decline", round_half_up(change, 4))
    change = _measure(lambda: dso(end) - dso(prior))
    if change is not None and change > 10:
        add("dso_increase", round_half_up(change, 1))
    change = _measure(lambda: dpo(end) - dpo(prior))
    if change is not None and change > 15:
        add("dpo_increase", round_half_up(change, 1))
    change = _measure(lambda: leverage(end) - leverage(prior))
    if change is not None and change > D("0.5"):
        add("leverage_increase", round_half_up(change, 2))
    net_income = _measure(lambda: fin.ttm("is.net_income", end))
    if net_income is not None and net_income < 0:
        add("net_loss_ttm", net_income)
    change = _measure(cash_change)
    if change is not None and change < D("-0.30"):
        add("cash_decline", round_half_up(change, 4))
    if line is not None and line["commitment"] > 0:
        usage = line["outstanding"] / line["commitment"]
        if usage > D("0.90"):
            add("line_usage_high", round_half_up(usage, 4))
    if bb_result is not None:
        share = bb_result["availability"] / bb_result["commitment"]
        if share < D("0.10"):
            add("availability_low", round_half_up(share, 4))
    if days_late is not None and days_late > 15:
        add("reporting_late", D(days_late))
    if past_due_days > 10:
        add("payment_past_due", D(past_due_days))
    return signals
