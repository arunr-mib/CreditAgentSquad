"""Decimal helpers for the calculation core of Credit Agent Squad.

Every number in `app.calc` is a `decimal.Decimal`. Floats are refused at the
public boundary, and rounding happens once, at the end of a formula, half-up.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Context, Decimal, InvalidOperation

# All arithmetic in the package runs in this context so results do not depend
# on whatever the calling thread's decimal context happens to be.
CALC_CONTEXT = Context(prec=50, rounding=ROUND_HALF_UP)

# Money here is whole dollars and ratios are small; anything beyond 10^30 (or finer than
# 10^-30) is a data error, and refusing it keeps every operation exact within the context.
MAX_MAGNITUDE = 30

ZERO = Decimal("0")
ONE = Decimal("1")


class FloatNotAllowed(TypeError):
    """A float reached the calculation boundary."""


def is_decimal(value: object) -> bool:
    """True only for a finite `Decimal` (not int, not float, not NaN)."""
    return isinstance(value, Decimal) and value.is_finite()


def to_decimal(value: object) -> Decimal:
    """Parse a str, int or Decimal into a finite Decimal.

    Raises `FloatNotAllowed` for floats, `TypeError` for other types (including
    bool and None), and `ValueError` for text that is not a plain finite number.
    """
    if isinstance(value, float):
        raise FloatNotAllowed(f"float {value!r} is not allowed; pass a string or Decimal")
    if isinstance(value, bool) or value is None:
        raise TypeError(f"cannot convert {value!r} to Decimal")
    if isinstance(value, Decimal):
        result = value
    elif isinstance(value, int):
        result = Decimal(value)
    elif isinstance(value, str):
        text = value.strip()
        if not text or "," in text or "_" in text:
            raise ValueError(f"not a decimal number: {value!r}")
        try:
            result = Decimal(text)
        except InvalidOperation as exc:
            raise ValueError(f"not a decimal number: {value!r}") from exc
    else:
        raise TypeError(f"cannot convert {type(value).__name__} to Decimal")
    if not result.is_finite():
        raise ValueError(f"not a finite decimal number: {value!r}")
    exponent = result.as_tuple().exponent
    if result and (abs(result.adjusted()) > MAX_MAGNITUDE or abs(int(exponent)) > MAX_MAGNITUDE):
        raise ValueError(f"decimal number out of range: {value!r}")
    return result


def round_half_up(value: Decimal, dp: int) -> Decimal:
    """Round to `dp` decimal places, halves away from zero."""
    if isinstance(value, float):
        raise FloatNotAllowed("float is not allowed; pass a Decimal")
    if not isinstance(value, Decimal):
        raise TypeError("round_half_up needs a Decimal")
    if isinstance(dp, bool) or not isinstance(dp, int):
        raise TypeError("dp must be an int")
    if dp < 0:
        raise ValueError("dp must be zero or more")
    return value.quantize(Decimal(1).scaleb(-dp), rounding=ROUND_HALF_UP, context=CALC_CONTEXT)
