"""The scenarios as the documents show them: what an analyst would read on the pages."""

from __future__ import annotations

import openpyxl

from synthetic.books.innovation.roster import CURRENT_PERIOD


def test_datamarrow_documents_show_the_inflated_certificate_the_pledged_account_and_clause_1_1(generated):
    certificate = "\n".join(generated.text("datamarrow.mcc-2026-10-31"))
    assert "$6,100,000" in certificate and "pledged collateral account" in certificate and "Yes" in certificate
    clause = generated.truths["datamarrow"]["scenario"]["details"]["definition_clause"]
    assert clause["section"] == "1.1" and "excluding any cash that is pledged" in clause["quote"]
    page = generated.text("datamarrow.credit-agreement")[clause["page"] - 1]
    assert " ".join(clause["quote"].split()) in " ".join(page.split())
    statement = "\n".join(generated.text("datamarrow.bank-2026-10-31"))
    assert "$4,600,000" in statement and "$1,500,000" in statement and "RESTRICTED" in statement


def test_datamarrows_term_sheet_names_the_amount_and_the_closing_date(generated):
    sheet = "\n".join(generated.text("datamarrow.term-sheet-2026-11-10"))
    assert "$8,000,000" in sheet and "December 12, 2026" in sheet and "TERM SHEET" in sheet


def test_calveres_october_package_is_absent_and_september_is_there(generated):
    ids = {d["id"] for d in generated.manifest["documents"] if d["borrower_id"] == "calvere-health"}
    assert not [i for i in ids if i.endswith(CURRENT_PERIOD.isoformat())]
    assert {"calvere-health.bank-2026-09-30", "calvere-health.mf-2026-09-30"} <= ids


def test_brackmeres_october_statement_shows_the_new_restricted_account_and_the_certificate_counts_it(generated):
    october = "\n".join(generated.text("brackmere-medical.bank-2026-10-31"))
    september = "\n".join(generated.text("brackmere-medical.bank-2026-09-30"))
    certificate = "\n".join(generated.text("brackmere-medical.mcc-2026-10-31"))
    assert "9002" in october and "RESTRICTED" in october and "$1,000,000" in october and "9002" not in september
    assert "$5,300,000" in certificate and "$4,300,000" in october


def test_ferrogates_certificate_says_runway_is_not_meaningful(generated):
    assert "Not meaningful" in "\n".join(generated.text("ferrogate-cloud.mcc-2026-10-31"))


def test_cindrels_october_package_has_a_new_line_a_confusable_software_label_and_a_stray_export(generated):
    october = "\n".join(generated.text("cindrel-tech.mf-2026-10-31"))
    september = "\n".join(generated.text("cindrel-tech.mf-2026-09-30"))
    assert "Contract liabilities" in october and "Contract liabilities" not in september
    assert "Deferred revenue, current" in september and "Software development costs" in october
    workbook = openpyxl.load_workbook(generated.out / "documents" / "cindrel-tech" / "mrr_export.xlsx")
    cells = [str(c.value) for row in workbook.active.iter_rows() for c in row if c.value is not None]
    assert not any("Cindrel" in c for c in cells), "the export must name no company"
    assert any(c.startswith("2025-") for c in cells) and not any(c.startswith("2026-") for c in cells)
    assert "SYNTHETIC - FOR DEMONSTRATION" in cells
    printed = "\n".join(generated.text("cindrel-tech.mrr-export"))
    assert "Cindrel" not in printed and "mrr_export.xlsx" in printed
    held = next(d for d in generated.truths["cindrel-tech"]["documents"] if d["id"] == "cindrel-tech.mrr-export")
    assert held["held"] is True and held["period_end"] is None and held["type"] == "unclassified"
    details = generated.truths["cindrel-tech"]["scenario"]["details"]
    assert details["new_line"]["page"] == 1 and details["capitalised_software"]["page"] == 1


def test_funding_events_are_in_the_truth_files_with_evidence_documents(generated):
    events = {cid: t["funding_events"] for cid, t in generated.truths.items() if t.get("funding_events")}
    assert sorted(events) == ["datamarrow", "kelvra-bio", "nimbusfield-security", "tavernel-grid"]
    for cid, rows in events.items():
        ids = {d["id"] for d in generated.truths[cid]["documents"]}
        assert all(e["evidence_document_ids"] and set(e["evidence_document_ids"]) <= ids for e in rows), cid
    assert events["tavernel-grid"][0]["expected_close"] == "2027-03-31"
    assert events["kelvra-bio"][0]["expected_close"] == "2027-02-26"
