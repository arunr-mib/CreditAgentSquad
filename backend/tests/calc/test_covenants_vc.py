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


def _dataflake():
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
    result = test_covenant(_cov("min_unrestricted_cash", {}, 5000000, "usd"), OCT, _dataflake())
    assert result.value == D("4600000") and result.passed is False


def test_rml_is_cash_over_average_three_month_burn():
    rml = compute_rml(OCT, _dataflake())
    assert rml.burn == D("650000") and rml.value.quantize(D("0.1")) == D("7.1") and not rml.not_meaningful


def test_rml_covenant_breach_below_threshold():
    result = test_covenant(_cov("min_runway_months", {}, 9, "months", basis="t3m"), OCT, _dataflake())
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
