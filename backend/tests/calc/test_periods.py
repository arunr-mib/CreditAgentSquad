from datetime import date
from decimal import Decimal as D

import pytest
from app.calc import errors as E
from app.calc.periods import (
    FactValue,
    PeriodKey,
    is_fiscal_year_end,
    prior_fiscal_year_end,
    provider_from_facts,
    resolve_line,
    same_period_prior_year,
    ytd_months,
)

FACTS = {
    ("is.revenue", date(2024, 6, 30), 6): D("2000000"),
    ("is.revenue", date(2024, 12, 31), 12): D("4000000"),
    ("is.revenue", date(2025, 6, 30), 6): FactValue(D("1900000"), "fact-rev-h1-25"),
    ("is.revenue", date(2025, 12, 31), 12): D("3900000"),
    ("bs.cash", date(2025, 6, 30), 6): FactValue(D("200000"), "fact-cash"),
    ("bs.cash", date(2025, 12, 31), 12): D("150000"),
    # A June fiscal year: FY ends 2025-06-30, first quarter ends 2025-09-30.
    ("is.cogs", date(2024, 9, 30), 3): D("500"),
    ("is.cogs", date(2025, 6, 30), 12): D("2400"),
    ("is.cogs", date(2025, 9, 30), 3): D("650"),
}


def recording_provider():
    calls = []
    inner = provider_from_facts(FACTS)

    def get(key, period_end, months):
        calls.append((key, period_end, months))
        return inner(key, period_end, months)

    return get, calls


def test_period_key_is_hashable_and_ordered():
    a, b = PeriodKey(date(2025, 6, 30), 6), PeriodKey(date(2025, 12, 31), 12)
    assert a < b and len({a, b, PeriodKey(date(2025, 6, 30), 6)}) == 2


def test_ytd_months_for_calendar_and_june_fiscal_years():
    assert [ytd_months(date(2025, m, 28), 12) for m in (3, 6, 9, 12)] == [3, 6, 9, 12]
    assert ytd_months(date(2025, 9, 30), 6) == 3
    assert ytd_months(date(2025, 6, 30), 6) == 12
    assert ytd_months(date(2025, 1, 31), 6) == 7
    with pytest.raises(ValueError):
        ytd_months(date(2025, 1, 31), 13)


def test_fiscal_year_helpers():
    assert is_fiscal_year_end(date(2025, 12, 31), 12)
    assert not is_fiscal_year_end(date(2025, 6, 30), 12)
    assert is_fiscal_year_end(date(2025, 6, 30), 6)
    assert prior_fiscal_year_end(date(2025, 6, 30), 12) == date(2024, 12, 31)
    assert prior_fiscal_year_end(date(2025, 12, 31), 12) == date(2024, 12, 31)
    assert prior_fiscal_year_end(date(2025, 9, 30), 6) == date(2025, 6, 30)
    assert prior_fiscal_year_end(date(2025, 3, 31), 2) == date(2025, 2, 28)
    assert prior_fiscal_year_end(date(2024, 3, 31), 2) == date(2024, 2, 29)


def test_same_period_prior_year_keeps_month_end():
    assert same_period_prior_year(date(2025, 6, 30)) == date(2024, 6, 30)
    assert same_period_prior_year(date(2024, 2, 29)) == date(2023, 2, 28)
    assert same_period_prior_year(date(2025, 2, 28)) == date(2024, 2, 29)


def test_point_reads_the_balance_at_the_period_end():
    get, calls = recording_provider()
    res = resolve_line("bs.cash", "point", date(2025, 6, 30), get)
    assert res.errors == [] and res.value == D("200000")
    assert calls == [("bs.cash", date(2025, 6, 30), 6)]
    (inp,) = res.inputs
    assert (inp.key, inp.period_end, inp.months, inp.value, inp.fact_id, inp.sign) == (
        "bs.cash", date(2025, 6, 30), 6, D("200000"), "fact-cash", 1)


def test_ytd_reads_the_fiscal_year_to_date_flow():
    get, calls = recording_provider()
    res = resolve_line("is.revenue", "ytd", date(2025, 6, 30), get)
    assert res.value == D("1900000")
    assert calls == [("is.revenue", date(2025, 6, 30), 6)]


def test_fy_at_year_end_and_refused_at_interim():
    get, _ = recording_provider()
    assert resolve_line("is.revenue", "fy", date(2025, 12, 31), get).value == D("3900000")
    res = resolve_line("is.revenue", "fy", date(2025, 6, 30), get)
    assert res.value is None
    assert [(e.code, e.key, e.period_end) for e in res.errors] == [
        (E.NOT_FISCAL_YEAR_END, "is.revenue", date(2025, 6, 30))]


def test_ttm_at_interim_is_ytd_plus_prior_fy_less_prior_ytd():
    get, calls = recording_provider()
    res = resolve_line("is.revenue", "ttm", date(2025, 6, 30), get)
    # 1,900,000 + 4,000,000 - 2,000,000
    assert res.errors == [] and res.value == D("3900000")
    assert calls == [
        ("is.revenue", date(2025, 6, 30), 6),
        ("is.revenue", date(2024, 12, 31), 12),
        ("is.revenue", date(2024, 6, 30), 6),
    ]
    assert [(i.period_end, i.months, i.sign, i.fact_id) for i in res.inputs] == [
        (date(2025, 6, 30), 6, 1, "fact-rev-h1-25"),
        (date(2024, 12, 31), 12, 1, None),
        (date(2024, 6, 30), 6, -1, None),
    ]


def test_ttm_at_fiscal_year_end_is_the_fiscal_year():
    get, calls = recording_provider()
    res = resolve_line("is.revenue", "ttm", date(2025, 12, 31), get)
    assert res.value == D("3900000")
    assert calls == [("is.revenue", date(2025, 12, 31), 12)]


def test_ttm_with_a_june_fiscal_year():
    get, calls = recording_provider()
    res = resolve_line("is.cogs", "ttm", date(2025, 9, 30), get, fye_month=6)
    assert res.value == D("2550")  # 650 + 2,400 - 500
    assert calls == [
        ("is.cogs", date(2025, 9, 30), 3),
        ("is.cogs", date(2025, 6, 30), 12),
        ("is.cogs", date(2024, 9, 30), 3),
    ]


def test_missing_input_names_line_and_period_and_is_never_zero():
    facts = dict(FACTS)
    del facts[("is.revenue", date(2024, 12, 31), 12)]
    del facts[("is.revenue", date(2024, 6, 30), 6)]
    res = resolve_line("is.revenue", "ttm", date(2025, 6, 30), provider_from_facts(facts))
    assert res.value is None
    assert [(e.code, e.key, e.period_end, e.months) for e in res.errors] == [
        (E.MISSING_INPUT, "is.revenue", date(2024, 12, 31), 12),
        (E.MISSING_INPUT, "is.revenue", date(2024, 6, 30), 6),
    ]
    assert len(res.inputs) == 1  # the one fact that was found is still traced


def test_unknown_line_and_bad_mode_are_errors():
    get, calls = recording_provider()
    assert resolve_line("is.ebitda", "ttm", date(2025, 6, 30), get).errors[0].code == E.UNKNOWN_LINE
    assert resolve_line("is.revenue", "qtd", date(2025, 6, 30), get).errors[0].code == E.INVALID_PERIOD_MODE
    assert calls == []


def test_mode_must_suit_the_line():
    get, _ = recording_provider()
    for key, mode in (("is.revenue", "point"), ("bs.cash", "ttm"), ("bs.cash", "ytd"), ("bs.cash", "fy")):
        res = resolve_line(key, mode, date(2025, 6, 30), get)
        assert res.value is None and res.errors[0].code == E.INVALID_PERIOD_MODE


def test_period_end_must_be_a_month_end_date():
    get, _ = recording_provider()
    assert resolve_line("bs.cash", "point", date(2025, 6, 29), get).errors[0].code == E.INVALID_PERIOD
    assert resolve_line("bs.cash", "point", "2025-06-30", get).errors[0].code == E.INVALID_PERIOD


def test_float_and_malformed_facts_are_refused():
    def floaty(key, period_end, months):
        return FactValue(1900000.0, "f1")

    res = resolve_line("is.revenue", "ytd", date(2025, 6, 30), floaty)
    assert res.value is None and res.errors[0].code == E.FLOAT_NOT_ALLOWED

    res = resolve_line("is.revenue", "ytd", date(2025, 6, 30), lambda k, p, m: "1900000")
    assert res.value is None and res.errors[0].code == E.INVALID_VALUE


def test_provider_from_facts_rejects_floats_up_front():
    with pytest.raises(TypeError):
        provider_from_facts({("is.revenue", date(2025, 6, 30), 6): 1.5})


def test_provider_accepts_plain_decimals():
    res = resolve_line("bs.cash", "point", date(2025, 12, 31), lambda k, p, m: D("150000"))
    assert res.value == D("150000") and res.inputs[0].fact_id is None
