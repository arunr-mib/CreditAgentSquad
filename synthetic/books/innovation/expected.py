"""Expected results for an innovation client, in plain arithmetic.

This module never imports from backend/app. The engine has to reach the same numbers by its own route; if it does not,
investigate, and never patch either side to match.
"""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from synthetic.books.innovation.model import JUNE_2026, LAST, MONTHS, Month, N
from synthetic.books.innovation.roster import ClientSpec

D = Decimal
FIRST_TEST = 7  # August 2025: the first month whose trailing three months all lie in the published periods
PLAN_FIRST = 4  # the approved plan covers May 2025 to October 2026
SIGNAL_SEVERITY = {
    "covenant_headroom_low": "medium", "covenant_headroom_falling": "low", "runway_below_watch": "medium",
    "runway_falling": "medium", "burn_rising": "medium", "revenue_below_plan": "medium", "reporting_late": "high",
}  # fmt: skip
SIGNAL_TRIGGER = {
    "covenant_headroom_low": "0.10", "runway_below_watch": "12", "burn_rising": "0.20", "revenue_below_plan": "1.00",
    "reporting_late": "15",
}  # fmt: skip
EXCEPTION_SEVERITY = {
    "covenant.reported_mismatch": "critical", "covenant.breach": "high", "signal.high": "high",
    "intake.missing_document": "medium", "funding_slipped": "high", "intake.unclassified": "medium",
    "spread.value_unverified": "medium", "cash.statement_mismatch": "high",
}  # fmt: skip
# A certificate figure is either exact or far from the engine's own tolerance (usd 1, months 0, pct 0.0005), so the
# two sides cannot disagree about "agrees with the certificate".
TOLERANCE = {"usd": D(1000), "months": D("0.05"), "pct": D("0.001")}
DUE_DAYS = {"bank_statement": 7, "mrr_report": 15, "monthly_financials": 30, "compliance_certificate": 30}
COVENANTS = (
    ("min_unrestricted_cash", "Minimum Unrestricted Cash", "usd"),
    ("min_runway_months", "Minimum Runway", "months"),
    ("revenue_vs_plan", "Revenue to Plan", "pct"),
)


def q(value: Decimal, dp: int) -> Decimal:
    return value.quantize(D(1).scaleb(-dp), rounding=ROUND_HALF_UP)


def thousands(value: Decimal) -> int:
    return int((value / 1000).quantize(D(1), rounding=ROUND_HALF_UP)) * 1000


class Series:
    """Discrete monthly figures for one client, indexed like MONTHS."""

    def __init__(self, months: list[Month]):
        self.months = months

    def flow3(self, key: str, i: int) -> int:
        return sum(self.months[j].flows[key] for j in range(i - 2, i + 1))

    def net_burn3(self, i: int) -> int:
        """Capex plus capitalised software spend, less operating cash flow, over the three months ending at i."""
        return (self.flow3("cf.vc_capex", i) + self.flow3("cf.capitalised_software_spend", i)
                - self.flow3("cf.vc_operating_cash_flow", i))  # fmt: skip

    def avg_burn(self, i: int) -> Decimal:
        return D(self.net_burn3(i)) / 3

    def cash(self, i: int) -> int:
        return self.months[i].balances["bs.cash_unrestricted"]

    def rml(self, i: int) -> Decimal | None:
        """Unrestricted cash over average monthly net burn; None (not meaningful) when the burn is zero or negative."""
        burn = self.avg_burn(i)
        return None if burn <= 0 else D(self.cash(i)) / burn

    def flow12(self, key: str, i: int) -> int:
        return sum(self.months[j].flows[key] for j in range(i - 11, i + 1))

    def dscr(self, i: int) -> Decimal | None:
        """Trailing-twelve-months DSCR, the generator's own copy of the vc-1 definition: (operating loss line plus
        depreciation and amortisation) over (interest plus scheduled principal). None when there are fewer than
        twelve months of history or no debt service."""
        if i < 11:
            return None
        service = self.flow12("is.vc_interest", i) + self.flow12("sup.scheduled_principal", i)
        if service <= 0:
            return None
        ebitda = self.flow12("is.vc_operating_loss", i) + self.flow12("is.vc_depreciation_amortization", i)
        return D(ebitda) / D(service)

    def revenue(self, i: int) -> int:
        return self.months[i].flows["is.subscription_revenue"] + self.months[i].flows["is.services_revenue"]

    def revenue3(self, i: int) -> int:
        return sum(self.revenue(j) for j in range(i - 2, i + 1))


def build_plan(spec: ClientSpec, series: Series) -> dict[date, int]:
    """Approved plan figures (monthly revenue, May 2025 to October 2026). Clean clients beat plan by about 5 percent;
    Corvane's plan runs away from its revenue after June 2026."""
    plan: dict[date, int] = {}
    for i in range(PLAN_FIRST, N):
        if spec.scenario == "plan_miss" and i >= JUNE_2026:
            value = D(series.revenue(JUNE_2026)) * D(spec.extra["plan_growth"]) ** (i - JUNE_2026)
        else:
            value = D(series.revenue(i)) * D("0.95")
        plan[MONTHS[i]] = thousands(value)
    return plan


def plan_ratio(series: Series, plan: dict[date, int], i: int) -> Decimal:
    planned = sum(plan[MONTHS[j]] for j in range(i - 2, i + 1))
    return D(series.revenue3(i)) / D(planned)


def cert_months(spec: ClientSpec) -> set[int]:
    """Months with a certificate on file: the last three, except Lumora's October (not yet delivered)."""
    months = {LAST - 2, LAST - 1, LAST}
    if spec.scenario == "late_package":
        months.discard(LAST)
    return months


def cert_cash(spec: ClientSpec, series: Series, i: int) -> int:
    """The cash the borrower's certificate shows. Dataflake counts its pledged account; Tidewell counts its new escrow
    account. Both are wrong in October only."""
    cash = series.cash(i)
    if i == LAST and spec.scenario == "pledged_cash":
        cash += spec.pledged
    if i == LAST and spec.scenario == "restricted_account":
        cash += spec.extra["newly_restricted"]
    return cash


def cert_entry(spec: ClientSpec, series: Series, plan: dict[date, int], i: int, covenant_id: str):
    """What the certificate reports for one covenant at month i: (value, in_compliance). A cash-flow-positive client
    reports no runway figure."""
    if covenant_id == "min_unrestricted_cash":
        cash = D(cert_cash(spec, series, i))
        return cash, cash >= spec.min_cash
    if covenant_id == "min_runway_months":
        burn = series.avg_burn(i)
        if burn <= 0:
            return None, True
        value = q(D(cert_cash(spec, series, i)) / burn, 1)
        return value, value >= D(spec.min_rml)
    ratio = q(plan_ratio(series, plan, i), 4)
    return ratio, ratio >= D(spec.plan_floor)


def classify(
    passed: bool,
    value: Decimal | None,
    reported: bool,
    rep_value: Decimal | None,
    rep_flag: bool | None,
    unit: str,
) -> str:
    """Outcome of a covenant test against the borrower's certificate (spec section 8 of the design)."""
    if not passed:
        return "breach_reported_compliant" if reported and rep_flag else "breach"
    if not reported:
        return "compliant"
    if value is None:  # not meaningful: the certificate's own figure is ignored; its flag is still compared
        return "compliant" if rep_flag else "compliant_variance"
    agrees = rep_value is not None and abs(rep_value - value) <= TOLERANCE[unit] and bool(rep_flag)
    return "compliant" if agrees else "compliant_variance"


def covenant_rows(
    spec: ClientSpec, series: Series, plan: dict[date, int], version_id: str, facility_id: str
) -> list[dict]:
    """One row per covenant per month from August 2025."""
    rows: list[dict] = []
    certified = cert_months(spec)
    for i in range(FIRST_TEST, N):
        for covenant_id, name, unit in COVENANTS:
            threshold = {"usd": D(spec.min_cash), "months": D(spec.min_rml), "pct": D(spec.plan_floor)}[unit]
            note = None
            if covenant_id == "min_unrestricted_cash":
                value: Decimal | None = D(series.cash(i))
            elif covenant_id == "min_runway_months":
                raw = series.rml(i)
                value = None if raw is None else q(raw, 1)
                note = "not_meaningful_cash_flow_positive" if raw is None else None
            else:
                value = q(plan_ratio(series, plan, i), 4)
            passed = True if value is None else value >= threshold
            headroom = None if value is None else q((value - threshold) / abs(threshold), 4)
            reported = i in certified
            rep_value, rep_flag = cert_entry(spec, series, plan, i, covenant_id) if reported else (None, None)
            rows.append({
                "period_end": MONTHS[i], "covenant_id": covenant_id, "covenant_name": name, "archetype": covenant_id,
                "facility_id": facility_id, "terms_version_id": version_id, "terms_version": 1, "unit": unit,
                "operator": ">=", "threshold": threshold, "value": value, "pass": passed, "headroom": headroom,
                "note": note, "reported_value": rep_value, "reported_threshold": threshold if reported else None,
                "reported_in_compliance": rep_flag,
                "outcome": classify(passed, value, reported, rep_value, rep_flag, unit),
            })  # fmt: skip
    return rows


def compute_signals(
    series: Series, plan: dict[date, int], rows: list[dict], i: int, days_late: list[tuple[str, int]]
) -> list[dict]:
    """Signals for month i under rule set `signals-1` (the startup rules of spec section 7)."""
    end = MONTHS[i]
    out: list[dict] = []

    def add(rule: str, value, severity: str | None = None, **detail) -> None:
        out.append({"rule": rule, "period_end": end, "severity": severity or SIGNAL_SEVERITY[rule], "value": value,
                    "trigger": SIGNAL_TRIGGER.get(rule), "detail": detail})  # fmt: skip

    headroom: dict[str, dict[int, Decimal | None]] = {}
    for row in rows:
        headroom.setdefault(row["covenant_id"], {})[MONTHS.index(row["period_end"])] = row["headroom"]
    for covenant_id, per_month in sorted(headroom.items()):
        now = per_month.get(i)
        if now is None:
            continue
        if now < D("0.10"):
            add("covenant_headroom_low", now, covenant_id=covenant_id)
        window = [per_month.get(j) for j in (i - 2, i - 1, i)]
        if None not in window and window[2] < window[1] < window[0]:
            add("covenant_headroom_falling", now, covenant_id=covenant_id)
    runway = series.rml(i)
    if runway is not None and runway < 12:
        add("runway_below_watch", q(runway, 2), "high" if runway < 9 else "medium")
    points = [series.rml(j) for j in range(i - 3, i + 1)]
    # four meaningful points, and more than one month of runway lost in each of the three steps
    if None not in points and all(
        earlier - later > 1 for earlier, later in zip(points, points[1:], strict=False)
    ):
        add("runway_falling", q(runway, 2))
    prior = series.avg_burn(i - 3)
    if prior > 0:
        change = q((series.avg_burn(i) - prior) / prior, 4)
        if change > D("0.20"):
            add("burn_rising", change)
    ratio = q(plan_ratio(series, plan, i), 4)
    if ratio < D("1.00"):
        add("revenue_below_plan", ratio)
    for requirement, late in days_late:
        if late > 15:
            add("reporting_late", D(late), requirement=requirement)
    return out
