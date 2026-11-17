from dataclasses import fields
from datetime import date
from decimal import Decimal as D

import pytest
from app.calc.periods import FactValue, provider_from_facts
from app.calc.signals import (
    RULES,
    SIGNALS_VERSION,
    AuditorOpinion,
    PeriodMetrics,
    ReportingItem,
    Signal,
    SystemRow,
    compute_signal_inputs,
    evaluate_signals,
    reporting_due_date,
)

Q4_23, Q1_24, Q2_24, Q3_24, Q4_24 = (date(2023, 12, 31), date(2024, 3, 31), date(2024, 6, 30),
                                     date(2024, 9, 30), date(2024, 12, 31))
PE = Q4_24
MONTHS = {Q4_23: 12, Q1_24: 3, Q2_24: 6, Q3_24: 9, Q4_24: 12}

BASE = {"revenue_ttm": "4000000", "ebitda_margin": "0.1500", "dso": "45.0", "dpo": "40.0", "leverage": "2.50",
        "net_income_ttm": "300000", "cash": "500000", "availability": "1000000"}


def period(period_end, headroom=None, **metrics):
    values = {k: D(v) for k, v in BASE.items()}
    for key, value in metrics.items():
        values[key] = None if value is None else D(value)
    return PeriodMetrics(period_end, MONTHS[period_end], values,
                         {k: None if v is None else D(v) for k, v in (headroom or {}).items()})


def series(current=None, prior_year=None, headrooms=("0.30", "0.30", "0.30")):
    """Five quarters; `prior_year` overrides Q4 2023 metrics and `current` overrides Q4 2024."""
    h2, h1, h0 = headrooms
    return [
        period(Q4_23, {"fccr": "0.30"}, **(prior_year or {})),
        period(Q1_24, {"fccr": "0.30"}),
        period(Q2_24, {"fccr": h2}),
        period(Q3_24, {"fccr": h1}),
        period(Q4_24, {"fccr": h0}, **(current or {})),
    ]


ROW = SystemRow(date(2024, 12, 31), D("2000000"), D("5000000"), 0)


def fired(evaluation):
    return [s.rule_id for s in evaluation.signals]


def run(data=None, **kw):
    kw.setdefault("system_rows", [ROW])
    return evaluate_signals(PE, data or series(), **kw)


def only(evaluation, rule_id):
    (signal,) = [s for s in evaluation.signals if s.rule_id == rule_id]
    return signal


def test_rule_table_is_signals_1():
    assert SIGNALS_VERSION == "signals-1"
    assert [r.id for r in RULES] == [
        "covenant_headroom_low", "covenant_headroom_falling", "revenue_ttm_decline", "ebitda_margin_decline",
        "dso_increase", "dpo_increase", "leverage_increase", "net_loss", "cash_decline", "line_usage_high",
        "availability_low", "reporting_late", "payment_past_due", "auditor_opinion",
    ]
    assert {r.id: r.severity for r in RULES} == {
        "covenant_headroom_low": "medium", "covenant_headroom_falling": "low", "revenue_ttm_decline": "medium",
        "ebitda_margin_decline": "medium", "dso_increase": "medium", "dpo_increase": "medium",
        "leverage_increase": "medium", "net_loss": "high", "cash_decline": "medium", "line_usage_high": "medium",
        "availability_low": "medium", "reporting_late": "high", "payment_past_due": "high",
        "auditor_opinion": "high",
    }


def test_a_healthy_borrower_fires_nothing():
    evaluation = run()
    assert evaluation.signals == [] and evaluation.not_evaluated == []


def test_signal_is_machine_readable_with_no_prose():
    assert [f.name for f in fields(Signal)] == ["rule_id", "severity", "period_end", "subject", "basis"]


# ---- covenant headroom ---------------------------------------------------------------------------


def test_headroom_below_ten_percent():
    signal = only(run(series(headrooms=("0.30", "0.30", "0.0999"))), "covenant_headroom_low")
    assert signal.subject == "fccr" and signal.period_end == PE and signal.severity == "medium"
    assert signal.basis == {
        "metric": "headroom_pct", "covenant_id": "fccr",
        "current": {"period_end": PE, "months": 12, "value": D("0.0999"), "fact_id": None},
        "threshold": D("0.10"),
    }
    assert "covenant_headroom_low" not in fired(run(series(headrooms=("0.30", "0.30", "0.10"))))
    assert "covenant_headroom_low" in fired(run(series(headrooms=("0.30", "0.30", "-0.05"))))  # a breach is also low


def test_headroom_falling_two_periods_running():
    signal = only(run(series(headrooms=("0.30", "0.25", "0.20"))), "covenant_headroom_falling")
    assert signal.subject == "fccr"
    assert [(p["period_end"], p["value"]) for p in signal.basis["values"]] == [
        (Q2_24, D("0.30")), (Q3_24, D("0.25")), (Q4_24, D("0.20"))]
    assert "covenant_headroom_falling" not in fired(run(series(headrooms=("0.30", "0.20", "0.20"))))  # flat, not falling
    assert "covenant_headroom_falling" not in fired(run(series(headrooms=("0.20", "0.30", "0.25"))))  # one fall only


def test_headroom_rules_skip_unmeasured_periods_and_say_so():
    evaluation = run(series(headrooms=("0.30", None, "0.20")))
    assert "covenant_headroom_falling" not in fired(evaluation)
    assert [(n.rule_id, n.subject, n.reason) for n in evaluation.not_evaluated] == [
        ("covenant_headroom_falling", "fccr", "missing_value")]
    evaluation = run(series(headrooms=("0.30", "0.30", None)))
    assert {(n.rule_id, n.reason) for n in evaluation.not_evaluated} == {
        ("covenant_headroom_low", "missing_value"), ("covenant_headroom_falling", "missing_value")}


# ---- year-on-year changes -------------------------------------------------------------------------


def test_revenue_down_more_than_ten_percent_year_on_year():
    signal = only(run(series(current={"revenue_ttm": "3599000"})), "revenue_ttm_decline")
    assert signal.basis["metric"] == "revenue_ttm" and signal.basis["compare"] == "yoy"
    assert signal.basis["current"] == {"period_end": PE, "months": 12, "value": D("3599000"), "fact_id": None}
    assert signal.basis["prior"]["period_end"] == Q4_23 and signal.basis["prior"]["value"] == D("4000000")
    # (3,599,000 - 4,000,000) / 4,000,000 = -0.10025, which rounds half-up to -0.1003
    assert signal.basis["change"] == D("-0.1003") and signal.basis["threshold"] == D("0.10")
    assert "revenue_ttm_decline" not in fired(run(series(current={"revenue_ttm": "3600000"})))  # exactly 10%
    # -0.1000025 rounds to -10.00%, which is not more than 10%: the figure shown is the figure tested.
    assert "revenue_ttm_decline" not in fired(run(series(current={"revenue_ttm": "3599990"})))


def test_ebitda_margin_down_more_than_three_points():
    signal = only(run(series(current={"ebitda_margin": "0.1199"})), "ebitda_margin_decline")
    assert signal.basis["change"] == D("-0.0301") and signal.basis["threshold"] == D("0.03")
    assert "ebitda_margin_decline" not in fired(run(series(current={"ebitda_margin": "0.1200"})))
    assert "ebitda_margin_decline" not in fired(run(series(current={"ebitda_margin": "0.11996"})))  # -0.0300


def test_changes_are_rounded_once_from_unrounded_metrics():
    # Leverage 3.2753664 against 2.2344398 a year earlier is up 1.0409 -> 1.04.
    # Differencing the rounded ratios (3.28 - 2.23) would wrongly give 1.05.
    data = series(prior_year={"leverage": "2.2344398"}, current={"leverage": "3.2753664"})
    signal = only(run(data), "leverage_increase")
    assert signal.basis["change"] == D("1.04")
    assert signal.basis["current"]["value"] == D("3.2753664") and signal.basis["prior"]["value"] == D("2.2344398")
    # 2.996 - 2.50 = 0.496 -> 0.50, which is not more than 0.5 even though both ratios round apart by 0.50.
    assert "leverage_increase" not in fired(run(series(current={"leverage": "2.996"})))
    assert "leverage_increase" in fired(run(series(current={"leverage": "3.005"})))  # 0.505 -> 0.51


def test_dso_and_dpo_increases():
    assert only(run(series(current={"dso": "55.1"})), "dso_increase").basis["change"] == D("10.1")
    assert "dso_increase" not in fired(run(series(current={"dso": "55.0"})))
    assert "dso_increase" not in fired(run(series(current={"dso": "55.04"})))  # 10.04 -> 10.0
    assert only(run(series(current={"dpo": "55.1"})), "dpo_increase").basis["change"] == D("15.1")
    assert "dpo_increase" not in fired(run(series(current={"dpo": "55.0"})))


def test_leverage_up_more_than_half_a_turn():
    assert only(run(series(current={"leverage": "3.01"})), "leverage_increase").severity == "medium"
    assert "leverage_increase" not in fired(run(series(current={"leverage": "3.00"})))


def test_cash_down_more_than_thirty_percent():
    signal = only(run(series(current={"cash": "349000"})), "cash_decline")
    assert signal.basis["prior"]["value"] == D("500000") and signal.basis["change"] == D("-0.3020")
    assert "cash_decline" not in fired(run(series(current={"cash": "350000"})))


def test_net_loss_ttm():
    signal = only(run(series(current={"net_income_ttm": "-1"})), "net_loss")
    assert signal.severity == "high" and signal.basis["threshold"] == D("0")
    assert signal.basis["current"]["value"] == D("-1")
    assert "net_loss" not in fired(run(series(current={"net_income_ttm": "0"})))


def test_unmeasured_metrics_are_reported_not_treated_as_zero():
    evaluation = run(series(current={"revenue_ttm": None, "net_income_ttm": None}))
    assert evaluation.signals == []
    assert {(n.rule_id, n.reason) for n in evaluation.not_evaluated} == {
        ("revenue_ttm_decline", "missing_value"), ("net_loss", "missing_value")}


def test_no_prior_year_period_and_non_positive_base():
    evaluation = run(series()[1:])  # Q4 2023 is not in the series
    reasons = {(n.rule_id, n.reason) for n in evaluation.not_evaluated}
    assert ("revenue_ttm_decline", "no_comparison_period") in reasons and ("cash_decline", "no_comparison_period") in reasons
    evaluation = run(series(prior_year={"cash": "0"}, current={"cash": "0"}))
    assert ("cash_decline", "non_positive_base") in {(n.rule_id, n.reason) for n in evaluation.not_evaluated}


def test_fact_ids_travel_into_the_basis():
    data = series()
    data[-1].metrics["net_income_ttm"] = FactValue(D("-5"), "fact-ni")
    assert only(run(data), "net_loss").basis["current"]["fact_id"] == "fact-ni"


# ---- system of record -----------------------------------------------------------------------------


def test_line_usage_above_ninety_percent():
    row = SystemRow(date(2024, 12, 31), D("4516500"), D("5000000"), 0)
    signal = only(run(system_rows=[row]), "line_usage_high")
    assert signal.basis == {"date": date(2024, 12, 31), "revolver_outstanding": D("4516500"),
                            "commitment": D("5000000"), "usage": D("0.9033"), "threshold": D("0.90")}
    exact = SystemRow(date(2024, 12, 31), D("4500000"), D("5000000"), 0)
    assert "line_usage_high" not in fired(run(system_rows=[exact]))
    hair = SystemRow(date(2024, 12, 31), D("4500001"), D("5000000"), 0)  # 0.9000002 -> 90.00%
    assert "line_usage_high" not in fired(run(system_rows=[hair]))


def test_latest_system_row_on_or_before_the_period_end_is_used():
    rows = [SystemRow(date(2024, 11, 30), D("4900000"), D("5000000"), 0), ROW,
            SystemRow(date(2025, 1, 31), D("4900000"), D("5000000"), 45)]
    assert run(system_rows=rows).signals == []


def test_availability_below_ten_percent_of_commitment():
    signal = only(run(series(current={"availability": "499000"})), "availability_low")
    assert signal.severity == "medium"
    assert signal.basis["availability"]["value"] == D("499000") and signal.basis["commitment"] == D("5000000")
    assert signal.basis["ratio"] == D("0.0998") and signal.basis["threshold"] == D("0.10")
    assert "availability_low" not in fired(run(series(current={"availability": "500000"})))
    over_advanced = only(run(series(current={"availability": "-81949"})), "availability_low")
    assert over_advanced.basis["ratio"] == D("-0.0164")  # -81,949 / 5,000,000 = -0.01639


def test_availability_left_unmeasured_is_not_evaluated():
    evaluation = run(series(current={"availability": None}))
    assert evaluation.signals == []
    assert [(n.rule_id, n.reason) for n in evaluation.not_evaluated] == [("availability_low", "missing_value")]


def test_payment_past_due_more_than_ten_days():
    signal = only(run(system_rows=[SystemRow(PE, D("2000000"), D("5000000"), 11)]), "payment_past_due")
    assert signal.severity == "high"
    assert signal.basis == {"date": PE, "past_due_days": 11, "threshold": 10}
    assert "payment_past_due" not in fired(run(system_rows=[SystemRow(PE, D("2000000"), D("5000000"), 10)]))


def test_system_rules_without_a_row_are_not_evaluated():
    evaluation = run(system_rows=[])
    assert evaluation.signals == []
    assert {n.rule_id for n in evaluation.not_evaluated} == {"line_usage_high", "availability_low", "payment_past_due"}
    assert {n.reason for n in evaluation.not_evaluated} == {"no_system_row"}


# ---- reporting and the auditor's opinion --------------------------------------------------------------


def test_reporting_more_than_fifteen_days_late():
    due = date(2025, 4, 30)
    late = ReportingItem("annual_fs", PE, due, date(2025, 5, 16))
    signal = only(run(reporting=[late]), "reporting_late")
    assert signal.subject == "annual_fs" and signal.severity == "high"
    assert signal.basis == {"requirement_id": "annual_fs", "period_end": PE, "due_date": due,
                            "received_date": date(2025, 5, 16), "as_of": None, "days_late": 16, "threshold": 15}
    on_time = ReportingItem("annual_fs", PE, due, date(2025, 5, 15))
    assert "reporting_late" not in fired(run(reporting=[on_time]))


def test_unreceived_reporting_is_measured_against_the_as_of_date():
    due = date(2025, 4, 30)
    outstanding = ReportingItem("annual_fs", PE, due, None)
    signal = only(run(reporting=[outstanding], as_of=date(2025, 6, 1)), "reporting_late")
    assert signal.basis["days_late"] == 32 and signal.basis["received_date"] is None
    assert "reporting_late" not in fired(run(reporting=[outstanding], as_of=date(2025, 5, 15)))
    evaluation = run(reporting=[outstanding])  # no date passed in: nothing is assumed about today
    assert [(n.rule_id, n.subject, n.reason) for n in evaluation.not_evaluated] == [
        ("reporting_late", "annual_fs", "no_as_of_date")]


def test_auditor_opinion_qualified_or_going_concern():
    for opinion in ("qualified", "going_concern"):
        item = AuditorOpinion(PE, opinion, fact_id="fact-op", document_id="doc-9", page=3)
        signal = only(run(opinions=[item]), "auditor_opinion")
        assert signal.severity == "high"
        assert signal.basis == {"opinion": opinion, "period_end": PE, "fact_id": "fact-op",
                                "document_id": "doc-9", "page": 3}
    assert run(opinions=[AuditorOpinion(PE, "unqualified", None, None, None)]).signals == []


# ---- plumbing ----------------------------------------------------------------------------------------


def test_floats_and_a_missing_current_period_are_refused():
    with pytest.raises(TypeError):
        PeriodMetrics(PE, 12, {"cash": 5.0})
    with pytest.raises(TypeError):
        SystemRow(PE, 2000000.0, D("5000000"), 0)
    with pytest.raises(ValueError):
        evaluate_signals(date(2025, 3, 31), series(), system_rows=[ROW])
    with pytest.raises(ValueError):
        evaluate_signals(PE, series() + [period(PE)], system_rows=[ROW])


def test_series_order_does_not_matter():
    data = series(headrooms=("0.30", "0.25", "0.20"))
    assert fired(run(list(reversed(data)))) == fired(run(data)) == ["covenant_headroom_falling"]


def test_compute_signal_inputs_reads_the_library():
    facts = {
        ("is.revenue", PE, 12): D("4000000"), ("is.net_income", PE, 12): D("300000"),
        ("is.interest_expense", PE, 12): D("100000"), ("is.income_tax_expense", PE, 12): D("100000"),
        ("is.depreciation_amortization", PE, 12): D("100000"), ("is.cogs", PE, 12): D("2920000"),
        ("bs.cash", PE, 12): D("500000"), ("bs.accounts_receivable", PE, 12): D("400000"),
        ("bs.revolver", PE, 12): D("600000"), ("bs.cpltd", PE, 12): D("100000"),
        ("bs.long_term_debt", PE, 12): D("500000"), ("bs.subordinated_debt", PE, 12): D("0"),
    }
    inputs = compute_signal_inputs(PE, provider_from_facts(facts))
    assert inputs.values == {
        "revenue_ttm": D("4000000"), "net_income_ttm": D("300000"), "cash": D("500000"),
        "ebitda_margin": D("0.15"),  # 600,000 / 4,000,000
        "dso": D("36.5"),  # 400,000 x 365 / 4,000,000
        "dpo": None,  # accounts payable is missing: unmeasured, not zero
        "leverage": D("2"),  # 1,200,000 / 600,000
    }
    assert list(inputs.errors) == ["dpo"] and inputs.errors["dpo"][0].key == "bs.accounts_payable"
    assert [i.key for i in inputs.traces["cash"].inputs] == ["bs.cash"]


def test_inputs_are_unrounded_so_the_rules_round_only_once():
    facts = {("is.revenue", PE, 12): D("3000000"), ("bs.accounts_receivable", PE, 12): D("400000")}
    dso = compute_signal_inputs(PE, provider_from_facts(facts)).values["dso"]
    assert dso != D("48.7") and abs(dso - D("48.6666666667")) < D("1e-9")  # 146,000,000 / 3,000,000


def test_reporting_due_date():
    assert reporting_due_date(date(2026, 9, 30), 30) == date(2026, 10, 30)
    assert reporting_due_date(date(2025, 12, 31), 120) == date(2026, 4, 30)
