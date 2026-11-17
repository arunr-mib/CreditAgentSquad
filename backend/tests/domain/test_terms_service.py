"""Terms: proposed by an agent or a person, checked against the page, approved by a second person."""
import io
from datetime import date
from decimal import Decimal as D

import pytest
from app.core.config import get_settings
from app.core.roles import SecondPersonRequired
from app.domain import hooks, workflow  # noqa: F401
from app.domain.covenant_service import governing_terms
from app.domain.credit import Borrower, Facility
from app.domain.documents_service import ingest_pdf
from app.domain.org import User
from app.domain.terms import ReportingObligation, TermsVersion
from app.domain.terms_service import TermsRefused, approve_terms, propose_terms
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import select

CLAUSES = [
    "7.11 Fixed Charge Coverage Ratio. Borrower shall not permit the Fixed Charge Coverage Ratio,",
    "measured as of the last day of each fiscal quarter, to be less than 1.20 to 1.00.",
    "6.1 Financial Statements. Borrower shall deliver quarterly financial statements within",
    "45 days after the end of each fiscal quarter.",
]


def agreement_pdf() -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter, invariant=1)
    y = 720
    for line in ["CREDIT AGREEMENT", "dated as of January 15, 2024", ""] + CLAUSES:
        c.drawString(72, y, line)
        y -= 16
    c.showPage()
    c.save()
    return buf.getvalue()


def terms(threshold="1.20", due_days=45, quote=None, external="AGR-1"):
    return {
        "definitions": {},
        "covenants": [{
            "id": "fccr", "name": "Fixed Charge Coverage Ratio", "archetype": "coverage",
            "params": {"numerator_base": "ebitda", "deductions": [], "denominator": ["cash_interest", "scheduled_principal"]},
            "test": {"operator": ">=", "threshold": threshold, "unit": "ratio"},
            "measurement": {"basis": "ttm", "frequency": "quarterly"}, "rounding": {"dp": 2, "mode": "half_up"},
            "citations": [{"document_id": external, "section": "7.11", "page": 1,
                           "quote": quote or "to be less than 1.20 to 1.00"}]}],
        "reporting_requirements": [{
            "id": "quarterly_statements", "document_type": "interim_statements", "frequency": "quarterly",
            "due_days_after_period_end": due_days,
            "citation": {"document_id": external, "section": "6.1", "page": 1,
                         "quote": "45 days after the end of each fiscal quarter"}}],
        "borrowing_base": None,
    }


@pytest.fixture()
def world(db, tmp_path, monkeypatch):
    monkeypatch.setenv("FILE_STORE_DIR", str(tmp_path))
    get_settings.cache_clear()
    people = {r: User(email=f"{r}@x.example", name=r, role=r, password_hash="x")
              for r in ("analyst", "credit_admin", "credit_officer")}
    borrower = Borrower(code="HTD", name="Harrowgate Tool & Die, Inc.")
    db.add_all([*people.values(), borrower])
    db.flush()
    facility = Facility(borrower_id=borrower.id, code="HTD-TL", name="Term loan", facility_type="term_loan",
                        commitment=D("10000000"))
    db.add(facility)
    db.flush()
    doc = ingest_pdf(db, borrower_id=borrower.id, data=agreement_pdf(), file_name="agreement.pdf",
                     doc_type="credit_agreement", doc_type_source="system")
    doc.meta = {**doc.meta, "external_id": "AGR-1"}
    db.flush()
    yield facility, people
    get_settings.cache_clear()


def propose(db, facility, body, by=("agent", "terms@1"), effective=date(2024, 1, 15)):
    return propose_terms(db, facility=facility, terms=body, effective_from=effective,
                         source_document_ids=["AGR-1"], prepared_by=by)


def test_clean_terms_have_no_warnings_and_do_not_govern_until_approved(db, world):
    facility, people = world
    version, item = propose(db, facility, terms())
    assert version.warnings == [] and version.status == "proposed" and item.requires_second_person
    assert governing_terms(db, facility, date(2025, 12, 31))[0] is None
    workflow.decide_work_item(db, item, user_id=people["credit_officer"].id, user_role="credit_officer", decision="approve")
    assert version.status == "approved" and version.approved_by == people["credit_officer"].id
    assert governing_terms(db, facility, date(2025, 12, 31))[0].id == version.id
    assert db.execute(select(ReportingObligation)).first() is not None  # the calendar was built


@pytest.mark.parametrize("body,warning", [
    (terms(threshold="1.25"), "number_not_in_quote:covenants.fccr.threshold"),
    (terms(quote="to be less than 1.25 to 1.00"), "quote_not_on_page:covenants.fccr"),
    (terms(due_days=30), "number_not_in_quote:reporting_requirements.quarterly_statements"),
    (terms(external="AGR-9"), "document_not_on_file:covenants.fccr"),
])
def test_a_number_that_is_not_in_its_quoted_clause_is_flagged(db, world, body, warning):
    facility, people = world
    version, item = propose(db, facility, body)
    assert warning in version.warnings and item.severity == "high"
    officer = people["credit_officer"]
    with pytest.raises(TermsRefused, match="written reason"):
        workflow.decide_work_item(db, item, user_id=officer.id, user_role=officer.role, decision="approve")
    assert version.status == "proposed" and item.status == "open"  # a refused decision records nothing
    workflow.decide_work_item(db, item, user_id=officer.id, user_role=officer.role, decision="approve",
                              reason="Checked against the signed original; the scan omits the rider.")
    assert version.status == "approved"


def test_malformed_terms_are_refused_with_the_place_to_repair(db, world):
    facility, _ = world
    body = terms()
    body["covenants"][0]["test"]["threshold"] = 1.2  # a float
    with pytest.raises(TermsRefused, match="covenants.0.test.threshold"):
        propose(db, facility, body)
    body = terms()
    body["covenants"][0]["params"]["denominator"] = []
    with pytest.raises(TermsRefused):
        propose(db, facility, body)
    assert db.execute(select(TermsVersion)).first() is None


def test_preparer_cannot_approve_their_own_terms(db, world):
    facility, people = world
    admin = people["credit_admin"]
    version, item = propose(db, facility, terms(), by=("user", str(admin.id)))
    with pytest.raises(SecondPersonRequired):
        approve_terms(db, version, admin)
    with pytest.raises(PermissionError):
        approve_terms(db, version, people["analyst"])
    approve_terms(db, version, people["credit_officer"])
    assert version.status == "approved"


def test_amendment_supersedes_without_rewriting(db, world):
    facility, people = world
    officer = people["credit_officer"]
    v1, _ = propose(db, facility, terms())
    approve_terms(db, v1, officer)
    original = dict(v1.terms)
    with pytest.raises(TermsRefused, match="after the version it replaces"):
        approve_terms(db, propose(db, facility, terms(), effective=date(2024, 1, 15))[0], officer)
    v3, _ = propose(db, facility, terms(), effective=date(2026, 7, 1))
    approve_terms(db, v3, officer)
    assert (v1.status, v1.effective_to, v1.terms) == ("superseded", date(2026, 6, 30), original)
    assert governing_terms(db, facility, date(2026, 6, 30))[0].id == v1.id
    assert governing_terms(db, facility, date(2026, 9, 30))[0].id == v3.id


def test_rejecting_needs_a_reason(db, world):
    facility, people = world
    officer = people["credit_officer"]
    version, item = propose(db, facility, terms())
    with pytest.raises(TermsRefused):
        workflow.decide_work_item(db, item, user_id=officer.id, user_role=officer.role, decision="reject")
    workflow.decide_work_item(db, item, user_id=officer.id, user_role=officer.role, decision="reject",
                              reason="Threshold misread; see section 7.11.")
    assert version.status == "rejected" and governing_terms(db, facility, date(2025, 12, 31))[0] is None
