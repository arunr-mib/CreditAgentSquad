from decimal import Decimal

import pytest
from app.calc.decimal_utils import FloatNotAllowed, is_decimal, round_half_up, to_decimal


def test_parses_str_int_and_decimal():
    assert to_decimal("1.25") == Decimal("1.25")
    assert to_decimal(" 1250000 ") == Decimal("1250000")
    assert to_decimal(7) == Decimal("7")
    assert to_decimal(Decimal("-3.5")) == Decimal("-3.5")


def test_rejects_float():
    with pytest.raises(FloatNotAllowed):
        to_decimal(1.25)


def test_rejects_bool_none_and_other_types():
    for bad in (True, False, None, [1], {"value": "1"}):
        with pytest.raises(TypeError):
            to_decimal(bad)


def test_rejects_unparseable_and_non_finite():
    for bad in ("", "abc", "1,250", "NaN", "Infinity", "-Infinity", "1e400000000000"):
        with pytest.raises(ValueError):
            to_decimal(bad)
    with pytest.raises(ValueError):
        to_decimal(Decimal("NaN"))


def test_round_half_up_ratios():
    assert round_half_up(Decimal("1.245"), 2) == Decimal("1.25")
    assert round_half_up(Decimal("1.2449999"), 2) == Decimal("1.24")
    assert round_half_up(Decimal("1.195"), 2) == Decimal("1.20")
    # Bankers' rounding would give 0.12 and 2; half-up must not.
    assert round_half_up(Decimal("0.125"), 2) == Decimal("0.13")
    assert round_half_up(Decimal("2.5"), 0) == Decimal("3")


def test_round_half_up_negative_rounds_away_from_zero():
    assert round_half_up(Decimal("-1.245"), 2) == Decimal("-1.25")
    assert round_half_up(Decimal("-2.5"), 0) == Decimal("-3")


def test_round_half_up_keeps_exponent():
    assert str(round_half_up(Decimal("1.2"), 2)) == "1.20"
    assert str(round_half_up(Decimal("1234.5"), 0)) == "1235"


def test_round_half_up_rejects_float_and_bad_dp():
    with pytest.raises(FloatNotAllowed):
        round_half_up(1.245, 2)
    with pytest.raises(ValueError):
        round_half_up(Decimal("1"), -1)
    with pytest.raises(TypeError):
        round_half_up(Decimal("1"), True)


def test_is_decimal_is_strict():
    assert is_decimal(Decimal("1"))
    assert not is_decimal(1)
    assert not is_decimal(1.0)
    assert not is_decimal(Decimal("NaN"))
