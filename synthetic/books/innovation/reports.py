"""What the client reports and sends: certificates, bank account balances, the MRR bridge, the software roll."""

from __future__ import annotations

from decimal import Decimal

from synthetic.books.innovation.expected import COVENANTS, Series, cert_cash, cert_entry, cert_months, q
from synthetic.books.innovation.model import LAST, MONTHS, Month, rnd
from synthetic.books.innovation.roster import ClientSpec
from synthetic.books.innovation.terms import DSCR_EFFECTIVE, DSCR_MIN, FERROGATE

D = Decimal


def build_certificates(spec: ClientSpec, series: Series, plan: dict) -> list[dict]:
    """Monthly compliance certificates for the last three months, as the client delivered them."""
    certificates = []
    for i in sorted(cert_months(spec)):
        threshold = {"usd": D(spec.min_cash), "months": D(spec.min_rml), "pct": D(spec.plan_floor)}
        reported = {}
        for covenant_id, _, unit in COVENANTS:
            value, flag = cert_entry(spec, series, plan, i, covenant_id)
            cash = [{"label": "Cash in operating accounts", "amount": series.cash(i)}]
            if i == LAST and spec.scenario == "pledged_cash":
                cash.append({"label": "Cash held in the pledged collateral account", "amount": spec.pledged})
            if i == LAST and spec.scenario == "restricted_account":
                cash.append({"label": "Cash in the escrow collateral account opened October 14, 2026",
                             "amount": spec.extra["newly_restricted"]})  # fmt: skip
            if covenant_id == "min_unrestricted_cash":
                lines = [*cash, {"label": "Unrestricted Cash", "amount": cert_cash(spec, series, i)}]
            elif covenant_id == "min_runway_months":
                lines = [{"label": "Unrestricted Cash (as above)", "amount": cert_cash(spec, series, i)},
                         {"label": "Net Burn for the three months ended", "amount": series.net_burn3(i)},
                         {"label": "Average monthly Net Burn", "amount": q(series.avg_burn(i), 0)}]  # fmt: skip
            else:
                planned = sum(plan[MONTHS[j]] for j in range(i - 2, i + 1))
                lines = [{"label": "Revenue for the three months ended", "amount": series.revenue3(i)},
                         {"label": "Approved Plan for the same three months", "amount": planned}]  # fmt: skip
            reported[covenant_id] = {"value": value, "threshold": threshold[unit], "in_compliance": flag,
                                     "unit": unit, "calculation": lines}  # fmt: skip
        if spec.id == FERROGATE and MONTHS[i] >= DSCR_EFFECTIVE:
            value = q(series.dscr(i), 2)
            ebitda = series.flow12("is.vc_operating_loss", i) + series.flow12(
                "is.vc_depreciation_amortization", i
            )
            service = series.flow12("is.vc_interest", i) + series.flow12("sup.scheduled_principal", i)
            reported["dscr"] = {
                "value": value, "threshold": D(DSCR_MIN), "in_compliance": value >= D(DSCR_MIN), "unit": "ratio",
                "calculation": [{"label": "EBITDA for the twelve months ended", "amount": ebitda},
                                {"label": "Interest and scheduled principal for the twelve months ended",
                                 "amount": service}],
            }  # fmt: skip
        certificates.append(
            {"period_end": MONTHS[i], "scale": 1, "signed_by": spec.cfo, "reported": reported}
        )
    return certificates


def format_actual(unit: str, value: Decimal | None) -> str:
    if value is None:
        return "Not meaningful (cash-flow positive)"
    if unit == "usd":
        return f"${int(value):,}"
    if unit == "months":
        return f"{value:.1f} months"
    if unit == "ratio":
        return f"{value:.2f} to 1.00"
    return f"{value * 100:.2f}%"


def format_required(unit: str, threshold: Decimal) -> str:
    if unit == "ratio":
        return f"Not less than {threshold:.2f} to 1.00"
    if unit == "usd":
        return f"Not less than ${int(threshold):,}"
    if unit == "months":
        return f"Not less than {threshold:.1f} months"
    return f"Not less than {threshold * 100:.2f}% of plan"


def bank_accounts(spec: ClientSpec, months: list[Month], i: int) -> list[dict]:
    """Account balances for month i. Operating balances sum to unrestricted cash and the pledged accounts to
    restricted cash, so the statement ties to the balance sheet exactly."""

    def split(cash: int) -> list[int]:
        operating, payroll = rnd(D("0.70") * cash), rnd(D("0.12") * cash)
        return [operating, payroll, cash - operating - payroll]

    now, before = months[i], months[i - 1]
    closing, opening = (
        split(now.balances["bs.cash_unrestricted"]),
        split(before.balances["bs.cash_unrestricted"]),
    )
    inflow = now.flows["is.subscription_revenue"] + now.flows["is.services_revenue"]
    credits = [rnd(D("1.02") * inflow) + now.flows["cf.equity_raised"] + now.flows["cf.debt_raised"]]
    credits += [abs(closing[k] - opening[k]) + rnd(D("0.25") * opening[k]) for k in (1, 2)]
    accounts = []
    for k, (name, tail) in enumerate((("Operating account", "4417"), ("Payroll account", "4425"),
                                      ("Treasury money market account", "4433"))):  # fmt: skip
        accounts.append({"name": name, "tail": tail, "restricted": False, "opening": opening[k],
                         "credits": credits[k], "debits": credits[k] - (closing[k] - opening[k]),
                         "closing": closing[k]})  # fmt: skip
    first = spec.extra.get("restricted_before", spec.pledged)
    accounts.append({"name": "Collateral account", "tail": "9001", "restricted": True, "opening": first,
                     "credits": 0, "debits": 0, "closing": first})  # fmt: skip
    if spec.scenario == "restricted_account" and i == LAST:
        accounts.append({"name": "Escrow collateral account", "tail": "9002", "restricted": True, "opening": 0,
                         "credits": spec.extra["newly_restricted"], "debits": 0,
                         "closing": spec.extra["newly_restricted"]})  # fmt: skip
    return accounts


def bank_notes(spec: ClientSpec, i: int) -> list[str]:
    note = spec.extra.get("pledged_note", "pledged as collateral under the venture loan agreement")
    notes = [
        f"The collateral account is {note}. Balances in restricted accounts are not available for withdrawal."
    ]
    if spec.scenario == "restricted_account" and i == LAST:
        notes.append("The account ending 9002 was opened on October 14, 2026 as a cash collateral account under an "
                     "escrow arrangement. It is restricted.")  # fmt: skip
    return notes


def mrr_bridge(months: list[Month], i: int) -> dict:
    """The MRR movement for month i: opening, new, expansion, contraction, churn, closing."""
    opening, closing = months[i - 1].balances["saas.mrr"], months[i].balances["saas.mrr"]
    expansion, contraction, churn = (
        rnd(D("0.012") * opening),
        rnd(D("0.004") * opening),
        rnd(D("0.008") * opening),
    )
    residual = closing - opening - (expansion - contraction - churn)
    new = max(residual, 0)
    churn += max(-residual, 0)
    return {"opening": opening, "new": new, "expansion": expansion, "contraction": contraction, "churn": churn,
            "mrr": closing, "arr": months[i].balances["saas.arr"], "net_new_arr": months[i].memo["saas.net_new_arr"],
            "customers": months[i].balances["saas.customers"], "nrr": months[i].memo["saas.nrr_percent"],
            "trend": [(MONTHS[j].strftime("%B %Y"), months[j].balances["saas.mrr"], months[j].balances["saas.customers"])
                      for j in range(i - 5, i + 1)]}  # fmt: skip


def software_roll(months: list[Month], i: int) -> dict:
    return {"opening": months[i - 1].balances["bs.capitalised_software"],
            "additions": months[i].flows["cf.capitalised_software_spend"],
            "amortisation": months[i].memo["software.amortisation"],
            "closing": months[i].balances["bs.capitalised_software"]}  # fmt: skip


def misread_runway(series: Series, i: int) -> Decimal | None:
    """Runway if the capitalised software balance were read as the month's spend (the Stripple trap)."""
    wrong = (series.flow3("cf.vc_capex", i) + series.months[i].balances["bs.capitalised_software"]
             - series.flow3("cf.vc_operating_cash_flow", i))  # fmt: skip
    burn = D(wrong) / 3
    return None if burn <= 0 else D(series.cash(i)) / burn
