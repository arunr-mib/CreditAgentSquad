from decimal import Decimal as D

import pytest
from app.calc import errors as E
from app.calc.template import (
    LINE_BY_KEY,
    LINES,
    TEMPLATE_ID,
    check_comparative,
    check_statement,
    compute_statement,
    line_info,
    stored_value,
)

# Fiscal year 2025, whole dollars. Hand-computed totals are in EXPECTED below.
IS_INPUTS = {
    "is.revenue": D("3900000"),
    "is.cogs": D("2360000"),
    "is.sga": D("800000"),
    "is.depreciation_amortization": D("160000"),
    "is.other_operating_expense": D("40000"),
    "is.nonrecurring_expense": D("200000"),
    "is.interest_expense": D("120000"),
    "is.other_income_net": D("0"),
    "is.income_tax_expense": D("70000"),
}
BS_INPUTS = {
    "bs.cash": D("150000"),
    "bs.accounts_receivable": D("650000"),
    "bs.inventory": D("520000"),
    "bs.other_current_assets": D("80000"),
    "bs.net_ppe": D("1250000"),
    "bs.intangibles": D("300000"),
    "bs.other_noncurrent_assets": D("0"),
    "bs.accounts_payable": D("320000"),
    "bs.accrued_liabilities": D("100000"),
    "bs.revolver": D("650000"),
    "bs.cpltd": D("100000"),
    "bs.other_current_liabilities": D("0"),
    "bs.long_term_debt": D("850000"),
    "bs.subordinated_debt": D("200000"),
    "bs.other_noncurrent_liabilities": D("0"),
    "bs.total_equity": D("730000"),
}
CF_INPUTS = {
    "cf.net_income": D("150000"),
    "cf.depreciation_amortization": D("160000"),
    "cf.change_in_working_capital": D("-20000"),
    "cf.other_operating": D("0"),
    "cf.capex": D("200000"),
    "cf.other_investing": D("-60000"),
    "cf.revolver_net": D("250000"),
    "cf.term_debt_proceeds": D("0"),
    "cf.term_debt_repayments": D("150000"),
    "cf.distributions": D("290000"),
    "cf.other_financing": D("10000"),
}
SUP_INPUTS = {
    "sup.cash_interest_paid": D("120000"),
    "sup.cash_taxes_paid": D("65000"),
    "sup.scheduled_principal": D("100000"),
    "sup.financed_capex": D("20000"),
}
EXPECTED = {
    "is.gross_profit": D("1540000"),  # 3,900,000 - 2,360,000
    "is.operating_income": D("340000"),  # 1,540,000 - 800,000 - 160,000 - 40,000 - 200,000
    "is.pretax_income": D("220000"),  # 340,000 - 120,000 + 0
    "is.net_income": D("150000"),  # 220,000 - 70,000
    "bs.total_current_assets": D("1400000"),  # 150 + 650 + 520 + 80 (thousands)
    "bs.total_assets": D("2950000"),  # 1,400 + 1,250 + 300 + 0
    "bs.total_current_liabilities": D("1170000"),  # 320 + 100 + 650 + 100 + 0
    "bs.total_liabilities": D("2220000"),  # 1,170 + 850 + 200 + 0
    "bs.total_liabilities_and_equity": D("2950000"),  # 2,220 + 730
    "cf.cfo": D("290000"),  # 150 + 160 - 20 + 0
    "cf.cfi": D("-260000"),  # -200 - 60
    "cf.cff": D("-180000"),  # 250 + 0 - 150 - 290 + 10
    "cf.net_change_in_cash": D("-150000"),  # 290 - 260 - 180
}
PRIOR_FYE_CASH = D("300000")  # 150,000 - 300,000 = -150,000


def full_inputs():
    return {**IS_INPUTS, **BS_INPUTS, **CF_INPUTS, **SUP_INPUTS}


def with_stated(inputs):
    out = dict(inputs)
    for key, value in EXPECTED.items():
        out[f"stated.{key}"] = value
    return out


def codes(errors):
    return [e.code for e in errors]


# ---- template data -----------------------------------------------------------------


def test_template_identity_and_line_count():
    assert TEMPLATE_ID == "ci-1"
    by_statement = {}
    for line in LINES:
        by_statement.setdefault(line.statement, []).append(line.key)
    assert len(by_statement["is"]) == 13
    assert len(by_statement["bs"]) == 21
    assert len(by_statement["cf"]) == 15
    assert len(by_statement["sup"]) == 4
    assert len(LINE_BY_KEY) == 53


def test_computed_lines_are_exactly_the_spec_ones():
    computed = {line.key for line in LINES if line.computed}
    assert computed == set(EXPECTED)
    for line in LINES:
        assert bool(line.formula) == line.computed
    assert LINE_BY_KEY["bs.total_equity"].computed is False  # input, as stated


def test_presentation_signs_and_flow_flags():
    negative = {line.key for line in LINES if line.presentation_sign == -1}
    assert negative == {"cf.capex", "cf.term_debt_repayments", "cf.distributions"}
    assert all(line.presentation_sign in (1, -1) for line in LINES)
    assert all(line.flow for line in LINES if line.statement in ("is", "cf", "sup"))
    assert not any(line.flow for line in LINES if line.statement == "bs")
    assert LINE_BY_KEY["is.revenue"].label == "Net revenue"


def test_line_info_knows_template_lines_and_availability_only():
    assert line_info("is.revenue") is LINE_BY_KEY["is.revenue"]
    assert line_info("bb.availability").flow is False
    assert line_info("is.ebitda") is None
    assert line_info("stated.bs.total_assets") is None


def test_stored_value_applies_presentation_sign():
    # Capex printed as (200,000) parses to -200000 and is stored positive.
    assert stored_value("cf.capex", D("-200000")) == D("200000")
    assert stored_value("is.cogs", D("2360000")) == D("2360000")
    assert stored_value("is.other_income_net", D("-5000")) == D("-5000")
    with pytest.raises(KeyError):
        stored_value("is.nope", D("1"))


# ---- compute_statement ---------------------------------------------------------------


def test_compute_statement_full_package():
    result = compute_statement(full_inputs())
    assert result.errors == []
    assert result.computed == EXPECTED
    assert result.values["is.revenue"] == D("3900000")
    assert result.values["bs.total_assets"] == D("2950000")


def test_compute_statement_one_statement_only():
    result = compute_statement(IS_INPUTS, statements=["is"])
    assert result.errors == []
    assert result.computed == {k: v for k, v in EXPECTED.items() if k.startswith("is.")}


def test_missing_input_is_an_error_naming_the_line_never_zero():
    inputs = full_inputs()
    del inputs["is.sga"]
    result = compute_statement(inputs)
    missing = [e for e in result.errors if e.code == E.MISSING_INPUT]
    assert [e.key for e in missing] == ["is.sga"]
    assert "is.gross_profit" in result.computed
    for dependent in ("is.operating_income", "is.pretax_income", "is.net_income"):
        assert dependent not in result.computed
    assert result.computed["bs.total_assets"] == D("2950000")


def test_unknown_key_computed_key_and_float_are_refused():
    inputs = full_inputs()
    inputs["is.ebitda"] = D("1")
    inputs["bs.total_assets"] = D("2950000")
    inputs["is.revenue"] = 3900000.0
    result = compute_statement(inputs)
    assert E.UNKNOWN_KEY in codes(result.errors)
    assert E.COMPUTED_LINE_SUPPLIED in codes(result.errors)
    assert E.FLOAT_NOT_ALLOWED in codes(result.errors)
    assert "is.gross_profit" not in result.computed


def test_absent_lines_compute_as_zero():
    inputs = full_inputs()
    del inputs["bs.other_noncurrent_assets"]
    result = compute_statement(inputs, absent=["bs.other_noncurrent_assets"])
    assert result.errors == []
    assert result.values["bs.other_noncurrent_assets"] == D("0")
    assert result.computed["bs.total_assets"] == D("2950000")


def test_absent_and_supplied_conflict_and_absent_computed_line_are_errors():
    result = compute_statement(full_inputs(), absent=["bs.cash", "bs.total_assets"])
    assert codes(result.errors).count(E.INVALID_VALUE) == 2


# ---- checks ----------------------------------------------------------------------------


def checks_by(report, check):
    return {c.key: c for c in report.checks if c.check == check}


def test_all_checks_pass_on_a_clean_package():
    report = check_statement(with_stated(full_inputs()), scale=1, prior_fye_cash=PRIOR_FYE_CASH)
    assert report.errors == []
    assert report.ok
    assert len(checks_by(report, "footing")) == 13
    assert {c.status for c in report.checks} == {"pass"}
    roll = checks_by(report, "cash_roll")["cf.net_change_in_cash"]
    assert roll.actual == D("-150000") and roll.expected == D("-150000")
    assert roll.tolerance == D("2")


def test_footing_within_and_outside_tolerance():
    # bs.total_current_assets has four components: tolerance is 4 dollars at scale 1.
    inputs = with_stated(full_inputs())
    inputs["stated.bs.total_current_assets"] = D("1400004")
    report = check_statement(inputs, scale=1, prior_fye_cash=PRIOR_FYE_CASH)
    footing = checks_by(report, "footing")["bs.total_current_assets"]
    assert footing.status == "pass" and footing.tolerance == D("4") and footing.difference == D("-4")

    inputs["stated.bs.total_current_assets"] = D("1400005")
    report = check_statement(inputs, scale=1, prior_fye_cash=PRIOR_FYE_CASH)
    footing = checks_by(report, "footing")["bs.total_current_assets"]
    assert footing.status == "fail"
    failed = [e for e in report.errors if e.code == E.DOES_NOT_FOOT]
    assert [e.key for e in failed] == ["bs.total_current_assets"]
    assert not report.ok


def test_footing_tolerance_scales_with_reported_scale():
    inputs = with_stated(full_inputs())
    inputs["stated.is.gross_profit"] = D("1542000")  # two components x 1000 = 2000
    report = check_statement(inputs, scale=1000, prior_fye_cash=PRIOR_FYE_CASH)
    assert checks_by(report, "footing")["is.gross_profit"].status == "pass"
    inputs["stated.is.gross_profit"] = D("1542001")
    report = check_statement(inputs, scale=1000, prior_fye_cash=PRIOR_FYE_CASH)
    assert checks_by(report, "footing")["is.gross_profit"].status == "fail"


def test_missing_stated_total_is_not_checked_not_passed():
    report = check_statement(full_inputs(), scale=1, prior_fye_cash=PRIOR_FYE_CASH)
    assert {c.status for c in checks_by(report, "footing").values()} == {"not_checked"}
    assert report.errors == []


def test_balance_sheet_must_balance():
    inputs = with_stated(full_inputs())
    inputs["bs.total_equity"] = D("730002")
    inputs["stated.bs.total_liabilities_and_equity"] = D("2950002")
    report = check_statement(inputs, scale=1, prior_fye_cash=PRIOR_FYE_CASH)
    balance = checks_by(report, "balance")["bs.total_assets"]
    assert balance.status == "fail" and balance.tolerance == D("1")
    assert balance.actual == D("2950000") and balance.expected == D("2950002")
    assert E.DOES_NOT_BALANCE in codes(report.errors)


def test_cash_flow_ties_to_income_statement():
    inputs = with_stated(full_inputs())
    inputs["cf.net_income"] = D("150900")
    inputs["cf.change_in_working_capital"] = D("-20900")  # keeps cfo footing
    report = check_statement(inputs, scale=1, prior_fye_cash=PRIOR_FYE_CASH)
    ties = checks_by(report, "tie")
    assert ties["cf.net_income"].status == "fail"
    assert ties["cf.depreciation_amortization"].status == "pass"
    assert [e.key for e in report.errors if e.code == E.DOES_NOT_TIE] == ["cf.net_income"]


def test_cash_roll_fails_and_is_not_checked_without_prior_year_end_cash():
    inputs = with_stated(full_inputs())
    report = check_statement(inputs, scale=1, prior_fye_cash=D("300003"))
    roll = checks_by(report, "cash_roll")["cf.net_change_in_cash"]
    assert roll.status == "fail" and roll.expected == D("-150003")
    assert E.CASH_ROLL_MISMATCH in codes(report.errors)

    report = check_statement(inputs, scale=1, prior_fye_cash=None)
    assert checks_by(report, "cash_roll")["cf.net_change_in_cash"].status == "not_checked"
    assert report.errors == []


def test_check_statement_needs_a_valid_scale():
    with pytest.raises(ValueError):
        check_statement(full_inputs(), scale=10, prior_fye_cash=None)
    with pytest.raises(TypeError):
        check_statement(full_inputs(), scale=1.0, prior_fye_cash=None)


# ---- absent lines ------------------------------------------------------------------------

ABSENT = ["bs.other_noncurrent_assets", "bs.other_current_liabilities", "is.other_income_net"]


def inputs_with_absent():
    inputs = with_stated(full_inputs())
    for key in ABSENT:
        del inputs[key]
    return inputs


def test_absent_line_allowed_when_section_foots():
    report = check_statement(inputs_with_absent(), absent=ABSENT, scale=1, prior_fye_cash=PRIOR_FYE_CASH)
    assert report.errors == []
    assert all(report.values[key] == D("0") for key in ABSENT)
    assert report.computed == EXPECTED


def test_absent_line_refused_when_section_does_not_foot():
    inputs = inputs_with_absent()
    # The statement really had 40,000 of other assets that was not captured.
    inputs["stated.bs.total_assets"] = D("2990000")
    report = check_statement(inputs, absent=ABSENT, scale=1, prior_fye_cash=PRIOR_FYE_CASH)
    unverified = {e.key for e in report.errors if e.code == E.ABSENT_NOT_VERIFIED}
    # Both absent balance sheet lines fall with their section; the income statement one stands.
    assert unverified == {"bs.other_noncurrent_assets", "bs.other_current_liabilities"}
    assert E.DOES_NOT_FOOT in codes(report.errors)


def test_absent_line_refused_when_no_stated_total_covers_it():
    inputs = full_inputs()
    del inputs["bs.other_noncurrent_assets"]
    report = check_statement(inputs, absent=["bs.other_noncurrent_assets"], scale=1, prior_fye_cash=None)
    assert [e.key for e in report.errors if e.code == E.ABSENT_NOT_VERIFIED] == ["bs.other_noncurrent_assets"]


def test_absent_supplemental_line_cannot_be_verified():
    inputs = with_stated(full_inputs())
    del inputs["sup.financed_capex"]
    report = check_statement(inputs, absent=["sup.financed_capex"], scale=1, prior_fye_cash=PRIOR_FYE_CASH)
    assert [e.key for e in report.errors if e.code == E.ABSENT_NOT_VERIFIED] == ["sup.financed_capex"]


def test_not_marked_absent_is_still_missing():
    inputs = inputs_with_absent()
    report = check_statement(inputs, absent=ABSENT[:2], scale=1, prior_fye_cash=PRIOR_FYE_CASH)
    assert [e.key for e in report.errors if e.code == E.MISSING_INPUT] == ["is.other_income_net"]


# ---- comparative column ---------------------------------------------------------------------


def test_comparative_matches_confirmed_spread():
    confirmed = {"is.revenue": D("4000000"), "is.cogs": D("2400000"), "bs.cash": D("300000")}
    comparative = {"is.revenue": D("4000000"), "is.cogs": D("2400001"), "bs.cash": D("300000")}
    checks = check_comparative(comparative, confirmed, scale=1)
    assert [c.status for c in checks] == ["pass", "pass", "pass"]
    assert all(c.check == "restatement" for c in checks)


def test_comparative_restatement_is_flagged():
    confirmed = {"is.revenue": D("4000000"), "is.cogs": D("2400000")}
    comparative = {"is.revenue": D("3950000"), "is.cogs": D("2400000"), "is.sga": D("800000")}
    checks = {c.key: c for c in check_comparative(comparative, confirmed, scale=1)}
    assert checks["is.revenue"].status == "fail"
    assert checks["is.revenue"].actual == D("3950000") and checks["is.revenue"].expected == D("4000000")
    assert checks["is.revenue"].difference == D("-50000")
    assert checks["is.cogs"].status == "pass"
    assert checks["is.sga"].status == "not_checked"  # nothing confirmed to compare with


def test_comparative_tolerance_uses_scale():
    confirmed = {"is.revenue": D("4000400")}
    assert check_comparative({"is.revenue": D("4000000")}, confirmed, scale=1000)[0].status == "pass"
    assert check_comparative({"is.revenue": D("3999000")}, confirmed, scale=1000)[0].status == "fail"
