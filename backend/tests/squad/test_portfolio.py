from datetime import date
from decimal import Decimal

from app.domain.facts_service import add_fact
from app.domain.lessons import record_lesson
from app.domain.work_items import raise_item
from app.domain.workflow import open_cycle
from app.squad import client_file
from app.squad.portfolio import build_portfolio, lessons_for
from app.squad.questions import raise_question
from app.squad.threads import build_thread

from .conftest import sign_in

END = date(2026, 10, 31)


def _venture(db, code, name, runway=None, note=None):
    """A venture client whose runway is read where the covenants view reads it: the live runway covenant test."""
    from app.domain.credit import Borrower, Facility
    from app.domain.monitoring import CovenantTest
    b = Borrower(code=code, name=name, template_id="vc-1")
    db.add(b)
    db.flush()
    open_cycle(db, borrower_id=b.id, period_end=END, months=1, cycle_type="monthly")
    fac = Facility(borrower_id=b.id, code=f"{code}-TL", name="Term loan", facility_type="term_loan",
                   commitment=Decimal("1000000"))
    db.add(fac)
    db.flush()
    fact = None
    if runway is not None:
        fact = add_fact(db, borrower_id=b.id, key="cov.min_runway_months.value", period_end=END, months=0,
                        value=Decimal(runway), kind="seeded", unit="months", status="verified")
    if fact is not None or note is not None:
        db.add(CovenantTest(borrower_id=b.id, facility_id=fac.id, covenant_id="min_runway_months",
                            covenant_name="Runway", period_end=END, value_fact_id=fact.id if fact else None,
                            value=fact.value if fact else None, outcome="pass" if fact else "not_meaningful",
                            note=note))
        db.flush()
    return b


def test_venture_clients_are_ordered_by_runway_lowest_first_unmeasured_last(db, world):
    long_ = _venture(db, "LNG", "Longwater Robotics, Inc.", "22.5")
    short = _venture(db, "SHT", "Shortfield Bio, Inc.", "7.1")
    none_ = _venture(db, "NON", "Nonesuch Analytics, Inc.")
    _venture(db, "CFP", "Cashflow Positive Labs, Inc.", note="not_meaningful_cash_flow_positive")
    short.analyst_id = world["analyst"].id
    raise_item(db, borrower_id=short.id, item_type="test.portfolio", title="t", question="Is this fine?",
               allowed_decisions=["yes"])
    out = build_portfolio(db, world["analyst"])
    venture = next(s for s in out["sections"] if s["template_id"] == "vc-1")
    codes = [r["code"] for r in venture["rows"]]
    # measured lowest first, then cash-flow positive (the safest), then nothing measured
    assert codes.index("SHT") < codes.index("LNG") < codes.index("CFP") < codes.index("NON")
    row = next(r for r in venture["rows"] if r["code"] == "SHT")
    assert row["mine"] is True and row["open"] == 1 and row["analyst"] == "Priya Raman"
    assert next(r for r in venture["rows"] if r["code"] == "NON")["measure"]["points"][-1]["fact"] is None
    assert none_.id and long_.id


def test_the_order_is_the_client_files_latest_point_for_every_client(db, world):
    _venture(db, "LNG", "Longwater Robotics, Inc.", "22.5")
    _venture(db, "SHT", "Shortfield Bio, Inc.", "7.1")
    out = build_portfolio(db, world["analyst"])
    from app.domain.credit import Borrower
    from sqlalchemy import select
    for section in out["sections"]:
        for r in section["rows"]:
            b = db.execute(select(Borrower).where(Borrower.code == r["code"])).scalar_one()
            assert r["measure"] == client_file.measure_series(db, b)


def test_lessons_are_listed_with_who_wrote_them_and_show_on_a_later_ask(db, world):
    record_lesson(db, borrower_id=world["borrower"].id, topic="line_mapping", text="Recurring revenue here is ARR.",
                  written_by=world["analyst"].id, tag="map_to_arr")
    rows = lessons_for(db, world["borrower"].id)
    assert rows[0]["text"] == "Recurring revenue here is ARR." and rows[0]["by"] == "Priya Raman"
    raise_question(db, borrower_id=world["borrower"].id, title="Map a line", question="ARR or MRR?",
                   topic="line_mapping", options=[{"id": "map_to_arr", "label": "ARR", "evidence": "Annual."},
                                                  {"id": "map_to_mrr", "label": "MRR", "evidence": "Monthly."}])
    ask = next(m for m in build_thread(db, world["borrower"].id, world["analyst"])["messages"] if m["type"] == "ask")
    assert [h["text"] for h in ask["habits"]] == ["Recurring revenue here is ARR."]


def test_portfolio_and_lessons_endpoints(db, client, world):
    db.commit()
    sign_in(client, "priya.raman")
    out = client.get("/api/v1/me/portfolio").json()
    assert {s["template_id"] for s in out["sections"]} <= {"vc-1", "ci-1"}
    assert client.get(f"/api/v1/borrowers/{world['borrower'].id}/lessons").json() == []
