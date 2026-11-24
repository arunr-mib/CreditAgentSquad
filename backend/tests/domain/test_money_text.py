from decimal import Decimal as D

from app.domain.money_text import dollars


def test_whole_dollars_have_no_cents_and_no_raw_decimal():
    assert dollars(D("15000000.00")) == "$15,000,000"
    assert dollars(D("8000000")) == "$8,000,000"
    assert dollars(D("0.00")) == "$0"


def test_cents_show_only_when_present_and_round_half_up():
    assert dollars(D("12000000.50")) == "$12,000,000.50"
    assert dollars(D("1.005")) == "$1.01"


def test_negative_amounts_use_parentheses():
    assert dollars(D("-2500")) == "($2,500)"
