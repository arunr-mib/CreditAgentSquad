"""The product's identity for Office files, and how a fact is printed.

Ink and warm neutrals; one typeface family (Calibri stands in for Inter, which Office does not
ship); red only for a breach, green only for a verified pass, amber for attention.
"""
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.guardrails.narrative import FactView, format_fact

FONT = "Calibri"
LENDER = "Bank of Stoic"
SYNTHETIC = "SYNTHETIC - FOR DEMONSTRATION"
DRAFT_LABEL = "Draft, not yet approved"
WITHHELD = "[figure withheld: no source]"

INK_900, INK_700, INK_500, INK_400 = "1B1A17", "45423B", "66625A", "8C877C"
CANVAS, SURFACE, SUNKEN = "F6F4EE", "FFFEFC", "EFECE4"
HAIRLINE, HAIRLINE_STRONG = "E3DFD5", "CFC9BC"
RED, RED_BG = "AE2018", "FBEDEB"
AMBER, AMBER_BG = "855400", "FAF1DC"
GREEN, GREEN_BG = "1D6B41", "E8F3EC"
IRIS = "5A3FA6"

OUTCOME_WORDS = {
    "compliant": ("Compliant", GREEN), "compliant_variance": ("Compliant, differs from certificate", AMBER),
    "breach": ("Breach", RED), "breach_reported_compliant": ("Breach, certified as compliant", RED),
    "cannot_test": ("Cannot test", AMBER),
}
BB_OUTCOME_WORDS = {
    "agrees": ("Agrees with certificate", GREEN), "mismatch": ("Differs from certificate", AMBER),
    "over_advance": ("Over-advanced", RED), "cannot_compute": ("Could not be recalculated", AMBER),
}
SEVERITY_COLOURS = {"critical": RED, "high": AMBER, "medium": AMBER, "low": INK_500}
OPERATOR_WORDS = {">=": "at least", "<=": "at most", ">": "above", "<": "below"}

# Excel number formats, by unit
XL_FORMATS = {
    "usd": '#,##0;(#,##0);"-"', "ratio": '0.00"x"', "pct": "0.0%", "days": "0.0", "count": "0",
}


def _q(value: Decimal, places: str) -> Decimal:
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


def display(record: dict[str, Any], fmt: str | None = None) -> str:
    """Print a frozen fact (or derived figure). Rounding is half-up and for display only."""
    value, unit = Decimal(record["value"]), record.get("unit", "usd")
    if fmt == "pct2":
        return f"{_q(value * Decimal(100), '0.01')}%"
    if fmt == "plain_usd":  # table cells under a dollar heading
        body = f"{_q(abs(value), '1'):,}"
        return f"({body})" if value < 0 else body
    if fmt == "days1":
        return f"{_q(value, '0.1')}"
    if unit == "count" and fmt is None:
        return f"{_q(value, '1'):,}"
    return format_fact(FactView(record["id"], value, unit), fmt)


def table_format(unit: str) -> str | None:
    """The compact format used inside tables for a unit."""
    return {"usd": "plain_usd", "days": "days1"}.get(unit)
