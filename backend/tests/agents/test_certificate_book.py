"""A certificate that shows a covenant failing must reach a person even when the bank's own
calculation passes, however the certificate's row was read (second independent review).

pellham-grain: fixed charge coverage truly fails and the certificate says so. A misread input
is planted so the bank's calculation passes; the certificate is then read four ways.
"""
import json
from datetime import date
from decimal import Decimal as D

import pytest
from app.agents.certificate import read_certificate
from app.agents.llm import LLMResponse, ScriptedClient
from app.domain.covenant_service import governing_terms, run_covenant_tests
from app.domain.credit import Borrower, Facility
from app.domain.documents import Document
from app.domain.facts import Fact
from app.domain.facts_service import add_fact, current_fact
from app.domain.monitoring import WorkItem
from sqlalchemy import select
from support.agent_book import book, book_db  # noqa: F401

PERIOD = date(2026, 9, 30)
HONEST = [
    {"covenant_id": "fccr", "page": 1, "printed_label": "Fixed Charge Coverage Ratio", "actual_printed": "1.28x",
     "required_printed": "Not less than 1.35x", "compliance_printed": "No"},
    {"covenant_id": "total_leverage", "page": 1, "printed_label": "Total Leverage Ratio", "actual_printed": "2.04x",
     "required_printed": "Not more than 2.40x", "compliance_printed": "Yes"},
]


def variant(name):
    rows = json.loads(json.dumps(HONEST))
    if name == "flag taken from the next row (label fragment 'Ratio')":
        rows[0].update(printed_label="Ratio", compliance_printed="Yes")
    elif name == "flag and requirement from the next row (fragment 'Ratio')":
        rows[0].update(printed_label="Ratio", compliance_printed="Yes", required_printed="Not more than 2.40x")
    elif name == "flag not reported":
        rows[0].update(compliance_printed="")
    return rows


@pytest.mark.parametrize("name", ["honest", "flag taken from the next row (label fragment 'Ratio')",
                                  "flag and requirement from the next row (fragment 'Ratio')", "flag not reported"])
def test_a_certificate_showing_a_breach_reaches_a_person_however_its_row_was_read(book, name):  # noqa: F811
    db, _ = book
    borrower = db.execute(select(Borrower).where(Borrower.code == "pellham-grain")).scalar_one()
    facility = db.execute(select(Facility).where(Facility.borrower_id == borrower.id)).scalars().first()
    _, version = governing_terms(db, facility, PERIOD)
    ids = [c.id for c in version.terms.covenants]
    fccr = next(i for i in ids if "fixed" in i or "fccr" in i)
    lev = next(i for i in ids if "lev" in i)
    rows = variant(name)
    rows[0]["covenant_id"], rows[1]["covenant_id"] = fccr, lev
    # the seeded reading of this certificate is set aside so that this reading is the only one
    for f in db.execute(select(Fact).where(Fact.borrower_id == borrower.id, Fact.key.like("cert.%"),
                                           Fact.period_end == PERIOD)).scalars():
        f.status = "rejected"
    # step 1: the slipped misread. Scheduled principal for the nine months is stored at the quarter's amount
    old = current_fact(db, borrower.id, "sup.scheduled_principal", PERIOD, 9)
    ifs = db.execute(select(Document).where(Document.borrower_id == borrower.id, Document.doc_type == "interim_statements",
                                            Document.period_end == PERIOD)).scalars().first()
    add_fact(db, borrower_id=borrower.id, key="sup.scheduled_principal", period_end=PERIOD, months=9,
             value=old.value / 3, kind="extracted", status="verified", document_id=ifs.id, page=5,
             quote="1,290", label_text="Scheduled principal payments on term debt")
    doc = db.execute(select(Document).where(Document.borrower_id == borrower.id, Document.doc_type == "compliance_certificate",
                                            Document.period_end == PERIOD)).scalars().first()
    answer = {"rows": rows, "scale_statement": "Dollar amounts in this certificate are presented in thousands of U.S. dollars.",
              "scale_page": 1, "notes": []}
    llm = ScriptedClient([LLMResponse(content=[{"type": "text", "text": json.dumps(answer)}], stop_reason="end_turn")])
    before = {w.id for w in db.execute(select(WorkItem).where(WorkItem.borrower_id == borrower.id)).scalars()}
    reading = read_certificate(db, borrower=borrower, document=doc, period_end=PERIOD, terms=version.terms, cycle=None, llm=llm)
    tests = run_covenant_tests(db, borrower=borrower, facility=facility, period_end=PERIOD)
    t = next(x for x in tests if x.covenant_id == fccr)
    flag = current_fact(db, borrower.id, f"cert.{fccr}.in_compliance", PERIOD, 0)
    thr = current_fact(db, borrower.id, f"cert.{fccr}.threshold", PERIOD, 0)
    new = [(w.item_type, w.severity) for w in db.execute(select(WorkItem).where(WorkItem.borrower_id == borrower.id)).scalars()
           if w.id not in before]
    assert t.passed is True and ("covenant.reported_breach_unconfirmed", "high") in new, (name, new)
    if "fragment" in name:
        # the flag from the neighbouring row is not stored as this covenant's
        assert flag is None and ("fccr", "compliance_unverified") in [
            (u.get("covenant_id"), u["reason"]) for u in reading.unverified] or flag is None
    else:
        assert flag is not None and flag.value == 0 and flag.quote == "No"  # read from the row by code
    assert thr is None or thr.value == D("1.35")
