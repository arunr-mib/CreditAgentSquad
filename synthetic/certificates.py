"""The borrower's own compliance certificates.

A certificate is what the borrower reported, which is not always what is correct.
Clean certificates repeat the correct calculation. Scenario borrowers distort the
current-period certificate in the specific way their scenario describes.
"""

from __future__ import annotations

from datetime import date
from decimal import ROUND_CEILING, Decimal

from synthetic import expected
from synthetic.scenarios import CURRENT_PERIOD, UNAPPROVED_AMENDMENT_CAP, BorrowerSpec

D = Decimal
COST_SAVINGS_LABEL = "Pro forma cost savings from plant consolidation"


def _uncapped(definitions: dict) -> dict:
    return {"ebitda": {**definitions["ebitda"], "addbacks": [{**a, "cap": None} for a in definitions["ebitda"]["addbacks"]]}}


def _recapped(definitions: dict, value: str) -> dict:
    cap = {"type": "amount", "value": value}
    return {"ebitda": {**definitions["ebitda"], "addbacks": [{**a, "cap": cap} for a in definitions["ebitda"]["addbacks"]]}}


def build_certificates(
    spec: BorrowerSpec,
    versions: list[dict],
    fin: expected.Financials,
    test_periods: list[date],
    availability_at,
) -> list[dict]:
    certificates = []
    for end in test_periods:
        distort = spec.scenario if end == CURRENT_PERIOD else "clean"
        if distort == "late_reporting":
            continue  # nothing was delivered for the current quarter
        version = expected.terms_version_in_force(versions, end)
        terms = version["terms"]
        definitions = terms["definitions"]
        if distort == "addback_over_cap":
            definitions = _uncapped(definitions)
        elif distort == "unapproved_amendment":
            definitions = _recapped(definitions, UNAPPROVED_AMENDMENT_CAP)
        reported = {}
        for covenant in terms["covenants"]:
            test = covenant["test"]
            threshold = expected.threshold_in_force(test, end)
            extra = None
            if distort == "hidden_breach" and covenant["archetype"] == "leverage":
                # The borrower adds just enough unpermitted "cost savings" to show a comfortable pass.
                correct, lines = expected.covenant_value(covenant, definitions, fin, end, availability_at(end))
                debt, earnings = lines[0]["amount"], lines[-1]["amount"]
                needed = debt / (threshold - D("0.08")) - earnings
                unit = D(100_000) if spec.scale == 1000 else D(25_000)
                extra = (COST_SAVINGS_LABEL, (needed / unit).to_integral_value(ROUND_CEILING) * unit)
            if distort == "step_up" and test["steps"]:
                threshold = D(test["threshold"])  # the borrower still tests against the superseded level
            value, lines = expected.covenant_value(covenant, definitions, fin, end, availability_at(end), extra)
            reported[covenant["id"]] = {
                "value": value,
                "threshold": threshold,
                "in_compliance": expected.passes(value, test["operator"], threshold),
                "unit": test["unit"],
                "calculation": lines,
            }
        certificates.append(
            {
                "period_end": end,
                "scale": 1 if spec.scenario == "scale_trap" else spec.scale,
                "signed_by": spec.cfo,
                "reported": reported,
            }
        )
    return certificates
