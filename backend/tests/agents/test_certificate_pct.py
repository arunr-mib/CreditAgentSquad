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


def run(world, *, unit, actual="105.30%", required="Not less than 80.00% of plan", cid="revenue_vs_plan",
        name="Revenue to Plan", threshold=D("0.80"), **pdf_args):
    db, _ = world
    borrower = db.execute(select(Borrower).where(Borrower.code == "pellham-grain")).scalar_one()
    facility = db.execute(select(Facility).where(Facility.borrower_id == borrower.id)).scalars().first()
    _, version = governing_terms(db, facility, PERIOD)
    base = version.terms.covenants[0]
    covenant = base.model_copy(update={"id": cid, "name": name,
                                       "test": base.test.model_copy(update={"unit": unit, "threshold": threshold})})
    terms = version.terms.model_copy(update={"covenants": [covenant]})
    doc = ingest_pdf(db, borrower_id=borrower.id, file_name="cert.pdf", doc_type="compliance_certificate",
                     period_end=PERIOD, data=cert_pdf(actual=actual, label=name, **pdf_args))
    rows = [{"covenant_id": cid, "page": 1, "printed_label": name, "actual_printed": actual,
             "required_printed": required, "compliance_printed": "Yes"}]
    answer = {"rows": rows, "scale_statement": "", "scale_page": 0, "notes": []}
    llm = ScriptedClient([LLMResponse(content=[{"type": "text", "text": json.dumps(answer)}], stop_reason="end_turn")])
    result = read_certificate(db, borrower=borrower, document=doc, period_end=PERIOD, terms=terms, cycle=None, llm=llm)
    get = lambda part: current_fact(db, borrower.id, f"cert.{cid}.{part}", PERIOD, 0)  # noqa: E731
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


def test_a_figure_printed_with_its_unit_word_is_stored_as_the_figure(book):  # noqa: F811
    result, get = run(book, unit="months", actual="9.4 months", required="Not less than 6.0 months",
                      cid="min_runway_months", name="Minimum Runway", required_lines=("", "Not less than 6.0 months"))
    assert result.unverified == [] and result.stored == ["min_runway_months"]
    assert get("value").value == D("9.4") and get("threshold").value == D("6.0")
    result, get = run(book, unit="ratio", actual="6.54 to 1.00", required="Not less than 1.25x",
                      cid="dscr", name="DSCR", required_lines=("", "Not less than 1.25x"))
    assert result.unverified == [] and get("value").value == D("6.54")


def test_a_unit_word_that_does_not_belong_to_the_covenant_is_not_dropped(book):  # noqa: F811
    result, get = run(book, unit="usd", actual="9.4 months", required="Not less than 6.0",
                      cid="cash", name="Minimum Cash", required_lines=("", "Not less than 6.0"))
    assert get("value") is None and result.stored == [] and result.unverified


def test_a_not_meaningful_actual_stores_no_value_but_the_requirement_and_the_flag(book):  # noqa: F811
    result, get = run(book, unit="months", actual="Not meaningful", required="Not less than 6.0 months",
                      cid="min_runway_months", name="Minimum Runway", required_lines=("", "Not less than 6.0 months"))
    assert result.unverified == [] and result.stored == [] and result.not_meaningful == ["min_runway_months"]
    assert get("value") is None  # never a zero or an invented figure
    assert get("threshold").value == D("6.0") and get("in_compliance").value == 1
    assert get("threshold").label_text == "Minimum Runway"


def test_a_ratio_requirement_printed_as_to_one_wraps_and_is_still_one_figure(book):  # noqa: F811
    result, get = run(book, unit="ratio", actual="6.54 to 1.00", required="Not less than 1.25 to 1.00",
                      cid="dscr", name="DSCR", threshold=D("1.25"), required_lines=("Not less than 1.25 to", "1.00"))
    assert result.unverified == [] and get("threshold").value == D("1.25")


def test_a_not_meaningful_actual_leaves_a_fact_the_comparison_can_read(book):  # noqa: F811
    from app.domain.covenant_service import _reported
    result, get = run(book, unit="months", actual="Not meaningful", required="Not less than 6.0 months",
                      cid="min_runway_months", name="Minimum Runway", required_lines=("", "Not less than 6.0 months"))
    flag = get("not_meaningful")
    assert flag.value == 1 and flag.quote == "Not meaningful" and flag.label_text == "Minimum Runway"
    db, _ = book
    borrower = db.execute(select(Borrower).where(Borrower.code == "pellham-grain")).scalar_one()
    entry, value_fact = _reported(db, borrower.id, "min_runway_months", PERIOD)
    assert entry.not_meaningful is True and entry.value is None and entry.in_compliance is True and value_fact is None
