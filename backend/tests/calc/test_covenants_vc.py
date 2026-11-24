from datetime import date
from decimal import Decimal as D

from app.calc.covenants import (
    COMPLIANT,
    COMPLIANT_VARIANCE,
    CovenantTestResult,
    compute_rml,
    determine_outcome,
    test_covenant,
)
from app.calc.periods import provider_from_facts
from app.calc.terms import Covenant

OCT = date(2026, 10, 31)


def _cov(archetype, params, threshold, unit, operator=">=", basis="point"):
    return Covenant.model_validate({
        "id": archetype, "name": archetype, "archetype": archetype, "params": params,
        "test": {"operator": operator, "threshold": str(threshold), "unit": unit, "steps": []},
        "measurement": {"basis": basis, "frequency": "monthly"},
        "rounding": {"dp": 1 if unit == "months" else 0, "mode": "half_up"},
    })


def _datamarrow():
    # unrestricted 4.6M; operating cash flow -1.95M over Aug-Oct (YTD Oct -6.5M, YTD Jul -4.55M); no capex
    return provider_from_facts({
        ("bs.cash_unrestricted", OCT, 10): D("4600000"),
        ("bs.cash_restricted", OCT, 10): D("700000"),
        ("cf.vc_operating_cash_flow", OCT, 10): D("-6500000"),
        ("cf.vc_operating_cash_flow", date(2026, 7, 31), 7): D("-4550000"),
        ("cf.vc_capex", OCT, 10): D("0"), ("cf.vc_capex", date(2026, 7, 31), 7): D("0"),
        ("cf.capitalised_software_spend", OCT, 10): D("0"),
        ("cf.capitalised_software_spend", date(2026, 7, 31), 7): D("0"),
    })


def test_min_unrestricted_cash_excludes_pledged_cash():
    result = test_covenant(_cov("min_unrestricted_cash", {}, 5000000, "usd"), OCT, _datamarrow())
    assert result.value == D("4600000") and result.passed is False


def test_rml_is_cash_over_average_three_month_burn():
    rml = compute_rml(OCT, _datamarrow())
    assert rml.burn == D("650000") and rml.value.quantize(D("0.1")) == D("7.1") and not rml.not_meaningful


def test_rml_covenant_breach_below_threshold():
    result = test_covenant(_cov("min_runway_months", {}, 9, "months", basis="t3m"), OCT, _datamarrow())
    assert result.value == D("7.1") and result.passed is False and result.note is None


def test_rml_not_meaningful_when_cash_flow_positive():
    # Review focus 1: burn <= 0 never divides
    provider = provider_from_facts({
        ("bs.cash_unrestricted", OCT, 10): D("9000000"),
        ("cf.vc_operating_cash_flow", OCT, 10): D("300000"),
        ("cf.vc_operating_cash_flow", date(2026, 7, 31), 7): D("100000"),
        ("cf.vc_capex", OCT, 10): D("0"), ("cf.vc_capex", date(2026, 7, 31), 7): D("0"),
        ("cf.capitalised_software_spend", OCT, 10): D("0"),
        ("cf.capitalised_software_spend", date(2026, 7, 31), 7): D("0"),
    })
    result = test_covenant(_cov("min_runway_months", {}, 9, "months", basis="t3m"), OCT, provider)
    assert result.passed is True and result.value is None
    assert result.note == "not_meaningful_cash_flow_positive" and result.errors == []


def test_not_meaningful_rml_maps_to_compliant_with_note():
    result = CovenantTestResult("min_runway_months", OCT, passed=True, threshold=D("9"),
                                note="not_meaningful_cash_flow_positive")
    outcome = determine_outcome(result, None, D("0"))
    assert outcome.outcome == COMPLIANT and outcome.note == "not_meaningful_cash_flow_positive"


def _plan(months):
    return {"metric": "revenue", "plan": [{"period_end": d.isoformat(), "amount": "1000000"} for d in months]}


def test_revenue_vs_plan_ratio():
    provider = provider_from_facts({
        ("is.subscription_revenue", OCT, 10): D("7700000"),
        ("is.subscription_revenue", date(2026, 7, 31), 7): D("5300000"),
        ("is.services_revenue", OCT, 10): D("0"), ("is.services_revenue", date(2026, 7, 31), 7): D("0"),
    })
    cov = _cov("revenue_vs_plan", _plan([date(2026, 8, 31), date(2026, 9, 30), OCT]), "0.80", "ratio", basis="t3m")
    cov = cov.model_copy(update={"rounding": cov.rounding.model_copy(update={"dp": 2})})
    result = test_covenant(cov, OCT, provider)
    assert result.value == D("0.80") and result.passed is True  # 2.4M of 3.0M plan


def test_revenue_vs_plan_missing_plan_month_cannot_test():
    # Review focus 4
    cov = _cov("revenue_vs_plan", _plan([date(2026, 9, 30), OCT]), "0.80", "ratio", basis="t3m")
    result = test_covenant(cov, OCT, provider_from_facts({}))
    assert result.passed is None
    assert any(e.code == "missing_parameter" and "2026-08-31" in e.message for e in result.errors)


def test_not_meaningful_rml_ignores_certificate_value():
    result = CovenantTestResult("min_runway_months", OCT, passed=True, threshold=D("9"),
                                note="not_meaningful_cash_flow_positive")
    entry = {"value": "24.0", "threshold": "9", "in_compliance": True}
    outcome = determine_outcome(result, entry, D("0.1"))
    assert outcome.outcome == COMPLIANT and outcome.note == "not_meaningful_cash_flow_positive"
    assert outcome.variances == []


def test_not_meaningful_rml_still_checks_certificate_compliance_flag():
    result = CovenantTestResult("min_runway_months", OCT, passed=True, threshold=D("9"),
                                note="not_meaningful_cash_flow_positive")
    entry = {"value": "2.0", "threshold": "9", "in_compliance": False}
    outcome = determine_outcome(result, entry, D("0.1"))
    assert outcome.outcome == COMPLIANT_VARIANCE and outcome.note == "not_meaningful_cash_flow_positive"
    assert [v.field for v in outcome.variances] == ["in_compliance"]


# ---- DSCR for venture borrowers (Task 3b) ----------------------------------------------------

FYE = date(2026, 12, 31)


def _dscr_cov():
    cov = _cov("coverage", {"numerator_base": "ebitda", "deductions": [], "denominator": ["cash_interest", "scheduled_principal"]},
               "1.20", "ratio", basis="ttm")
    return cov.model_copy(update={"rounding": cov.rounding.model_copy(update={"dp": 2})})


def _dscr_facts(interest="300000", principal="500000"):
    return provider_from_facts({
        ("is.vc_operating_loss", FYE, 12): D("-1000000"),
        ("is.vc_depreciation_amortization", FYE, 12): D("200000"),
        ("sup.cash_interest_paid", FYE, 12): D(interest),
        ("sup.scheduled_principal", FYE, 12): D(principal),
    })


def test_vc_dscr_negative_ebitda_is_a_real_breach():
    result = test_covenant(_dscr_cov(), FYE, _dscr_facts(), template_id="vc-1")
    assert result.errors == [] and result.value == D("-1.00") and result.passed is False


def test_vc_dscr_without_debt_service_cannot_be_tested():
    result = test_covenant(_dscr_cov(), FYE, _dscr_facts("0", "0"), template_id="vc-1")
    assert result.passed is None and [e.code for e in result.errors] == ["non_positive_denominator"]


def test_vc_dscr_uses_vc_ebitda_and_vc_capex():
    from app.calc.covenants import compile_covenant
    plain = compile_covenant(_dscr_cov(), template_id="vc-1")
    assert "vc_ebitda" in str(plain) and "'ebitda'" not in str(plain)
    cov = _dscr_cov().model_copy(update={"params": _dscr_cov().typed_params.model_copy(update={"deductions": ["unfinanced_capex"]})})
    assert "cf.vc_capex" in str(compile_covenant(cov, template_id="vc-1"))


def test_vc_adjusted_ebitda_is_not_defined():
    cov = _dscr_cov().model_copy(update={"params": _dscr_cov().typed_params.model_copy(update={"numerator_base": "adjusted_ebitda"})})
    result = test_covenant(cov, FYE, _dscr_facts(), template_id="vc-1")
    assert result.passed is None and result.errors[0].code == "undefined_for_template"
    assert "venture template" in result.errors[0].message


def test_ci_coverage_still_uses_ebitda():
    from app.calc.covenants import compile_covenant
    assert "vc_ebitda" not in str(compile_covenant(_dscr_cov()))


# ---- revenue_vs_plan basis follows the metric (terms validation) -----------------------------

def test_revenue_plan_needs_t3m_and_arr_plan_needs_point():
    import pytest
    from pydantic import ValidationError
    arr = {"metric": "arr", "plan": [{"period_end": OCT.isoformat(), "amount": "4800000"}]}
    revenue = _plan([date(2026, 8, 31), date(2026, 9, 30), OCT])
    assert _cov("revenue_vs_plan", revenue, "0.80", "ratio", basis="t3m").measurement.basis == "t3m"
    assert _cov("revenue_vs_plan", arr, "0.80", "ratio", basis="point").measurement.basis == "point"
    with pytest.raises(ValidationError, match="measured on basis 't3m'"):
        _cov("revenue_vs_plan", revenue, "0.80", "ratio", basis="point")
    with pytest.raises(ValidationError, match="measured on basis 'point'"):
        _cov("revenue_vs_plan", arr, "0.80", "ratio", basis="t3m")


# ---- test gaps (Phase 1 final review) --------------------------------------------------------

def _runway_provider(burn_t3m):
    """Unrestricted cash 4.6M; operating cash flow over Aug-Oct is -burn_t3m (no capex)."""
    return provider_from_facts({
        ("bs.cash_unrestricted", OCT, 10): D("4600000"),
        ("cf.vc_operating_cash_flow", OCT, 10): D("-1000000") - D(burn_t3m),
        ("cf.vc_operating_cash_flow", date(2026, 7, 31), 7): D("-1000000"),
        ("cf.vc_capex", OCT, 10): D("0"), ("cf.vc_capex", date(2026, 7, 31), 7): D("0"),
        ("cf.capitalised_software_spend", OCT, 10): D("0"),
        ("cf.capitalised_software_spend", date(2026, 7, 31), 7): D("0"),
    })


def test_rml_with_burn_exactly_zero_is_not_meaningful_and_never_divides():
    rml = compute_rml(OCT, _runway_provider("0"))
    assert rml.burn == D("0") and rml.not_meaningful is True and rml.value is None and rml.errors == []
    result = test_covenant(_cov("min_runway_months", {}, 9, "months", basis="t3m"), OCT, _runway_provider("0"))
    assert result.passed is True and result.value is None and result.avg_net_burn == D("0")
    assert result.note == "not_meaningful_cash_flow_positive"


def test_a_barely_positive_burn_is_measured():
    rml = compute_rml(OCT, _runway_provider("3"))  # 1 a month
    assert rml.not_meaningful is False and rml.value == D("4600000")


def test_t3m_in_the_second_month_of_the_year_uses_the_prior_year_end():
    from app.calc.periods import resolve_line
    key = "cf.vc_operating_cash_flow"
    feb = date(2026, 2, 28)
    facts = {(key, feb, 2): D("-1300"), (key, date(2025, 12, 31), 12): D("-7000"),
             (key, date(2025, 11, 30), 11): D("-6400")}
    res = resolve_line(key, "t3m", feb, provider_from_facts(facts))
    assert res.errors == [] and res.value == D("-1900")  # Dec 600 + Jan..Feb 1300: -(-7000 - -6400) - 1300


def test_t3m_with_a_non_december_fiscal_year_end():
    from app.calc.periods import resolve_line
    key = "cf.vc_operating_cash_flow"
    # fiscal year ends June 30; August is the second month of the year
    aug = date(2026, 8, 31)
    facts = {(key, aug, 2): D("-900"), (key, date(2026, 6, 30), 12): D("-5000"),
             (key, date(2026, 5, 31), 11): D("-4600")}
    res = resolve_line(key, "t3m", aug, provider_from_facts(facts), fye_month=6)
    assert res.errors == [] and res.value == D("-1300")  # Jun 400 + Jul..Aug 900
    # October is the fourth month: this year's October less July
    oct_ = date(2026, 10, 31)
    facts = {(key, oct_, 4): D("-2000"), (key, date(2026, 7, 31), 1): D("-500")}
    assert resolve_line(key, "t3m", oct_, provider_from_facts(facts), fye_month=6).value == D("-1500")
    # September is the third month: the year to date is the answer
    sep = date(2026, 9, 30)
    assert resolve_line(key, "t3m", sep, provider_from_facts({(key, sep, 3): D("-1100")}), fye_month=6).value == D("-1100")


def test_revenue_vs_plan_with_a_zero_plan_total_does_not_divide_or_pass():
    provider = provider_from_facts({
        ("is.subscription_revenue", OCT, 10): D("7700000"),
        ("is.subscription_revenue", date(2026, 7, 31), 7): D("5300000"),
        ("is.services_revenue", OCT, 10): D("0"), ("is.services_revenue", date(2026, 7, 31), 7): D("0"),
    })
    plan = {"metric": "revenue", "plan": [{"period_end": d.isoformat(), "amount": "0"}
                                          for d in (date(2026, 8, 31), date(2026, 9, 30), OCT)]}
    result = test_covenant(_cov("revenue_vs_plan", plan, "0.80", "ratio", basis="t3m"), OCT, provider)
    assert result.passed is None and result.value is None
    assert [e.code for e in result.errors] == ["non_positive_denominator"]


def test_arr_plan_path_compares_the_point_arr_with_the_months_plan():
    provider = provider_from_facts({("saas.arr", OCT, 10): D("4800000")})
    plan = {"metric": "arr", "plan": [{"period_end": OCT.isoformat(), "amount": "5000000"}]}
    cov = _cov("revenue_vs_plan", plan, "0.90", "ratio", basis="point")
    cov = cov.model_copy(update={"rounding": cov.rounding.model_copy(update={"dp": 2})})
    result = test_covenant(cov, OCT, provider)
    assert result.errors == [] and result.value == D("0.96") and result.passed is True
    # only the period end month counts: another month's plan figure is not asked for
    plan_missing = {"metric": "arr", "plan": [{"period_end": "2026-09-30", "amount": "5000000"}]}
    cannot = test_covenant(_cov("revenue_vs_plan", plan_missing, "0.90", "ratio", basis="point"), OCT, provider)
    assert cannot.passed is None and cannot.errors[0].code == "missing_parameter"


def test_a_certificate_that_prints_not_meaningful_against_a_finite_computed_runway_is_a_variance():
    result = CovenantTestResult("min_runway_months", OCT, passed=True, value=D("7.1"), threshold=D("6"))
    entry = {"value": None, "threshold": "6", "in_compliance": True, "not_meaningful": True}
    outcome = determine_outcome(result, entry, D("0.1"))
    assert outcome.outcome == COMPLIANT_VARIANCE
    assert [(v.field, v.computed, v.reported) for v in outcome.variances] == [("value", D("7.1"), None)]


def test_not_meaningful_on_both_sides_agrees_and_a_value_on_both_sides_is_unchanged():
    nm = CovenantTestResult("min_runway_months", OCT, passed=True, threshold=D("6"),
                            note="not_meaningful_cash_flow_positive")
    agree = determine_outcome(nm, {"value": None, "threshold": "6", "in_compliance": True, "not_meaningful": True}, D("0.1"))
    assert agree.outcome == COMPLIANT and agree.variances == []
    finite = CovenantTestResult("min_runway_months", OCT, passed=True, value=D("7.1"), threshold=D("6"))
    same = determine_outcome(finite, {"value": "7.1", "threshold": "6", "in_compliance": True}, D("0.1"))
    assert same.outcome == COMPLIANT


def test_a_certified_figure_against_a_not_meaningful_computed_runway_stays_ignored():
    # the opposite direction is the recorded design (test_not_meaningful_rml_ignores_certificate_value): the
    # certificate's figure is not a covenant input when the computed runway has no value
    nm = CovenantTestResult("min_runway_months", OCT, passed=True, threshold=D("6"),
                            note="not_meaningful_cash_flow_positive")
    assert determine_outcome(nm, {"value": "24.0", "threshold": "6", "in_compliance": True}, D("0.1")).variances == []
