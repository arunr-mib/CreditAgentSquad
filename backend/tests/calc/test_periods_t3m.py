from datetime import date
from decimal import Decimal as D

from app.calc.expr import evaluate
from app.calc.periods import provider_from_facts, resolve_line

K = "cf.vc_operating_cash_flow"


def test_within_the_fiscal_year():
    facts = {(K, date(2026, 10, 31), 10): D("-6500"), (K, date(2026, 7, 31), 7): D("-4550")}
    res = resolve_line(K, "t3m", date(2026, 10, 31), provider_from_facts(facts))
    assert res.errors == [] and res.value == D("-1950")


def test_exactly_three_months_into_the_year():
    facts = {(K, date(2026, 3, 31), 3): D("-1800")}
    res = resolve_line(K, "t3m", date(2026, 3, 31), provider_from_facts(facts))
    assert res.value == D("-1800")


def test_across_the_fiscal_year_end():
    # Review focus 2: January with a December year end uses November and December of the prior year
    facts = {
        (K, date(2026, 1, 31), 1): D("-600"),
        (K, date(2025, 12, 31), 12): D("-7000"),
        (K, date(2025, 10, 31), 10): D("-5800"),
    }
    res = resolve_line(K, "t3m", date(2026, 1, 31), provider_from_facts(facts))
    assert res.value == D("-1800")  # -600 + (-7000) - (-5800)


def test_missing_month_is_an_error_not_zero():
    facts = {(K, date(2026, 10, 31), 10): D("-6500")}
    res = resolve_line(K, "t3m", date(2026, 10, 31), provider_from_facts(facts))
    assert res.value is None and res.errors[0].code == "missing_input"


def test_point_lines_cannot_be_t3m():
    res = resolve_line("bs.cash_unrestricted", "t3m", date(2026, 10, 31), provider_from_facts({}))
    assert res.value is None and res.errors[0].code == "invalid_period_mode"


def test_line_node_accepts_t3m_in_evaluate():
    facts = {(K, date(2026, 10, 31), 10): D("-6500"), (K, date(2026, 7, 31), 7): D("-4550")}
    node = {"op": "line", "key": K, "period": "t3m"}
    result = evaluate(node, date(2026, 10, 31), provider_from_facts(facts))
    assert result.errors == [] and result.value == D("-1950")
