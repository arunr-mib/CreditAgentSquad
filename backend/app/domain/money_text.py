"""Money as people read it in a title or a question: "$15,000,000", never "15,000,000.00"."""
from decimal import ROUND_HALF_UP, Decimal


def dollars(value: Decimal | int | str) -> str:
    """Whole dollars with thousands separators; cents only when the amount has them. Negative in parentheses."""
    amount = Decimal(value)
    whole = abs(amount).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    cents = abs(amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    body = f"{cents:,}" if cents != whole else f"{whole:,}"
    return f"(${body})" if amount < 0 else f"${body}"
