"""Intake: the agent proposes a type and period; code checks it, files it and chases what is missing."""
import io
import json
from datetime import UTC, date, datetime

import pytest
from app.agents.intake import chase_missing, classify_documents
from app.agents.llm import LLMResponse, ScriptedClient
from app.core.config import get_settings
from app.domain import calendar, workflow
from app.domain.credit import Borrower, Facility
from app.domain.documents_service import ingest_pdf
from app.domain.monitoring import WorkItem
from app.domain.org import User
from app.domain.terms import ReportingObligation, TermsVersion
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import select

PERIOD = date(2026, 9, 30)
TERMS = {
    "definitions": {}, "covenants": [], "borrowing_base": None,
    "reporting_requirements": [
        {"id": "quarterly_statements", "document_type": "interim_statements", "frequency": "quarterly",
         "due_days_after_period_end": 45},
        {"id": "quarterly_certificate", "document_type": "compliance_certificate", "frequency": "quarterly",
         "due_days_after_period_end": 45},
        {"id": "annual_statements", "document_type": "annual_statements", "frequency": "annual",
         "due_days_after_period_end": 120, "quality": "audited"},
    ],
}


def pdf(*lines: str) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter, invariant=1)
    y = 720
    for line in lines:
        c.drawString(72, y, line)
        y -= 16
    c.showPage()
    c.save()
    return buf.getvalue()


@pytest.fixture()
def world(db, tmp_path, monkeypatch):
    monkeypatch.setenv("FILE_STORE_DIR", str(tmp_path))
    get_settings.cache_clear()
    approver = User(email="a@x.example", name="A", role="credit_officer", password_hash="x")
    borrower = Borrower(code="HTD", name="Harrowgate Tool & Die, Inc.")
    db.add_all([approver, borrower])
    db.flush()
    facility = Facility(borrower_id=borrower.id, code="HTD-RLOC", name="Revolver", facility_type="revolver",
                        commitment=5_000_000)
    db.add(facility)
    db.flush()
    version = TermsVersion(facility_id=facility.id, version=1, status="approved", effective_from=date(2024, 1, 1),
                           terms=TERMS, approved_by=approver.id, approved_at=datetime.now(UTC))
    db.add(version)
    db.flush()
    calendar.generate_obligations(db, facility, version, start=date(2026, 1, 1), through=date(2026, 11, 17))
    cycle = workflow.open_cycle(db, borrower_id=borrower.id, period_end=PERIOD, months=9)
    yield borrower, cycle
    get_settings.cache_clear()


def answer(*docs) -> ScriptedClient:
    body = {"documents": [dict(document_number=i, effective_date_text="", concern="", **d)
                          for i, d in enumerate(docs, start=1)]}
    return ScriptedClient([LLMResponse(content=[{"type": "text", "text": json.dumps(body)}], stop_reason="end_turn")])


def obligations(db, status):
    return sorted((o.document_type, o.period_end) for o in db.execute(
        select(ReportingObligation).where(ReportingObligation.status == status)).scalars())


def test_obligations_are_generated_from_approved_terms(db, world):
    all_obs = db.execute(select(ReportingObligation)).scalars().all()
    by_type = {}
    for ob in all_obs:
        by_type.setdefault(ob.document_type, []).append(ob.period_end)
    assert sorted(by_type["interim_statements"]) == [date(2026, 3, 31), date(2026, 6, 30), date(2026, 9, 30)]
    assert next(o for o in all_obs if o.period_end == PERIOD and o.document_type == "interim_statements").due_date == date(2026, 11, 14)
    assert "annual_statements" not in by_type  # nothing annual falls due inside this window


def test_documents_are_filed_and_matched_when_code_agrees(db, world):
    borrower, cycle = world
    docs = [
        ingest_pdf(db, borrower_id=borrower.id, file_name="fs.pdf", received_date=date(2026, 11, 10), data=pdf(
            "Harrowgate Tool & Die, Inc.", "Balance Sheet", "Nine months ended September 30, 2026", "Unaudited")),
        ingest_pdf(db, borrower_id=borrower.id, file_name="cert.pdf", received_date=date(2026, 11, 10), data=pdf(
            "COMPLIANCE CERTIFICATE", "Harrowgate Tool & Die, Inc.", "For the fiscal quarter ended September 30, 2026")),
    ]
    llm = answer(
        dict(doc_type="interim_statements", period_end_text="September 30, 2026", quality="internal", title_as_printed="Balance Sheet"),
        dict(doc_type="compliance_certificate", period_end_text="September 30, 2026", quality="na", title_as_printed="COMPLIANCE CERTIFICATE"))
    result = classify_documents(db, borrower=borrower, documents=docs, llm=llm, cycle=cycle, batch_key="t1")
    assert len(result.filed) == 2 and result.work_items == []
    assert docs[0].doc_type == "interim_statements" and docs[0].period_end == PERIOD and docs[0].doc_type_source == "agent"
    assert obligations(db, "received") == [("compliance_certificate", PERIOD), ("interim_statements", PERIOD)]
    # the model saw only text it cannot act on: the request carried no tools
    assert llm.requests[0].tools == []


def test_disagreement_with_the_filing_rules_goes_to_a_person(db, world):
    borrower, cycle = world
    doc = ingest_pdf(db, borrower_id=borrower.id, file_name="cert.pdf", data=pdf(
        "COMPLIANCE CERTIFICATE", "For the fiscal quarter ended September 30, 2026"))
    llm = answer(dict(doc_type="interim_statements", period_end_text="September 30, 2026", quality="internal",
                      title_as_printed="COMPLIANCE CERTIFICATE"))
    result = classify_documents(db, borrower=borrower, documents=[doc], llm=llm, cycle=cycle, batch_key="t2")
    assert result.filed == [] and doc.doc_type is None
    item = db.execute(select(WorkItem)).scalar_one()
    assert item.item_type == "intake.unclassified" and "filing rules read it as compliance_certificate" in item.evidence["reason"]


def test_a_period_that_is_not_on_the_page_is_refused(db, world):
    borrower, cycle = world
    doc = ingest_pdf(db, borrower_id=borrower.id, file_name="fs.pdf", data=pdf(
        "Balance Sheet", "Six months ended June 30, 2026", "Unaudited"))
    llm = answer(dict(doc_type="interim_statements", period_end_text="September 30, 2026", quality="internal",
                      title_as_printed="Balance Sheet"))
    result = classify_documents(db, borrower=borrower, documents=[doc], llm=llm, cycle=cycle, batch_key="t3")
    assert result.filed == [] and obligations(db, "received") == []


def test_missing_reporting_raises_one_item_with_a_draft_chaser(db, world):
    borrower, cycle = world
    assert chase_missing(db, borrower=borrower, cycle=cycle, today=date(2026, 11, 10)) is None  # not yet due
    calendar.refresh_statuses(db, date(2026, 11, 17))
    item = chase_missing(db, borrower=borrower, cycle=cycle, today=date(2026, 11, 17))
    assert item.item_type == "intake.missing_document" and item.evidence["days_past_due"] == 3
    assert "compliance certificate, interim statements" in item.evidence["draft_email"]
    assert chase_missing(db, borrower=borrower, cycle=cycle, today=date(2026, 11, 17)).id == item.id  # no duplicate
    overdue_now = [o for o in obligations(db, "overdue") if o[1] == PERIOD]
    assert overdue_now == [("compliance_certificate", PERIOD), ("interim_statements", PERIOD)]


# ---- third independent review: a document for another company, or filed to the comparative date

def test_a_document_that_does_not_name_the_borrower_is_not_filed(db, world):
    borrower, cycle = world
    doc = ingest_pdf(db, borrower_id=borrower.id, file_name="fs.pdf", data=pdf(
        "Northfield Castings Group, LLC", "Balance Sheet", "Nine months ended September 30, 2026", "Unaudited"))
    llm = answer(dict(doc_type="interim_statements", period_end_text="September 30, 2026", quality="internal",
                      title_as_printed="Balance Sheet"))
    result = classify_documents(db, borrower=borrower, documents=[doc], llm=llm, cycle=cycle, batch_key="t8")
    assert result.filed == [] and doc.doc_type is None
    assert "may be another company's" in db.execute(select(WorkItem)).scalar_one().evidence["reason"]


def test_statements_are_not_filed_to_the_comparative_columns_date(db, world):
    borrower, cycle = world
    doc = ingest_pdf(db, borrower_id=borrower.id, file_name="fs.pdf", data=pdf(
        "Harrowgate Tool & Die, Inc.", "Balance Sheet", "September 30, 2026", "September 30, 2025", "Unaudited"))
    llm = answer(dict(doc_type="interim_statements", period_end_text="September 30, 2025", quality="internal",
                      title_as_printed="Balance Sheet"))
    result = classify_documents(db, borrower=borrower, documents=[doc], llm=llm, cycle=cycle, batch_key="t9")
    assert result.filed == [] and doc.period_end is None
    assert "comparative column" in db.execute(select(WorkItem)).scalar_one().evidence["reason"]


def test_one_late_filing_raises_one_item_and_the_late_signal_attaches_to_it(db, world):
    """Reporting 18 days late used to raise both "reporting is 18 days past due" (the calendar's
    chaser) and "reporting late" (the early warning). One late obligation is one item: the
    early warning is recorded on the chaser item instead of raising a second."""
    from app.core.ledger import LedgerEvent
    from app.domain.monitoring import Signal
    from app.domain.signals_service import run_signals

    borrower, cycle = world
    today = date(2026, 12, 2)  # the September reporting was due on November 14
    calendar.refresh_statuses(db, today)
    chaser = chase_missing(db, borrower=borrower, cycle=cycle, today=today)
    assert chaser.evidence["days_past_due"] == 18
    run_signals(db, borrower=borrower, period_end=PERIOD, as_of=today, cycle=cycle)
    late = db.execute(select(Signal).where(Signal.rule_id == "reporting_late")).scalar_one()
    assert late.severity == "high"

    open_items = db.execute(select(WorkItem).where(WorkItem.status == "open")).scalars().all()
    assert [w.id for w in open_items] == [chaser.id]
    assert chaser.evidence["signals"] == [{"signal_id": str(late.id), "rule_id": "reporting_late"}]
    attached = db.execute(select(LedgerEvent).where(LedgerEvent.action == "work_item.signal_attached")).scalar_one()
    assert attached.entity_id == str(chaser.id) and attached.payload["signal_id"] == str(late.id)

    # running both again changes nothing
    chase_missing(db, borrower=borrower, cycle=cycle, today=today)
    run_signals(db, borrower=borrower, period_end=PERIOD, as_of=today, cycle=cycle)
    assert db.execute(select(WorkItem).where(WorkItem.status == "open")).scalars().all() == [chaser]
    assert len(chaser.evidence["signals"]) == 1


def test_late_reporting_with_no_chaser_still_raises_the_early_warning(db, world):
    """Received late: nothing is missing, so there is no chaser, and the early warning is the item."""
    from app.domain.signals_service import run_signals

    borrower, cycle = world
    for ob in db.execute(select(ReportingObligation).where(ReportingObligation.period_end == PERIOD)).scalars():
        ob.status, ob.received_date = "received", date(2026, 12, 2)
    db.flush()
    run_signals(db, borrower=borrower, period_end=PERIOD, as_of=date(2026, 12, 3), cycle=cycle)
    items = db.execute(select(WorkItem).where(WorkItem.status == "open")).scalars().all()
    assert [w.item_type for w in items] == ["signal.high"]


@pytest.mark.parametrize("head", [
    "AMENDED AND RESTATED CREDIT AGREEMENT\ndated as of March 1, 2024",
    "Credit Agreement dated as of March 1, 2024",
    "Second Amendment to Amended and Restated Credit Agreement",   # an amendment, not a credit agreement
    "VENTURE LOAN AND SECURITY AGREEMENT",
    "Loan and Security Agreement among Veridia Payments and Bank of Stoic",
])
def test_the_credit_agreement_heading_anchor_handles_real_titles(head):
    from app.agents.intake import rule_type
    expected = "amendment" if head.startswith("Second Amendment") else "credit_agreement"
    assert rule_type(head) == expected


def test_a_bank_statement_note_about_the_agreement_is_not_a_credit_agreement():
    from app.agents.intake import rule_type
    assert rule_type("Collateral account pledged under the venture loan agreement\nOpening balance") != "credit_agreement"
    assert rule_type("Note: see the Credit Agreement dated March 1, 2024 for terms of the loan.") is None


def test_a_document_the_agent_classifies_wakes_gathering_for_a_returned_case(db, world):
    """Task 5c: classification is where code gathers again; an agent's unconfirmed guess is asked about, not attached."""
    from app.core import ledger
    from app.domain.work_items import raise_item
    from app.domain.workflow import RETURNED

    borrower, cycle = world
    item = raise_item(db, borrower_id=borrower.id, item_type="test.routed_case", title="Cash below minimum",
                      question="How should the bank respond?", allowed_decisions=["no_action"])
    ledger.record(db, actor_type="user", actor_id="00000000-0000-0000-0000-000000000001", action=RETURNED,
                  entity_type="work_item", entity_id=item.id,
                  payload={"borrower_id": borrower.id, "reason": "Need it.",
                           "needs": [{"index": 0, "doc_type": "interim_statements", "period_end": "2026-09-30"}]})
    doc = ingest_pdf(db, borrower_id=borrower.id, file_name="fs.pdf", received_date=date(2026, 11, 10), data=pdf(
        "Harrowgate Tool & Die, Inc.", "Balance Sheet", "Nine months ended September 30, 2026", "Unaudited"))
    llm = answer(dict(doc_type="interim_statements", period_end_text="September 30, 2026", quality="internal",
                      title_as_printed="Balance Sheet"))
    classify_documents(db, borrower=borrower, documents=[doc], llm=llm, cycle=cycle, batch_key="t5c")
    asks = [w for w in db.execute(select(WorkItem)).scalars()
            if w.item_type == "question" and w.evidence.get("topic") == "evidence_match"]
    assert len(asks) == 1 and asks[0].evidence["case_id"] == str(item.id)
