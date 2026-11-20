from datetime import date
from decimal import Decimal as D

from app.calc.expr import shift_period_end
from app.calc.periods import provider_from_facts
from app.calc.signals import (
    RULES,
    PeriodMetrics,
    compute_signal_inputs,
    evaluate_signals,
)

OCT = date(2026, 10, 31)
VC = "vc-1"


def test_net_loss_does_not_apply_to_venture_template():
    net_loss = next(r for r in RULES if r.id == "net_loss")
    assert "vc-1" not in net_loss.templates and "ci-1" in net_loss.templates


def test_startup_rules_exist_for_vc_only():
    names = {r.id: r for r in RULES}
    for name in ("runway_below_watch", "runway_falling", "burn_rising", "revenue_below_plan"):
        assert names[name].templates == frozenset({"vc-1"})
    for name in ("reporting_late", "payment_past_due", "covenant_headroom_low", "covenant_headroom_falling"):
        assert {"vc-1", "ci-1"} <= names[name].templates
    assert names["revenue_ttm_decline"].templates == frozenset({"ci-1"})


def _entry(months_back, **metrics):
    return PeriodMetrics(shift_period_end(OCT, -months_back), 1,
                         {k: None if v is None else D(v) for k, v in metrics.items()})


def _run(entries, template_id=VC, **kw):
    return evaluate_signals(OCT, entries, template_id=template_id, **kw)


def _names(evaluation):
    return [s.rule_id for s in evaluation.signals]


def test_runway_below_watch_high_under_nine():
    out = _run([_entry(0, rml="7.1")])
    assert _names(out) == ["runway_below_watch"] and out.signals[0].severity == "high"


def test_runway_below_watch_medium_between_nine_and_twelve():
    out = _run([_entry(0, rml="10")])
    assert _names(out) == ["runway_below_watch"] and out.signals[0].severity == "medium"


def test_runway_ok_above_watch_and_at_watch():
    assert _names(_run([_entry(0, rml="13")])) == []
    assert _names(_run([_entry(0, rml="12")])) == []


def test_not_meaningful_runway_never_fires():
    out = _run([_entry(3, rml="20"), _entry(2, rml="18"), _entry(1, rml="15"),
                _entry(0, rml=None, rml_not_meaningful="1")])
    assert _names(out) == []
    assert all(n.reason == "not_meaningful" for n in out.not_evaluated if n.rule_id.startswith("runway"))


def test_runway_falling_three_falling_months():
    entries = [_entry(3, rml="20"), _entry(2, rml="18"), _entry(1, rml="16"), _entry(0, rml="14")]
    assert _names(_run(entries)) == ["runway_falling"]


def test_runway_not_falling_when_it_ticks_up():
    entries = [_entry(3, rml="20"), _entry(2, rml="18"), _entry(1, rml="19"), _entry(0, rml="14")]
    assert _names(_run(entries)) == []


def test_burn_rising_against_three_months_earlier():
    entries = [_entry(3, avg_net_burn="500000"), _entry(0, avg_net_burn="650000")]
    out = _run(entries)
    assert _names(out) == ["burn_rising"] and out.signals[0].basis["change"] == D("0.3000")


def test_burn_not_rising_under_threshold():
    entries = [_entry(3, avg_net_burn="500000"), _entry(0, avg_net_burn="590000")]
    assert _names(_run(entries)) == []


def test_burn_without_prior_is_not_evaluated():
    out = _run([_entry(0, avg_net_burn="650000")])
    assert _names(out) == [] and any(n.rule_id == "burn_rising" for n in out.not_evaluated)


def test_revenue_below_plan_fires_under_one():
    assert _names(_run([_entry(0, plan_ratio="0.8000")])) == ["revenue_below_plan"]
    assert _names(_run([_entry(0, plan_ratio="1.0000")])) == []


def test_no_plan_means_the_rule_does_not_fire():
    # absent data is not a signal: it is reported as not evaluated, never as a miss
    out = _run([_entry(0, plan_ratio=None)])
    assert _names(out) == [] and any(n.rule_id == "revenue_below_plan" for n in out.not_evaluated)


def test_venture_rules_do_not_run_for_ci_and_ci_rules_not_for_venture():
    entries = [_entry(0, rml="2", net_income_ttm="-5")]
    assert _names(_run(entries, template_id="ci-1")) == ["net_loss"]
    assert _names(_run(entries, template_id=VC)) == ["runway_below_watch"]


def test_custom_watch_level_is_a_rule_param():
    from dataclasses import replace
    rule = next(r for r in RULES if r.id == "runway_below_watch")
    tight = replace(rule, params={"watch": D("6"), "high_below": D("3")})
    assert _names(_run([_entry(0, rml="7.1")], rules=[tight])) == []


# ---- compute_signal_inputs for the venture template ------------------------------------------



def _provider(plan_revenue=True):
    facts = {
        ("bs.cash_unrestricted", OCT, 10): D("4600000"),
        ("cf.vc_operating_cash_flow", OCT, 10): D("-6500000"),
        ("cf.vc_operating_cash_flow", date(2026, 7, 31), 7): D("-4550000"),
        ("cf.vc_capex", OCT, 10): D("0"), ("cf.vc_capex", date(2026, 7, 31), 7): D("0"),
        ("cf.capitalised_software_spend", OCT, 10): D("0"),
        ("cf.capitalised_software_spend", date(2026, 7, 31), 7): D("0"),
        ("is.subscription_revenue", OCT, 10): D("7700000"),
        ("is.subscription_revenue", date(2026, 7, 31), 7): D("5300000"),
        ("is.services_revenue", OCT, 10): D("0"), ("is.services_revenue", date(2026, 7, 31), 7): D("0"),
    }
    return provider_from_facts(facts)


PLAN = {date(2026, 8, 31): D("1000000"), date(2026, 9, 30): D("1000000"), OCT: D("1000000")}


def test_compute_inputs_venture_values():
    inputs = compute_signal_inputs(OCT, _provider(), template_id=VC, plan=PLAN)
    assert inputs.values["avg_net_burn"] == D("650000")
    assert inputs.values["rml"].quantize(D("0.1")) == D("7.1")
    assert inputs.values["plan_ratio"] == D("0.8")
    assert inputs.values["rml_not_meaningful"] == D("0")
    assert "net_income_ttm" not in inputs.values


def test_compute_inputs_without_plan_has_no_plan_ratio():
    inputs = compute_signal_inputs(OCT, _provider(), template_id=VC)
    assert inputs.values["plan_ratio"] is None and "plan_ratio" not in inputs.errors


def test_compute_inputs_plan_missing_a_month_gives_no_ratio():
    plan = {k: v for k, v in PLAN.items() if k != date(2026, 8, 31)}
    inputs = compute_signal_inputs(OCT, _provider(), template_id=VC, plan=plan)
    assert inputs.values["plan_ratio"] is None


def test_compute_inputs_history_is_monthly_and_prior_only():
    inputs = compute_signal_inputs(OCT, _provider(), template_id=VC, history_months=2)
    assert sorted(inputs.history) == [date(2026, 8, 31), date(2026, 9, 30)]
    assert inputs.history[date(2026, 9, 30)].values["rml"] is None  # no facts for that month: unmeasured
    assert inputs.history[date(2026, 9, 30)].errors["rml"]


def test_compute_inputs_not_meaningful_runway_flag():
    p = provider_from_facts({
        ("bs.cash_unrestricted", OCT, 10): D("9000000"),
        ("cf.vc_operating_cash_flow", OCT, 10): D("300000"),
        ("cf.vc_operating_cash_flow", date(2026, 7, 31), 7): D("100000"),
        ("cf.vc_capex", OCT, 10): D("0"), ("cf.vc_capex", date(2026, 7, 31), 7): D("0"),
        ("cf.capitalised_software_spend", OCT, 10): D("0"),
        ("cf.capitalised_software_spend", date(2026, 7, 31), 7): D("0"),
    })
    inputs = compute_signal_inputs(OCT, p, template_id=VC)
    assert inputs.values["rml"] is None and inputs.values["rml_not_meaningful"] == D("1")
    assert "rml" not in inputs.errors
