from datetime import date
from decimal import Decimal as D

import pytest
from app.calc import errors as E
from app.calc.expr import validate_node
from app.calc.metrics import METRICS, METRICS_VERSION, compute_metric, compute_metrics, metric_definitions
from app.calc.periods import provider_from_facts

FYE = date(2025, 12, 31)
PRIOR_FYE = date(2024, 12, 31)

FY2025 = {
    "is.revenue": "3900000", "is.cogs": "2360000", "is.gross_profit": "1540000",
    "is.net_income": "150000", "is.interest_expense": "120000", "is.income_tax_expense": "70000",
    "is.depreciation_amortization": "160000",
    "bs.cash": "150000", "bs.accounts_receivable": "650000", "bs.inventory": "520000",
    "bs.total_current_assets": "1400000", "bs.intangibles": "300000",
    "bs.accounts_payable": "320000", "bs.revolver": "650000", "bs.cpltd": "100000",
    "bs.total_current_liabilities": "1170000", "bs.long_term_debt": "850000",
    "bs.subordinated_debt": "200000", "bs.total_liabilities": "2220000", "bs.total_equity": "730000",
    "cf.capex": "200000", "cf.distributions": "290000",
    "sup.cash_interest_paid": "120000", "sup.cash_taxes_paid": "65000",
    "sup.scheduled_principal": "100000", "sup.financed_capex": "20000",
    "bb.availability": "400000",
}
FACTS = {(k, FYE, 12): D(v) for k, v in FY2025.items()}
FACTS[("is.revenue", PRIOR_FYE, 12)] = D("4000000")
PROVIDER = provider_from_facts(FACTS)

# Hand-computed from FY2025 above (TTM at a fiscal year end is the fiscal year).
EXPECTED = {
    "ebitda": ("500000", "usd"),  # 150,000 + 120,000 + 70,000 + 160,000
    "total_debt": ("1800000", "usd"),  # 650,000 + 100,000 + 850,000 + 200,000
    "senior_debt": ("1600000", "usd"),  # 1,800,000 - 200,000
    "tangible_net_worth": ("430000", "usd"),  # 730,000 - 300,000
    "working_capital": ("230000", "usd"),  # 1,400,000 - 1,170,000
    "current_ratio": ("1.20", "ratio"),  # 1,400,000 / 1,170,000 = 1.19658
    "quick_ratio": ("0.68", "ratio"),  # (150,000 + 650,000) / 1,170,000 = 0.68376
    "leverage": ("3.60", "ratio"),  # 1,800,000 / 500,000
    "senior_leverage": ("3.20", "ratio"),  # 1,600,000 / 500,000
    "interest_coverage": ("4.17", "ratio"),  # 500,000 / 120,000 = 4.16667
    "dscr": ("2.27", "ratio"),  # 500,000 / (120,000 + 100,000) = 2.27273
    # (500,000 - (200,000 - 20,000) - 65,000 - 290,000) / (120,000 + 100,000) = -35,000 / 220,000
    "fccr": ("-0.16", "ratio"),
    "debt_to_tnw": ("5.16", "ratio"),  # 2,220,000 / 430,000 = 5.16279
    "gross_margin": ("0.3949", "pct"),  # 1,540,000 / 3,900,000 = 0.394872
    "ebitda_margin": ("0.1282", "pct"),  # 500,000 / 3,900,000 = 0.128205
    "net_margin": ("0.0385", "pct"),  # 150,000 / 3,900,000 = 0.038462
    "dso": ("60.8", "days"),  # 650,000 x 365 / 3,900,000 = 60.8333
    "dio": ("80.4", "days"),  # 520,000 x 365 / 2,360,000 = 80.4237
    "dpo": ("49.5", "days"),  # 320,000 x 365 / 2,360,000 = 49.4915
    "revenue_growth_yoy": ("-0.0250", "pct"),  # 3,900,000 / 4,000,000 - 1
    "liquidity": ("550000", "usd"),  # 150,000 + 400,000
}


def test_library_is_metrics_1_with_the_spec_names():
    assert METRICS_VERSION == "metrics-1"
    assert set(METRICS) == set(EXPECTED)


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_metric_value_unit_and_rounding(name):
    value, unit = EXPECTED[name]
    result = compute_metric(name, FYE, PROVIDER)
    assert result.errors == []
    assert str(result.rounded) == value
    assert METRICS[name].unit == unit


def test_every_tree_is_structurally_valid():
    definitions = metric_definitions()
    for name, metric in METRICS.items():
        assert validate_node(metric.expr, definitions) == [], name
        assert metric.rounding["mode"] == "half_up"
        assert metric.rounding["dp"] == {"usd": 0, "ratio": 2, "pct": 4, "days": 1}[metric.unit]


def test_leverage_trace_names_debt_and_ebitda_inputs():
    result = compute_metric("leverage", FYE, PROVIDER, calc_id="c1")
    assert result.calc_id == "c1"
    assert [i.key for i in result.trace.inputs] == [
        "bs.revolver", "bs.cpltd", "bs.long_term_debt", "bs.subordinated_debt",
        "is.net_income", "is.interest_expense", "is.income_tax_expense", "is.depreciation_amortization",
    ]


def test_unmeasured_metric_is_null_with_an_error_never_zero():
    facts = dict(FACTS)
    del facts[("is.depreciation_amortization", FYE, 12)]
    result = compute_metric("leverage", FYE, provider_from_facts(facts))
    assert result.value is None and result.rounded is None
    assert [(e.code, e.key, e.period_end, e.months) for e in result.errors] == [
        (E.MISSING_INPUT, "is.depreciation_amortization", FYE, 12)]


def test_non_positive_ebitda_makes_leverage_an_error():
    facts = dict(FACTS)
    facts[("is.net_income", FYE, 12)] = D("-350000")  # EBITDA = 0
    result = compute_metric("leverage", FYE, provider_from_facts(facts))
    assert result.value is None and [e.code for e in result.errors] == [E.NON_POSITIVE_DENOMINATOR]


def test_unknown_metric_is_an_error_not_an_exception():
    result = compute_metric("ebitdar", FYE, PROVIDER)
    assert result.value is None and [e.code for e in result.errors] == [E.UNKNOWN_DEFINITION]


def test_compute_metrics_returns_one_result_per_name():
    results = compute_metrics(["ebitda", "dso"], FYE, PROVIDER)
    assert {k: str(v.rounded) for k, v in results.items()} == {"ebitda": "500000", "dso": "60.8"}
    assert set(compute_metrics(None, FYE, PROVIDER)) == set(METRICS)
