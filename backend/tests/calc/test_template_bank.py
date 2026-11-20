from decimal import Decimal

from app.calc import template


def test_bank_lines_exist_for_the_venture_template_only_and_are_optional():
    keys = {line.key: line for line in template.template_lines("vc-1")}
    assert keys["bank.cash_unrestricted"].optional and keys["bank.cash_restricted"].optional
    assert not any(line.key.startswith("bank.") for line in template.template_lines("ci-1"))


def test_a_bank_statement_is_checked_for_the_bank_statement_only():
    values = {"bank.cash_unrestricted": Decimal("4300000"), "bank.cash_restricted": Decimal("1100000")}
    report = template.check_statement(values, scale=1, prior_fye_cash=None, absent=[], statements=("bank",),
                                      template_id="vc-1")
    assert [e for e in report.errors] == []
    assert report.values == values
