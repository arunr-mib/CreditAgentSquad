from datetime import date, timedelta

from app.domain.documents import Document
from app.domain.work_items import raise_item
from app.squad.briefing import build_briefing
from app.squad.threads import build_thread
from app.squad.words import document_type_words

OCT, SEP = date(2026, 10, 31), date(2026, 9, 30)


def _doc(db, borrower, title, doc_type, period):
    d = Document(borrower_id=borrower.id, title=title, file_name="d.pdf", storage_path="x", sha256="c" * 64,
                 page_count=1, doc_type=doc_type, period_end=period, status="indexed")
    db.add(d)
    db.flush()
    return d


def _october(db, borrower):
    for title, kind in (("MRR report, October 2026", "mrr_report"), ("Account statement, October 2026", "bank_statement"),
                        ("Management financial statements, October 2026", "monthly_financials")):
        _doc(db, borrower, title, kind, OCT)


def test_documents_for_one_period_arrive_as_one_message(db, world):
    _october(db, world["borrower"])
    _doc(db, world["borrower"], "Venture Loan and Security Agreement", "credit_agreement", None)
    msgs = build_thread(db, world["borrower"].id)["messages"]
    arrivals = [m for m in msgs if m["type"] == "arrivals"]
    assert len(arrivals) == 1 and arrivals[0]["title"] == "3 documents arrived for October 2026"
    assert sorted(d["doc_type_words"] for d in arrivals[0]["documents"]) == [
        "Bank account statement", "MRR report", "Monthly financial statements"]
    assert [m["type"] for m in msgs].count("document") == 1  # the agreement has no period and stands alone


def test_the_thread_opens_at_the_first_open_case_not_the_oldest_document(db, world):
    _doc(db, world["borrower"], "MRR report, September 2026", "mrr_report", SEP)
    _october(db, world["borrower"])
    item = raise_item(db, borrower_id=world["borrower"].id, item_type="test.opening", title="A line is new",
                      question="How should the new line be mapped?", allowed_decisions=["mapped"])
    assert build_thread(db, world["borrower"].id)["opening_id"] == f"case:{item.id}"


def test_with_nothing_open_it_opens_at_the_newest_arrivals(db, world):
    for title in ("MRR report, September 2026", "Account statement, September 2026"):
        _doc(db, world["borrower"], title, "mrr_report", SEP)
    _october(db, world["borrower"])
    assert build_thread(db, world["borrower"].id)["opening_id"] == "arrivals:2026-10"


def test_an_empty_thread_opens_nowhere(db, world):
    assert build_thread(db, world["borrower"].id)["opening_id"] is None


def test_document_types_read_in_plain_words():
    assert document_type_words("mrr_report") == "MRR report"
    assert document_type_words("bank_statement") == "Bank account statement"
    assert document_type_words("bank_statements") == "Bank account statement"
    assert document_type_words(None) == "Not yet classified"
    assert document_type_words("new_kind") == "New kind"


def test_an_overdue_mrr_report_reads_mrr_in_the_briefing(db, world):
    from decimal import Decimal

    from app.core import clock
    from app.domain.credit import Facility
    from app.domain.terms import ReportingObligation
    f = Facility(borrower_id=world["borrower"].id, code="QFL-TL", name="Term loan", facility_type="term_loan",
                 commitment=Decimal("1000000"))
    db.add(f)
    db.flush()
    today = clock.today(db)
    db.add(ReportingObligation(borrower_id=world["borrower"].id, facility_id=f.id, requirement_id="mrr",
                               document_type="mrr_report", period_end=date(2026, 10, 31),
                               due_date=today - timedelta(days=4), status="overdue"))
    db.flush()
    titles = [i["title"] for i in build_briefing(db, world["analyst"])["items"] if i["kind"] == "overdue_report"]
    assert titles == ["MRR report for October 2026 is overdue"]
