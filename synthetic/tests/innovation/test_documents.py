"""The documents: every one is marked synthetic, names its client, and prints exactly what the truth says."""

from __future__ import annotations

import re
from decimal import Decimal as D

from synthetic.books.innovation.layout import OUTFLOWS
from synthetic.books.innovation.roster import LENDER
from synthetic.render import common

REAL_BANKS = ("JPMorgan", "Chase", "Wells Fargo", "Citibank", "Citigroup", "Silicon Valley Bank", "SVB", "Bank of America",
              "HSBC", "Goldman", "Morgan Stanley", "First Republic", "Signature Bank", "Comerica", "Capital One")
WORDS = {8: "Eight", 9: "Nine", 10: "Ten"}
MONTHLY = ("monthly_financials", "mrr_report", "bank_statement", "compliance_certificate")


def real_banks_in(text: str) -> list[str]:
    """Proper names only, as whole words: "Purchases of property" must not match "Chase"."""
    return [bank for bank in REAL_BANKS if re.search(rf"\b{re.escape(bank)}\b", text)]


def innovation_docs(generated):
    kept = {"kestrel-bay-packaging", "harrowgate-precision", "briarstone-beverage", "pellham-grain"}
    return [d for d in generated.manifest["documents"] if d["borrower_id"] not in kept and d["path"].endswith(".pdf")]


def test_book_size_and_the_lender(generated):
    assert generated.manifest["counts"]["borrowers"] == 20
    assert len(generated.truths) == 20
    assert {t["borrower"]["lender"] for t in generated.truths.values()} == {LENDER}
    assert sum(1 for t in generated.truths.values() if t["borrower"].get("template_id") == "vc-1") == 16


def test_every_page_of_every_document_carries_the_marker_and_no_real_bank_appears(generated):
    for doc in innovation_docs(generated):
        pages = common.page_texts(generated.out / doc["path"])
        assert all(common.MARKER in page for page in pages), doc["id"]
        joined = "\n".join(pages)
        assert not real_banks_in(joined), doc["id"]
    assert any(d["path"].endswith(".xlsx") for d in generated.manifest["documents"])


def test_every_document_but_the_stray_export_names_its_client_in_the_first_pages(generated):
    names = {t["borrower"]["id"]: t["borrower"]["name"] for t in generated.truths.values()}
    for doc in innovation_docs(generated):
        if doc["id"] == "stripple-tech.mrr-export":
            continue
        head = "\n".join(common.page_texts(generated.out / doc["path"])[:2])
        assert names[doc["borrower_id"]] in head, doc["id"]


def printed(key: str, value: int) -> str:
    return common.accounting(D(-value if key in OUTFLOWS else value))


def test_monthly_financials_print_exactly_the_truth(generated):
    checked = 0
    for truth in generated.truths.values():
        if truth["borrower"].get("template_id") != "vc-1":
            continue
        periods = {p["period_end"]: p for p in truth["periods"]}
        for doc in (d for d in truth["documents"] if d["type"] == "monthly_financials"):
            values = periods[doc["period_end"]]["values"]
            pages = generated.text(doc["id"])
            for key, figure in doc["figures"].items():
                assert figure["printed"] == printed(key, values[key]), (doc["id"], key)
                assert figure["printed"] in pages[figure["page"] - 1], (doc["id"], key)
                checked += 1
            head = "\n".join(pages)
            assert "month ended" in head.lower() and f"{WORDS[doc['months']]} months ended" in head, doc["id"]
    assert checked > 16 * 3 * 40


def test_bank_statements_tie_to_the_balance_sheet(generated):
    for truth in generated.truths.values():
        if truth["borrower"].get("template_id") != "vc-1":
            continue
        periods = {p["period_end"]: p for p in truth["periods"]}
        for doc in (d for d in truth["documents"] if d["type"] == "bank_statement"):
            values = periods[doc["period_end"]]["values"]
            assert doc["figures"]["bs.cash_unrestricted"]["printed"] == f"${values['bs.cash_unrestricted']:,}", doc["id"]
            assert doc["figures"]["bs.cash_restricted"]["printed"] == f"${values['bs.cash_restricted']:,}", doc["id"]


def test_mrr_reports_print_the_saas_lines(generated):
    for truth in generated.truths.values():
        if truth["borrower"].get("template_id") != "vc-1":
            continue
        periods = {p["period_end"]: p for p in truth["periods"]}
        for doc in (d for d in truth["documents"] if d["type"] == "mrr_report"):
            values = periods[doc["period_end"]]["values"]
            assert doc["figures"]["saas.mrr"]["printed"] == f"${values['saas.mrr']:,}", doc["id"]
            assert doc["figures"]["saas.customers"]["printed"] == f"{values['saas.customers']:,}", doc["id"]


def test_certificates_print_what_the_truth_reports(generated):
    for truth in generated.truths.values():
        if truth["borrower"].get("template_id") != "vc-1":
            continue
        by_end = {c["period_end"]: c for c in truth["certificates"]}
        for doc in (d for d in truth["documents"] if d["type"] == "compliance_certificate"):
            text = "\n".join(generated.text(doc["id"]))
            reported = by_end[doc["period_end"]]["reported"]
            assert text.count("Yes") >= sum(1 for r in reported.values() if r["in_compliance"]), doc["id"]
            for entry in reported.values():
                if entry["unit"] == "usd":
                    assert f"${int(D(entry['value'])):,}" in text, doc["id"]


def test_each_client_has_the_documents_the_agreement_requires(generated):
    for cid, truth in generated.truths.items():
        if truth["borrower"].get("template_id") != "vc-1":
            continue
        by_type = {}
        for d in truth["documents"]:
            by_type.setdefault(d["type"], []).append(d)
        assert len(by_type["credit_agreement"]) == 1 and len(by_type["annual_financial_statements"]) == 1
        counts = {t: len(by_type.get(t, [])) for t in MONTHLY}
        assert counts == dict.fromkeys(MONTHLY, 2 if cid == "lumora-health" else 3), cid  # three months on file
        for d in by_type["monthly_financials"]:
            assert d["received_date"] <= truth["as_of"]
