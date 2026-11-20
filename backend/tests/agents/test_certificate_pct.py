"""Percent covenants on a certificate: stored as the engine's fractions, cited as printed, and a
wrapped required cell does not change the label stored for the row (stand-in defects A and B)."""
import io
import json
from datetime import date
from decimal import Decimal as D

from app.agents.certificate import read_certificate
from app.agents.llm import LLMResponse, ScriptedClient
from app.domain.covenant_service import governing_terms
from app.domain.credit import Borrower, Facility
from app.domain.documents_service import ingest_pdf
from app.domain.facts_service import current_fact
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import select
from support.agent_book import book, book_db  # noqa: F401

PERIOD = date(2026, 9, 30)


def cert_pdf(actual="105.30%", required_lines=("Not less than 80.00% of", "plan"), label="Revenue to Plan"):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter, invariant=1)
    c.setFont("Helvetica", 9)
    c.drawString(72, 760, "MONTHLY COMPLIANCE CERTIFICATE")
    c.drawString(72, 746, "Pellham Grain Co.")
    c.drawString(72, 560, "Covenant")
    c.drawString(200, 560, "Section")
    c.drawString(300, 560, "Required")
    c.drawString(450, 560, "Actual")
    c.drawString(510, 560, "In compliance")
    y = 540
    c.drawString(72, y, label)
    c.drawString(220, y, "6.3")
    # the required cell wraps: its first line sits above the covenant's own line
    c.drawString(243, y + 12, required_lines[0])
    c.drawString(243, y, required_lines[1])
    c.drawString(350, y, actual)
    c.drawString(520, y, "Yes")
    c.drawString(72, 40, "SYNTHETIC - FOR DEMONSTRATION")
    c.showPage()
    c.save()
    return buf.getvalue()


def run(book, *, unit, actual="105.30%", required="Not less than 80.00% of plan", **pdf_args):  # noqa: F811
    db, _ = book
    borrower = db.execute(select(Borrower).where(Borrower.code == "pellham-grain")).scalar_one()
    facility = db.execute(select(Facility).where(Facility.borrower_id == borrower.id)).scalars().first()
    _, version = governing_terms(db, facility, PERIOD)
    base = version.terms.covenants[0]
    covenant = base.model_copy(update={"id": "revenue_vs_plan", "name": "Revenue to Plan",
                                       "test": base.test.model_copy(update={"unit": unit, "threshold": D("0.80")})})
    terms = version.terms.model_copy(update={"covenants": [covenant]})
    doc = ingest_pdf(db, borrower_id=borrower.id, file_name="cert.pdf", doc_type="compliance_certificate",
                     period_end=PERIOD, data=cert_pdf(actual=actual, **pdf_args))
    rows = [{"covenant_id": "revenue_vs_plan", "page": 1, "printed_label": "Revenue to Plan", "actual_printed": actual,
             "required_printed": required, "compliance_printed": "Yes"}]
    answer = {"rows": rows, "scale_statement": "", "scale_page": 0, "notes": []}
    llm = ScriptedClient([LLMResponse(content=[{"type": "text", "text": json.dumps(answer)}], stop_reason="end_turn")])
    result = read_certificate(db, borrower=borrower, document=doc, period_end=PERIOD, terms=terms, cycle=None, llm=llm)
    get = lambda part: current_fact(db, borrower.id, f"cert.revenue_vs_plan.{part}", PERIOD, 0)  # noqa: E731
    return result, get


def test_a_percent_covenant_is_stored_as_a_fraction_and_cites_the_printed_figure(book):  # noqa: F811
    result, get = run(book, unit="pct")
    assert result.unverified == [] and result.stored == ["revenue_vs_plan"]
    value, threshold = get("value"), get("threshold")
    assert value.value == D("1.053") and threshold.value == D("0.80")
    assert value.quote == "105.30%" and threshold.quote == "Not less than 80.00% of plan"
    assert value.unit == "pct" and threshold.unit == "pct"


def test_a_wrapped_required_cell_does_not_change_the_stored_label(book):  # noqa: F811
    result, get = run(book, unit="pct")
    assert get("value").label_text == "Revenue to Plan"
    assert get("threshold").label_text == "Revenue to Plan" and get("in_compliance").label_text == "Revenue to Plan"
    assert result.unverified == []


def test_a_percent_sign_on_a_covenant_that_is_not_a_percentage_is_refused_not_scaled(book):  # noqa: F811
    result, get = run(book, unit="ratio")
    assert get("value") is None and result.stored == []
    assert result.unverified and result.unverified[0]["reason"] == "refused"
    assert "percent" in result.unverified[0]["detail"]


def test_a_percent_covenant_printed_without_a_percent_sign_is_refused(book):  # noqa: F811
    result, get = run(book, unit="pct", actual="1.053", required="Not less than 0.80 of plan",
                      required_lines=("Not less than 0.80 of", "plan"))
    assert get("value") is None and result.unverified[0]["reason"] == "refused"


def test_a_ratio_covenant_printed_as_a_ratio_is_stored_as_printed(book):  # noqa: F811
    result, get = run(book, unit="ratio", actual="1.28x", required="Not less than 0.80x of plan",
                      required_lines=("Not less than 0.80x of", "plan"))
    assert get("value").value == D("1.28") and result.unverified == []
