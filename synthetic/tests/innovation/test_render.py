"""The renderers for the new document types print what they are given, on pages marked synthetic."""

from __future__ import annotations

from datetime import date

from synthetic.books.innovation import reports
from synthetic.books.innovation.model import LAST
from synthetic.render import common
from synthetic.render import innovation as render

END = date(2026, 10, 31)
SPEC = type("Spec", (), {"name": "Datamarrow Inc", "auditor": "Wexley Arnault LLP", "city": "Austin", "state": "TX",
                         "legal_form": "corporation"})  # fmt: skip


def text(path) -> str:
    pages = common.page_texts(path)
    assert all(common.MARKER in page for page in pages)
    return "\n".join(pages)


def test_management_financials_print_the_figures_and_the_period_phrases(sims, tmp_path):
    sim = sims["cindrel-tech"]
    month, i = sim.months[LAST], LAST
    payload = {"end": END, "months": 10, "prior_end": date(2025, 12, 31), "balances": month.balances,
               "prior": sim.months[11].balances, "ytd": sim.periods[i].values, "month": {**month.flows, **month.balances},
               "labels": {"bs.deferred_revenue_current": "Contract liabilities"},
               "software_roll": reports.software_roll(sim.months, i)}  # fmt: skip
    result = render.render_monthly_financials(tmp_path / "mf.pdf", sim.spec, payload, "mf")
    body = text(tmp_path / "mf.pdf")
    assert "Ten months ended" in body and "One month ended" in body and "month ended October 31, 2026" in body
    assert "Contract liabilities" in body and "Deferred revenue, current" not in body
    figure = result["extra"]["figures"]["bs.cash_unrestricted"]
    assert figure["printed"] == f"{month.balances['bs.cash_unrestricted']:,}" and figure["page"] == 1
    assert result["extra"]["figures"]["cf.vc_capex"]["printed"].startswith("(")  # an outflow prints in brackets


def test_bank_statement_prints_restricted_accounts_and_ties_the_totals(tmp_path):
    accounts = [
        {"name": "Operating account", "tail": "4417", "restricted": False, "opening": 3_000_000, "credits": 800_000,
         "debits": 1_100_000, "closing": 2_700_000},
        {"name": "Collateral account", "tail": "9001", "restricted": True, "opening": 1_500_000, "credits": 0,
         "debits": 0, "closing": 1_500_000},
    ]  # fmt: skip
    result = render.render_bank_statement(tmp_path / "bank.pdf", SPEC, {"end": END, "accounts": accounts,
                                                                        "notes": ["Restricted."]}, "bank")
    body = text(tmp_path / "bank.pdf")
    assert "STATEMENT OF ACCOUNT" in body and "RESTRICTED" in body and "Bank of Stoic" in body
    assert result["extra"]["figures"]["bs.cash_unrestricted"]["printed"] == "$2,700,000"
    assert result["extra"]["figures"]["bs.cash_restricted"]["printed"] == "$1,500,000"


def test_certificate_mrr_report_and_notices(tmp_path):
    reported = {"min_unrestricted_cash": {"required_text": "Not less than $5,000,000", "actual_text": "$6,100,000",
                                          "in_compliance": True, "calculation": [("Unrestricted Cash", "$6,100,000")]}}
    render.render_monthly_certificate(tmp_path / "cc.pdf", SPEC, {
        "end": END, "document_date": date(2026, 11, 12), "signed_by": "Imogen Farrow", "reported": reported,
        "names": {"min_unrestricted_cash": "Minimum Unrestricted Cash"}}, "cc")
    assert "MONTHLY COMPLIANCE CERTIFICATE" in text(tmp_path / "cc.pdf") and "$6,100,000" in text(tmp_path / "cc.pdf")
    render.render_mrr_report(tmp_path / "mrr.pdf", SPEC, {
        "end": END, "mrr": 640_000, "arr": 7_680_000, "net_new_arr": 240_000, "customers": 140, "nrr": 108,
        "opening": 620_000, "new": 20_000, "expansion": 7_000, "contraction": 2_000, "churn": 5_000,
        "trend": [("May 2026", 500_000, 120)]}, "mrr")
    assert "MONTHLY RECURRING REVENUE REPORT" in text(tmp_path / "mrr.pdf")
    render.render_notice(tmp_path / "ts.pdf", SPEC, {
        "heading": "SUMMARY OF TERMS (TERM SHEET)", "subheading": "Series B extension",
        "sections": [("Amount", "$8,000,000")], "table": [["Term", "Summary"], ["Amount", "$8,000,000"]],
        "closing": "Non-binding.", "footer": "Term sheet"}, "ts")
    assert "TERM SHEET" in text(tmp_path / "ts.pdf")


def test_the_export_has_no_company_name_and_carries_the_marker(tmp_path):
    rows = [("2025-01", 800_000, 120), ("2025-02", 820_000, 121)]
    cells = render.write_export_workbook(tmp_path / "mrr_export.xlsx", rows)
    printed = render.render_export_print(tmp_path / "mrr_export.pdf", rows)
    assert "month,mrr_usd,customers" in cells and "SYNTHETIC - FOR DEMONSTRATION" in cells
    assert printed["extra"]["intake_form"] == "pdf_print_of_xlsx"
    assert "Cindrel" not in text(tmp_path / "mrr_export.pdf") and "2025-01" in text(tmp_path / "mrr_export.pdf")


def test_certificate_prints_a_ratio_line_and_mrr_figures_use_engine_keys(tmp_path):
    reported = {"dscr": {"required_text": "Not less than 1.25 to 1.00", "actual_text": "1.40 to 1.00",
                         "in_compliance": True, "calculation": [("EBITDA", "$1,400,000")]}}  # fmt: skip
    render.render_monthly_certificate(tmp_path / "cc.pdf", SPEC, {
        "end": END, "document_date": date(2026, 11, 12), "signed_by": "Imogen Farrow", "reported": reported,
        "names": {"dscr": "Debt Service Coverage Ratio"}}, "cc")
    assert "Not less than 1.25 to 1.00" in text(tmp_path / "cc.pdf")
    result = render.render_mrr_report(tmp_path / "mrr.pdf", SPEC, {
        "end": END, "mrr": 640_000, "arr": 7_680_000, "net_new_arr": 240_000, "customers": 140, "nrr": 108,
        "opening": 620_000, "new": 20_000, "expansion": 7_000, "contraction": 2_000, "churn": 5_000,
        "trend": [("May 2026", 500_000, 120)]}, "mrr")  # fmt: skip
    figures = result["extra"]["figures"]
    assert set(figures) == {"saas.mrr", "saas.arr", "saas.customers", "saas.net_new_arr", "saas.net_revenue_retention"}
    assert figures["saas.net_revenue_retention"]["printed"] == "108%" and figures["saas.customers"]["printed"] == "140"


def test_certificate_columns_do_not_overprint_and_carry_the_units_line(tmp_path):
    import pymupdf

    reported = {"min_runway_months": {"required_text": "Not less than 6.0 months",
                                      "actual_text": "Not meaningful (cash-flow positive)", "in_compliance": True,
                                      "calculation": [("Unrestricted Cash", "$6,100,000")]}}  # fmt: skip
    path = tmp_path / "cc.pdf"
    render.render_monthly_certificate(path, SPEC, {
        "end": END, "document_date": date(2026, 11, 12), "signed_by": "Imogen Farrow", "reported": reported,
        "names": {"min_runway_months": "Minimum Runway"}}, "cc")
    assert "Dollar amounts in this certificate are presented in whole U.S. dollars." in text(path)
    with pymupdf.open(path) as pdf:
        page = pdf[0]
        required = pymupdf.Rect(page.search_for("Not less than 6.0 months")[0])
        actual = [pymupdf.Rect(r) for r in page.search_for("Not meaningful")]
        assert actual and not any(required.intersects(r) for r in actual)


def test_unmeasured_values_print_n_a_not_none(tmp_path):
    result = render.render_mrr_report(tmp_path / "mrr.pdf", SPEC, {
        "end": END, "mrr": 640_000, "arr": 7_680_000, "net_new_arr": None, "customers": 140, "nrr": None,
        "opening": 620_000, "new": 20_000, "expansion": 7_000, "contraction": 2_000, "churn": 5_000,
        "trend": [("May 2026", 500_000, 120)]}, "mrr")  # fmt: skip
    body = text(tmp_path / "mrr.pdf")
    assert "None" not in body and "n/a" in body
    assert "saas.nrr" not in result["extra"]["figures"] and "saas.net_revenue_retention" not in result["extra"]["figures"]
    assert "saas.net_new_arr" not in result["extra"]["figures"]
    accounts = [{"name": "Operating account", "tail": "4417", "restricted": False, "opening": None, "credits": 1,
                 "debits": 1, "closing": None}]  # fmt: skip
    bank = render.render_bank_statement(tmp_path / "bank.pdf", SPEC, {"end": END, "accounts": accounts, "notes": []}, "b")
    assert "None" not in text(tmp_path / "bank.pdf") and "bs.cash_unrestricted" not in bank["extra"]["figures"]
