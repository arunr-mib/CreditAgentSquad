from datetime import date
from decimal import Decimal as D

import pytest
from app.calc import covenants as cov
from app.calc import errors as E
from app.calc.covenants import (
    CertificateEntry,
    build_definitions,
    compile_covenant,
    determine_outcome,
    is_test_date,
)
from app.calc.periods import provider_from_facts
from app.calc.terms import Covenant, Definition

FYE = date(2025, 12, 31)

# Fiscal year 2025 (TTM at the fiscal year end is the fiscal year).
FY2025 = {
    "is.net_income": "150000", "is.interest_expense": "120000", "is.income_tax_expense": "70000",
    "is.depreciation_amortization": "160000", "is.nonrecurring_expense": "200000",
    "bs.cash": "150000", "bs.intangibles": "300000", "bs.revolver": "650000", "bs.cpltd": "100000",
    "bs.long_term_debt": "850000", "bs.subordinated_debt": "200000",
    "bs.total_current_assets": "1400000", "bs.total_current_liabilities": "1170000",
    "bs.total_liabilities": "2220000", "bs.total_equity": "730000",
    "cf.capex": "200000", "cf.distributions": "290000",
    "sup.cash_interest_paid": "120000", "sup.cash_taxes_paid": "65000",
    "sup.scheduled_principal": "100000", "sup.financed_capex": "20000",
    "bb.availability": "400000",
}
FACTS = {(k, FYE, 12): D(v) for k, v in FY2025.items()}
PROVIDER = provider_from_facts(FACTS)
# EBITDA = 150,000 + 120,000 + 70,000 + 160,000 = 500,000


TEN_PCT_OF_EBITDA = {"type": "pct_of", "value": "0.10", "of": "ebitda"}


def definitions(cap="ten_pct", omit_cap=False):
    addback = {"name": "restructuring", "source_key": "is.nonrecurring_expense"}
    if not omit_cap:
        addback["cap"] = dict(TEN_PCT_OF_EBITDA) if cap == "ten_pct" else cap
    return {"ebitda": Definition.model_validate({"base": "ebitda", "addbacks": [addback]})}


def covenant(archetype, params, operator=">=", threshold="1.20", steps=(), basis="ttm", unit="ratio", dp=2,
             frequency="quarterly"):
    return Covenant.model_validate({
        "id": "c1", "name": "Covenant", "archetype": archetype, "params": params,
        "test": {"operator": operator, "threshold": threshold, "steps": list(steps), "unit": unit},
        "measurement": {"basis": basis, "frequency": frequency},
        "rounding": {"dp": dp, "mode": "half_up"}, "citations": [],
    })


COVERAGE = {"numerator_base": "adjusted_ebitda", "deductions": ["unfinanced_capex", "cash_taxes"],
            "denominator": ["cash_interest", "scheduled_principal"]}


def run(c, defs=None, provider=PROVIDER, **kw):
    return cov.test_covenant(c, FYE, provider, definitions() if defs is None else defs, **kw)


# ---- coverage with add-backs --------------------------------------------------------------


def test_coverage_with_percent_capped_addback():
    result = run(covenant("coverage", COVERAGE))
    # cap = 10% x 500,000 = 50,000 of the 200,000 raw; adjusted EBITDA = 550,000
    # (550,000 - (200,000 - 20,000) - 65,000) / (120,000 + 100,000) = 305,000 / 220,000 = 1.38636
    assert result.errors == []
    assert str(result.value) == "1.39" and result.threshold == D("1.20") and result.passed is True
    assert result.headroom == D("0.19") and result.headroom_pct == D("0.1583")  # 0.19 / 1.20
    (ab,) = result.trace.addbacks
    assert (ab.name, ab.raw, ab.cap_limit, ab.applied, ab.capped) == (
        "restructuring", D("200000"), D("50000"), D("50000"), True)
    assert abs(result.raw_value - D("1.386363636")) < D("1e-9")
    assert result.covenant_id == "c1" and result.period_end == FYE and result.operator == ">="


def test_cap_null_and_absent_are_uncapped_but_cap_zero_flips_the_test():
    for defs in (definitions(cap=None), definitions(omit_cap=True)):
        result = run(covenant("coverage", COVERAGE), defs)
        # (700,000 - 180,000 - 65,000) / 220,000 = 2.06818
        assert str(result.value) == "2.07" and result.passed is True
        assert result.trace.addbacks[0].cap_limit is None and result.trace.addbacks[0].applied == D("200000")
    zero = run(covenant("coverage", COVERAGE), definitions(cap={"type": "amount", "value": "0"}))
    # (500,000 - 180,000 - 65,000) / 220,000 = 1.15909
    assert str(zero.value) == "1.16" and zero.passed is False
    assert zero.headroom == D("-0.04") and zero.headroom_pct == D("-0.0333")


def test_amount_cap():
    result = run(covenant("coverage", COVERAGE), definitions(cap={"type": "amount", "value": "100000"}))
    assert str(result.value) == "1.61"  # (600,000 - 245,000) / 220,000 = 1.61364


def test_coverage_parameter_variants():
    all_deductions = dict(COVERAGE, deductions=["unfinanced_capex", "cash_taxes", "distributions"])
    assert str(run(covenant("coverage", all_deductions)).value) == "0.07"  # 15,000 / 220,000 = 0.06818
    interest_only = dict(COVERAGE, denominator=["interest_expense"])
    assert str(run(covenant("coverage", interest_only)).value) == "2.54"  # 305,000 / 120,000 = 2.54167
    plain = dict(COVERAGE, numerator_base="ebitda")
    result = run(covenant("coverage", plain))
    assert str(result.value) == "1.16" and result.trace.addbacks == []  # 255,000 / 220,000
    none = dict(COVERAGE, deductions=[])
    assert str(run(covenant("coverage", none)).value) == "2.50"  # 550,000 / 220,000


def test_coverage_trace_names_every_input():
    result = run(covenant("coverage", COVERAGE))
    assert [i.key for i in result.trace.inputs] == [
        "is.net_income", "is.interest_expense", "is.income_tax_expense", "is.depreciation_amortization",
        "is.nonrecurring_expense", "cf.capex", "sup.financed_capex", "sup.cash_taxes_paid",
        "sup.cash_interest_paid", "sup.scheduled_principal",
    ]
    assert all(i.period_end == FYE and i.months == 12 for i in result.trace.inputs)


def test_adjusted_ebitda_without_a_definition_cannot_be_tested():
    result = run(covenant("coverage", COVERAGE), {})
    assert result.value is None and result.passed is None
    assert [e.code for e in result.errors] == [E.UNKNOWN_DEFINITION]


# ---- leverage and the "<=" direction ---------------------------------------------------------

LEVERAGE = {"debt": "total_debt", "ebitda": "adjusted_ebitda"}


def test_leverage_maximum_passes_with_positive_headroom():
    result = run(covenant("leverage", LEVERAGE, operator="<=", threshold="3.50"))
    # 1,800,000 / 550,000 = 3.27273
    assert str(result.value) == "3.27" and result.passed is True
    assert result.headroom == D("0.23") and result.headroom_pct == D("0.0657")  # 0.23 / 3.50


def test_leverage_maximum_fails_with_negative_headroom():
    result = run(covenant("leverage", LEVERAGE, operator="<=", threshold="3.00"))
    assert result.passed is False and result.headroom == D("-0.27") and result.headroom_pct == D("-0.0900")


def test_senior_leverage_on_plain_ebitda():
    result = run(covenant("leverage", {"debt": "senior_debt", "ebitda": "ebitda"}, operator="<=", threshold="3.50"))
    assert str(result.value) == "3.20"  # 1,600,000 / 500,000


def test_strict_operators_fail_at_the_threshold():
    params = {"debt": "senior_debt", "ebitda": "ebitda"}
    assert run(covenant("leverage", params, operator="<=", threshold="3.20")).passed is True
    assert run(covenant("leverage", params, operator="<", threshold="3.20")).passed is False
    assert run(covenant("leverage", params, operator=">=", threshold="3.20")).passed is True
    assert run(covenant("leverage", params, operator=">", threshold="3.20")).passed is False
    assert run(covenant("leverage", params, operator=">", threshold="3.19")).headroom == D("0.01")
    assert run(covenant("leverage", params, operator="<", threshold="3.21")).headroom == D("0.01")


# ---- step thresholds ----------------------------------------------------------------------------


@pytest.mark.parametrize("step_from, threshold, passed", [
    ("2025-12-30", "1.45", False),  # stepped the day before the period end
    ("2025-12-31", "1.45", False),  # steps on the period end: the step governs
    ("2026-01-01", "1.20", True),  # steps the day after: the base threshold still governs
])
def test_step_threshold_on_and_around_its_effective_date(step_from, threshold, passed):
    c = covenant("coverage", COVERAGE, steps=[{"from": step_from, "value": "1.45"}])
    result = run(c)
    assert result.threshold == D(threshold) and result.passed is passed and str(result.value) == "1.39"


# ---- the other archetypes -------------------------------------------------------------------------


def test_current_ratio_compares_the_rounded_value():
    result = run(covenant("current_ratio", {}, basis="point"))
    # 1,400,000 / 1,170,000 = 1.19658 rounds to 1.20, which meets a 1.20 minimum
    assert str(result.value) == "1.20" and result.passed is True
    assert result.headroom == D("0.00") and result.headroom_pct == D("0.0000")


def test_min_tangible_net_worth_without_step_up():
    c = covenant("min_tangible_net_worth", {"step_up_pct_of_net_income": None}, threshold="400000",
                 basis="point", unit="usd", dp=0)
    result = run(c)
    assert result.value == D("430000") and result.threshold == D("400000") and result.passed is True
    assert result.headroom == D("30000") and result.headroom_pct == D("0.0750")


def test_min_tangible_net_worth_steps_up_with_positive_net_income():
    c = covenant("min_tangible_net_worth", {"step_up_pct_of_net_income": "0.50"}, threshold="400000",
                 basis="point", unit="usd", dp=0)
    result = run(c, step_up_from=date(2024, 12, 31))
    # 400,000 + 50% x 150,000 (fiscal 2025) = 475,000
    assert result.threshold == D("475000") and result.passed is False and result.headroom == D("-45000")
    assert ("is.net_income", FYE, 12) in [(i.key, i.period_end, i.months) for i in result.trace.inputs]

    # A loss year adds nothing; it does not reduce the threshold.
    facts = dict(FACTS)
    facts[("is.net_income", FYE, 12)] = D("-80000")
    result = run(c, provider=provider_from_facts(facts), step_up_from=date(2024, 12, 31))
    assert result.threshold == D("400000") and result.passed is True

    # A fiscal year end on the start date itself is not after it.
    assert run(c, step_up_from=FYE).threshold == D("400000")


def test_min_tangible_net_worth_step_up_refusals():
    c = covenant("min_tangible_net_worth", {"step_up_pct_of_net_income": "0.50"}, threshold="400000",
                 basis="point", unit="usd", dp=0)
    no_start = run(c)
    assert no_start.passed is None and [e.code for e in no_start.errors] == [E.MISSING_PARAMETER]
    missing_year = run(c, step_up_from=date(2023, 12, 31))
    assert missing_year.passed is None
    assert [(e.code, e.key, e.period_end, e.months) for e in missing_year.errors] == [
        (E.MISSING_INPUT, "is.net_income", date(2024, 12, 31), 12)]


def test_min_liquidity_with_and_without_availability():
    cash = covenant("min_liquidity", {"include_availability": False}, threshold="100000", basis="point",
                    unit="usd", dp=0)
    assert run(cash).value == D("150000")
    both = covenant("min_liquidity", {"include_availability": True}, threshold="500000", basis="point",
                    unit="usd", dp=0)
    result = run(both)
    assert result.value == D("550000") and result.passed is True
    assert [i.key for i in result.trace.inputs] == ["bs.cash", "bb.availability"]


def test_max_capex_and_debt_to_tnw():
    capex = covenant("max_capex", {}, operator="<=", threshold="250000", basis="fy", unit="usd", dp=0)
    result = run(capex)
    assert result.value == D("200000") and result.passed is True and result.headroom == D("50000")
    dtnw = covenant("debt_to_tnw", {}, operator="<=", threshold="4.00", basis="point")
    result = run(dtnw)
    assert str(result.value) == "5.16" and result.passed is False  # 2,220,000 / 430,000 = 5.16279


def test_custom_expression_is_evaluated_as_written():
    expression = {"op": "div", "num": {"op": "named", "name": "adjusted_ebitda"},
                  "den": {"op": "line", "key": "is.interest_expense", "period": "ttm"}}
    result = run(covenant("custom", {"expression": expression}, threshold="3.00"))
    assert str(result.value) == "4.58" and result.passed is True  # 550,000 / 120,000 = 4.58333


def test_compile_covenant_returns_the_expression_tree():
    tree = compile_covenant(covenant("leverage", LEVERAGE, operator="<="))
    assert tree == {"op": "div", "num": {"op": "named", "name": "total_debt"},
                    "den": {"op": "named", "name": "adjusted_ebitda"}}
    defs = build_definitions(definitions())
    assert defs["adjusted_ebitda"]["args"][1] == {
        "op": "addback", "name": "restructuring",
        "source": {"op": "line", "key": "is.nonrecurring_expense", "period": "ttm"},
        "cap": {"type": "pct_of", "value": "0.10", "of": {"op": "named", "name": "ebitda"}},
    }
    assert "ebitda" in defs and "total_debt" in defs


# ---- refusals ------------------------------------------------------------------------------------


def test_missing_input_cannot_be_tested_and_names_the_line():
    facts = dict(FACTS)
    del facts[("sup.cash_taxes_paid", FYE, 12)]
    result = run(covenant("coverage", COVERAGE), provider=provider_from_facts(facts))
    assert result.value is None and result.passed is None and result.headroom is None
    assert result.threshold == D("1.20")
    assert [(e.code, e.key, e.period_end, e.months) for e in result.errors] == [
        (E.MISSING_INPUT, "sup.cash_taxes_paid", FYE, 12)]


def test_non_positive_denominator_cannot_be_tested():
    facts = dict(FACTS)
    facts[("is.net_income", FYE, 12)] = D("-400000")  # EBITDA = -50,000
    result = run(covenant("leverage", {"debt": "total_debt", "ebitda": "ebitda"}, operator="<="),
                 provider=provider_from_facts(facts))
    assert result.passed is None and [e.code for e in result.errors] == [E.NON_POSITIVE_DENOMINATOR]


def test_invalid_covenant_mapping_is_an_error_not_an_exception():
    result = cov.test_covenant({"id": "x", "archetype": "coverage"}, FYE, PROVIDER, {})
    assert result.passed is None and [e.code for e in result.errors] == [E.INVALID_TERMS]
    assert result.covenant_id == "x"


def test_headroom_percent_is_null_for_a_zero_threshold():
    c = covenant("min_liquidity", {"include_availability": False}, threshold="0", basis="point", unit="usd", dp=0)
    result = run(c)
    assert result.passed is True and result.headroom == D("150000") and result.headroom_pct is None


# ---- when a covenant is tested ------------------------------------------------------------------


def test_is_test_date_follows_frequency():
    quarterly = covenant("coverage", COVERAGE)
    annual = covenant("coverage", COVERAGE, frequency="annual")
    monthly = covenant("coverage", COVERAGE, frequency="monthly")
    assert is_test_date(quarterly, date(2025, 6, 30)) and not is_test_date(quarterly, date(2025, 5, 31))
    assert is_test_date(annual, date(2025, 12, 31)) and not is_test_date(annual, date(2025, 6, 30))
    assert is_test_date(annual, date(2025, 6, 30), fye_month=6)
    assert is_test_date(quarterly, date(2025, 9, 30), fye_month=6)
    assert not is_test_date(quarterly, date(2025, 10, 31), fye_month=6)
    assert is_test_date(monthly, date(2025, 5, 31))


# ---- outcomes ---------------------------------------------------------------------------------------

TOL = D("0.01")


def passing():
    return run(covenant("coverage", COVERAGE))  # 1.39 against 1.20


def failing():
    return run(covenant("coverage", COVERAGE, threshold="1.50"))  # 1.39 against 1.50


def test_compliant_when_pass_agrees_with_certificate():
    out = determine_outcome(passing(), CertificateEntry(D("1.39"), D("1.20"), True), TOL)
    assert out.outcome == "compliant" and out.variances == [] and out.certificate_compared is True


def test_tolerance_boundary():
    at = determine_outcome(passing(), CertificateEntry(D("1.40"), D("1.20"), True), TOL)
    assert at.outcome == "compliant"
    beyond = determine_outcome(passing(), CertificateEntry(D("1.41"), D("1.20"), True), TOL)
    assert beyond.outcome == "compliant_variance"
    (v,) = beyond.variances
    assert (v.field, v.computed, v.reported) == ("value", D("1.39"), D("1.41"))


def test_compliant_variance_for_threshold_or_compliance_flag_differences():
    threshold = determine_outcome(passing(), CertificateEntry(D("1.39"), D("1.15"), True), TOL)
    assert threshold.outcome == "compliant_variance" and threshold.variances[0].field == "threshold"
    flag = determine_outcome(passing(), CertificateEntry(D("1.39"), D("1.20"), False), TOL)
    assert flag.outcome == "compliant_variance" and flag.variances[0].field == "in_compliance"


def test_breach_and_breach_reported_compliant():
    assert determine_outcome(failing(), CertificateEntry(D("1.39"), D("1.50"), False), TOL).outcome == "breach"
    assert determine_outcome(failing(), None, TOL).outcome == "breach"
    hidden = determine_outcome(failing(), CertificateEntry(D("2.07"), D("1.50"), True), TOL)
    assert hidden.outcome == "breach_reported_compliant"
    assert {v.field for v in hidden.variances} == {"value", "in_compliance"}


def test_cannot_test_names_the_missing_item():
    facts = dict(FACTS)
    del facts[("cf.capex", FYE, 12)]
    result = run(covenant("coverage", COVERAGE), provider=provider_from_facts(facts))
    out = determine_outcome(result, CertificateEntry(D("1.39"), D("1.20"), True), TOL)
    assert out.outcome == "cannot_test"
    assert [(e.code, e.key) for e in out.errors] == [(E.MISSING_INPUT, "cf.capex")]


def test_no_terms_in_force_is_cannot_test():
    error = E.CalcError(E.NO_TERMS_IN_FORCE, "no approved terms", period_end=FYE)
    out = determine_outcome(cov.untested("fccr", FYE, [error]), None, TOL)
    assert out.outcome == "cannot_test" and out.errors[0].code == E.NO_TERMS_IN_FORCE


def test_no_certificate_entry_is_compliant_but_marked_not_compared():
    out = determine_outcome(passing(), None, TOL)
    assert out.outcome == "compliant" and out.certificate_compared is False


def test_certificate_entry_from_mapping_is_strict():
    entry = CertificateEntry.from_mapping({"value": "1.39", "threshold": "1.20", "in_compliance": True})
    assert entry == CertificateEntry(D("1.39"), D("1.20"), True)
    assert determine_outcome(passing(), {"value": "1.39", "threshold": "1.20", "in_compliance": True}, TOL).outcome == "compliant"
    with pytest.raises(TypeError):
        CertificateEntry.from_mapping({"value": 1.39, "threshold": "1.20", "in_compliance": True})
    with pytest.raises(ValueError):
        CertificateEntry.from_mapping({"value": "1.39", "threshold": "1.20", "in_compliance": True, "x": 1})
    with pytest.raises(TypeError):
        CertificateEntry.from_mapping({"value": "1.39", "threshold": "1.20", "in_compliance": "yes"})
    with pytest.raises(TypeError):
        determine_outcome(passing(), None, 0.01)
