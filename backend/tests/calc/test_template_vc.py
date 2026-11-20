import re
from decimal import Decimal as D
from pathlib import Path

import app.calc
import pytest
from app.calc import errors as E
from app.calc.template import (
    LINES,
    TEMPLATES,
    TemplateLine,
    check_statement,
    compute_statement,
    in_template,
    line_info,
    template_lines,
)

VC_KEYS = {
    "is.subscription_revenue", "is.services_revenue", "is.total_revenue", "is.cost_of_revenue",
    "is.vc_gross_profit", "is.rnd", "is.sales_marketing", "is.gna", "is.vc_operating_loss",
    "is.vc_interest", "is.vc_other_income", "is.vc_net_loss",
    "bs.cash_unrestricted", "bs.cash_restricted", "bs.vc_total_cash", "bs.short_term_investments",
    "bs.capitalised_software", "bs.deferred_revenue_current", "bs.deferred_revenue_noncurrent",
    "bs.venture_debt_current", "bs.venture_debt_noncurrent", "bs.convertible_notes", "bs.safes",
    "bs.preferred_equity", "bs.common_equity",
    "cf.vc_operating_cash_flow", "cf.vc_capex", "cf.capitalised_software_spend", "cf.equity_raised",
    "cf.debt_raised", "cf.vc_net_change_in_cash",
    "saas.mrr", "saas.arr", "saas.customers",
}


def test_both_templates_registered():
    assert set(TEMPLATES) == {"ci-1", "vc-1"}
    assert VC_KEYS <= {line.key for line in template_lines("vc-1")}


def test_lines_alias_is_the_ci_template():
    assert LINES is TEMPLATES["ci-1"]


def test_unknown_template_is_an_error():
    with pytest.raises(ValueError):
        template_lines("xx-9")


def test_template_membership_is_separate():
    # Review focus 3: a ci-1 borrower must not accept vc-1 lines, and vice versa
    assert in_template("bs.cash", "ci-1") and not in_template("bs.cash", "vc-1")
    assert in_template("bs.cash_unrestricted", "vc-1") and not in_template("bs.cash_unrestricted", "ci-1")


def test_shared_keys_have_identical_definitions():
    ci = {line.key: line for line in template_lines("ci-1")}
    vc = {line.key: line for line in template_lines("vc-1")}
    for key in ci.keys() & vc.keys():
        assert ci[key] == vc[key], key


def test_line_info_finds_keys_in_either_template():
    assert line_info("is.revenue").label == "Net revenue"
    assert line_info("bs.cash_unrestricted").flow is False
    assert line_info("saas.arr").flow is False  # ARR is a point-in-time run rate
    assert line_info("cf.vc_capex").flow is True


def _vc_balance_absent(present):
    return [
        line.key for line in template_lines("vc-1")
        if line.key.startswith("bs.") and not line.computed and line.key not in present
    ]


def test_vc_total_cash_is_unrestricted_plus_restricted():
    present = ("bs.cash_unrestricted", "bs.cash_restricted")
    result = compute_statement(
        {"bs.cash_unrestricted": D("4600000"), "bs.cash_restricted": D("700000")},
        statements=["bs"], template_id="vc-1", absent=_vc_balance_absent(present),
    )
    assert result.values["bs.vc_total_cash"] == D("5300000")


def test_ci_statement_unchanged_by_default():
    result = compute_statement({"is.revenue": D("10"), "is.cogs": D("4")}, statements=["is"],
                               absent=["is.sga", "is.depreciation_amortization", "is.other_operating_expense",
                                       "is.nonrecurring_expense", "is.interest_expense", "is.other_income_net",
                                       "is.income_tax_expense"])
    assert result.values["is.gross_profit"] == D("6")


def test_saas_lines_are_point_in_time_even_when_computed_statements_are_chosen():
    result = compute_statement({"saas.mrr": D("1"), "saas.arr": D("12"), "saas.customers": D("3")},
                               statements=["saas"], template_id="vc-1")
    assert result.ok and result.values["saas.arr"] == D("12")


def test_vc_missing_input_is_an_error_naming_the_line():
    result = compute_statement({"is.subscription_revenue": D("5")}, statements=["is"], template_id="vc-1")
    assert any(e.key == "is.services_revenue" for e in result.errors)
    assert "is.total_revenue" not in result.values


def test_ci_line_in_a_vc_statement_is_unknown_and_the_error_names_the_template():
    result = compute_statement({"bs.cash": D("1")}, statements=["bs"], template_id="vc-1")
    errors = [e for e in result.errors if e.key == "bs.cash"]
    assert errors and errors[0].code == E.UNKNOWN_KEY and "vc-1" in errors[0].message
    absent = compute_statement({}, absent=["bs.cash"], statements=["bs"], template_id="vc-1")
    assert any(e.key == "bs.cash" and "vc-1" in e.message for e in absent.errors)


def test_stated_total_of_the_other_template_is_unknown():
    result = compute_statement({"stated.bs.total_assets": D("1")}, statements=["saas"], template_id="vc-1")
    assert any(e.code == E.UNKNOWN_KEY and "vc-1" in e.message for e in result.errors)


def test_vc_check_statement_has_no_ties_and_foots_totals():
    inputs = {"saas.mrr": D("1"), "saas.arr": D("12"), "saas.customers": D("3"), "stated.is.total_revenue": D("9")}
    inputs.update({"is.subscription_revenue": D("6"), "is.services_revenue": D("3"), "is.cost_of_revenue": D("1"),
                   "is.rnd": D("1"), "is.sales_marketing": D("1"), "is.gna": D("1"),
                   "is.vc_depreciation_amortization": D("0"), "is.vc_interest": D("0"), "is.vc_other_income": D("0")})
    report = check_statement(inputs, scale=1, prior_fye_cash=None, statements=["is"], template_id="vc-1")
    assert report.ok, report.errors
    assert not [c for c in report.checks if c.check == "tie"]
    assert [c.status for c in report.checks if c.key == "is.total_revenue"] == ["pass"]
    assert report.values["is.vc_net_loss"] == D("5")


def test_vc_check_statement_balance_and_roll_use_vc_keys():
    inputs = {k: D("0") for k in (line.key for line in template_lines("vc-1"))
              if k.startswith(("bs.", "cf.")) and not line_info(k).computed}
    inputs["bs.cash_unrestricted"] = D("10")
    inputs["bs.common_equity"] = D("10")
    inputs["cf.equity_raised"] = D("10")
    report = check_statement(inputs, scale=1, prior_fye_cash=D("0"), statements=["bs", "cf"], template_id="vc-1")
    by_check = {c.check: c for c in report.checks if c.check in ("balance", "cash_roll")}
    assert by_check["balance"].key == "bs.vc_total_assets" and by_check["balance"].status == "pass"
    assert by_check["cash_roll"].key == "cf.vc_net_change_in_cash" and by_check["cash_roll"].status == "pass"


def test_vc_check_statement_balance_failure_is_reported():
    inputs = {k: D("0") for k in (line.key for line in template_lines("vc-1"))
              if k.startswith("bs.") and not line_info(k).computed}
    inputs["bs.cash_unrestricted"] = D("10")
    report = check_statement(inputs, scale=1, prior_fye_cash=None, statements=["bs"], template_id="vc-1")
    assert any(e.code == E.DOES_NOT_BALANCE for e in report.errors)


def test_ci_check_statement_still_runs_ties():
    report = check_statement({}, scale=1, prior_fye_cash=None, statements=["cf"])
    assert {c.key for c in report.checks if c.check == "tie"} == {
        "cf.net_income", "cf.depreciation_amortization"}


# Standard-spread sections (backend/app/calc/TEMPLATES.md)
DOC = Path(app.calc.__file__).parent / "TEMPLATES.md"


def _documented_sections():
    return set(re.findall(r"^\| ([A-Z][^|]*?) \| (?:is|bs|cf|sup|saas) \|", DOC.read_text(), flags=re.M))


def test_every_line_has_a_documented_section():
    documented = _documented_sections()
    assert documented, "no section table found in TEMPLATES.md"
    for template_id, lines in TEMPLATES.items():
        for line in lines:
            assert line.section in documented, (template_id, line.key, line.section)


def test_every_template_line_is_listed_in_the_doc():
    text = DOC.read_text()
    for lines in TEMPLATES.values():
        for line in lines:
            assert f"`{line.key}`" in text, line.key


def test_section_defaults_so_existing_constructors_keep_working():
    assert TemplateLine("x.y", "Y", "is").section == ""
