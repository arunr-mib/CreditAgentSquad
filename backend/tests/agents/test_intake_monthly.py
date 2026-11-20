"""Intake for monthly reporting: new document types, filing rules, and a person asked who and when."""
from datetime import date

import pytest
from app.agents.intake import classify_documents, rule_type
from app.domain import workflow
from app.domain.documents_service import ingest_pdf
from app.domain.monitoring import WorkItem
from sqlalchemy import select
from tests.agents.test_intake import answer, pdf, world  # noqa: F401  (world: borrower fixture)

OCT = date(2026, 10, 31)


@pytest.mark.parametrize("text,expected", [
    ("For the ten months ended October 31, 2026", "monthly_financials"),
    ("One month ended October 31, 2026", "monthly_financials"),
    ("For the month of October 2026", "monthly_financials"),
    ("For the month ended October 31, 2026", "monthly_financials"),
    ("Eleven months ended November 30, 2026", "monthly_financials"),
    ("Nine months ended September 30, 2026", "interim_statements"),
    ("Three months ended September 30, 2026", "interim_statements"),
    ("Quarter ended September 30, 2026", "interim_statements"),
    ("Year ended December 31, 2025", "annual_statements"),
    ("Monthly Recurring Revenue report", "mrr_report"),
    ("MRR report - October 2026", "mrr_report"),
    ("ARR report", "mrr_report"),
    ("Dataflake Inc\nMRR report for the month ended October 31, 2026", "mrr_report"),
    ("Annual recurring revenue report", "mrr_report"),
    ("ARR waterfall", None),  # a bare acronym is not a title phrase: the agent reads it, code does not file it
    # an investor update or a monthly pack that mentions ARR on page one keeps its own type
    ("Q3 Investor Update\nARR grew 40% to $4.8M; MRR $400k", "investor_update"),
    ("Harrowgate Labs\nFor the month ended October 31, 2026\nARR 4,800 MRR 400", "monthly_financials"),
    ("Harrowgate Labs\nFor the ten months ended October 31, 2026\nMonthly recurring revenue 400", "monthly_financials"),
    ("Statement of account", "bank_statement"),
    ("Bank statement - operating", "bank_statement"),
    ("Series B term sheet", "term_sheet"),
    ("Summary of Terms", "term_sheet"),
    ("Q3 Investor Update", "investor_update"),
    ("Letter to investors", "investor_update"),
    ("COMPLIANCE CERTIFICATE for the month ended October 31, 2026", "compliance_certificate"),
])
def test_filing_rules(text, expected):
    assert rule_type(text) == expected


def test_a_monthly_statement_is_filed_with_its_period(db, world):  # noqa: F811
    borrower, _ = world
    cycle = workflow.open_cycle(db, borrower_id=borrower.id, period_end=OCT, months=1)
    doc = ingest_pdf(db, borrower_id=borrower.id, file_name="oct.pdf", data=pdf(
        "Harrowgate Tool & Die, Inc.", "Income Statement", "For the ten months ended October 31, 2026"))
    llm = answer(dict(doc_type="monthly_financials", period_end_text="October 31, 2026", quality="internal",
                      title_as_printed="Income Statement"))
    result = classify_documents(db, borrower=borrower, documents=[doc], llm=llm, cycle=cycle, batch_key="m1")
    assert result.work_items == [] and doc.doc_type == "monthly_financials" and doc.period_end == OCT


def test_an_mrr_export_naming_no_company_is_held_with_one_question(db, world):  # noqa: F811
    borrower, _ = world
    cycle = workflow.open_cycle(db, borrower_id=borrower.id, period_end=OCT, months=1)
    doc = ingest_pdf(db, borrower_id=borrower.id, file_name="mrr.pdf", data=pdf(
        "Monthly Recurring Revenue", "As of October 31, 2026", "New MRR  Expansion MRR  Churned MRR"))
    llm = answer(dict(doc_type="mrr_report", period_end_text="October 31, 2026", quality="internal",
                      title_as_printed="Monthly Recurring Revenue"))
    result = classify_documents(db, borrower=borrower, documents=[doc], llm=llm, cycle=cycle, batch_key="m2")
    assert result.filed == [] and doc.doc_type is None
    item = db.execute(select(WorkItem)).scalar_one()
    assert item.question == "Which client is this, and which month?"


def test_a_monthly_document_for_another_period_is_held_with_the_same_question(db, world):  # noqa: F811
    borrower, _ = world
    cycle = workflow.open_cycle(db, borrower_id=borrower.id, period_end=OCT, months=1)
    doc = ingest_pdf(db, borrower_id=borrower.id, file_name="sep.pdf", data=pdf(
        "Harrowgate Tool & Die, Inc.", "Monthly Recurring Revenue", "As of September 30, 2026"))
    llm = answer(dict(doc_type="mrr_report", period_end_text="September 30, 2026", quality="internal",
                      title_as_printed="Monthly Recurring Revenue"))
    result = classify_documents(db, borrower=borrower, documents=[doc], llm=llm, cycle=cycle, batch_key="m3")
    assert result.filed == []
    item = db.execute(select(WorkItem)).scalar_one()
    assert item.question == "Which client is this, and which month?"
    assert "expected" in item.evidence["reason"]


def test_a_term_sheet_needs_no_period(db, world):  # noqa: F811
    borrower, _ = world
    cycle = workflow.open_cycle(db, borrower_id=borrower.id, period_end=OCT, months=1)
    doc = ingest_pdf(db, borrower_id=borrower.id, file_name="ts.pdf", data=pdf(
        "Harrowgate Tool & Die, Inc.", "Series B Term Sheet"))
    llm = answer(dict(doc_type="term_sheet", period_end_text="", quality="na", title_as_printed="Series B Term Sheet"))
    result = classify_documents(db, borrower=borrower, documents=[doc], llm=llm, cycle=cycle, batch_key="m4")
    assert result.work_items == [] and doc.doc_type == "term_sheet"
