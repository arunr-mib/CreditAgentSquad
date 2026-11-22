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
    codes = [r["code"] for r in venture["rows"] if r["code"] in {"SHT", "LNG", "NON", "CFP"}]
    # measured lowest first, then "Not measured" (not knowing is a risk), then cash-flow positive last
    assert codes == ["SHT", "LNG", "NON", "CFP"]
    row = next(r for r in venture["rows"] if r["code"] == "SHT")
    assert row["mine"] is True and row["open"] == 1 and row["analyst"] == "Priya Raman"
    assert next(r for r in venture["rows"] if r["code"] == "NON")["measure"]["points"][-1]["fact"] is None
    assert none_.id and long_.id


def test_every_row_carries_the_client_files_own_measure(db, world):
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


def _ci(db, code, name, headrooms):
    """A C&I client: one live test per covenant, each with its stored headroom fact."""
    from app.domain.credit import Borrower, Facility
    from app.domain.monitoring import CovenantTest
    b = Borrower(code=code, name=name, template_id="ci-1")
    db.add(b)
    db.flush()
    open_cycle(db, borrower_id=b.id, period_end=END, months=1, cycle_type="monthly")
    fac = Facility(borrower_id=b.id, code=f"{code}-TL", name="Term loan", facility_type="term_loan",
                   commitment=Decimal("1000000"))
    db.add(fac)
    db.flush()
    for cov, value in headrooms.items():
        add_fact(db, borrower_id=b.id, key=f"cov.{cov}.headroom_pct", period_end=END, months=0, value=Decimal(value),
                 kind="seeded", unit="pct", status="verified")
        db.add(CovenantTest(borrower_id=b.id, facility_id=fac.id, covenant_id=cov, covenant_name=cov, period_end=END,
                            outcome="pass"))
    db.flush()
    return b


def test_ci_clients_are_ordered_by_tightest_headroom_a_breach_first_and_the_order_can_fail(db, world):
    _ci(db, "AAA", "Alderwick Foods, Inc.", {"leverage": "0.40", "fccr": "0.25"})
    _ci(db, "BBB", "Bramblecote Tooling, Inc.", {"leverage": "-0.05", "fccr": "0.9"})
    _ci(db, "CCC", "Cinderfall Textiles, Inc.", {"leverage": "0.0"})
    _ci(db, "DDD", "Dunmere Plastics, Inc.", {})
    out = build_portfolio(db, world["analyst"])
    section = next(s for s in out["sections"] if s["template_id"] == "ci-1")
    assert [r["code"] for r in section["rows"] if r["code"] != "ZZZ"] == ["BBB", "CCC", "AAA", "DDD"]


def test_open_cases_in_the_nav_and_open_in_the_portfolio_are_one_count(db, world):
    from datetime import timedelta

    from app.core import clock
    from app.domain.funding import FundingEvent
    from app.domain.monitoring import Signal
    from app.domain.terms import ReportingObligation
    from app.squad.briefing import build_briefing
    worked = _venture(db, "WRK", "Workedon Labs, Inc.", "10.0")
    signalled = _venture(db, "SIG", "Signalled Labs, Inc.", "11.0")
    funded = _venture(db, "FND", "Funded Labs, Inc.", "12.0")
    late = _venture(db, "LTE", "Latereport Labs, Inc.", "13.0")
    for n in (1, 2):
        raise_item(db, borrower_id=worked.id, item_type=f"test.portfolio{n}", title="t", question="Is this fine?",
                   allowed_decisions=["yes"])
    today = clock.today(db)
    db.add(Signal(borrower_id=signalled.id, period_end=today, rule_id="burn_rising", rule_version="1", severity="high",
                  status="open"))
    db.add(FundingEvent(borrower_id=funded.id, kind="equity_round", status="expected", amount=Decimal("1000000"),
                        expected_close=today + timedelta(days=5)))
    from app.domain.credit import Facility
    from sqlalchemy import select
    fac = db.execute(select(Facility).where(Facility.borrower_id == late.id)).scalar_one()
    db.add(ReportingObligation(borrower_id=late.id, facility_id=fac.id, requirement_id="q", document_type="mrr_report",
                               period_end=today - timedelta(days=60), due_date=today - timedelta(days=5),
                               status="overdue"))
    db.flush()
    portfolio = {r["code"]: r["open"] for s in build_portfolio(db, world["analyst"])["sections"] for r in s["rows"]}
    nav = {c["code"]: c["open"] for c in build_briefing(db, world["analyst"])["open_clients"]}
    assert portfolio["WRK"] == 2 and portfolio["SIG"] == 0 and portfolio["FND"] == 0 and portfolio["LTE"] == 0
    assert nav == {code: n for code, n in portfolio.items() if n}  # the nav lists exactly the clients with open cases
    assert "SIG" not in nav and "FND" not in nav and "LTE" not in nav


def test_the_portfolio_says_whether_the_viewer_owns_any_client(db, world):
    world["borrower"].analyst_id = world["analyst"].id
    assert build_portfolio(db, world["analyst"])["owns_clients"] is True
    assert build_portfolio(db, world["officer"])["owns_clients"] is False


def test_an_ask_shows_only_habits_taught_before_it_was_asked(db, world):
    options = [{"id": "a", "label": "A", "evidence": "x"}, {"id": "b", "label": "B", "evidence": "y"}]
    first = raise_question(db, borrower_id=world["borrower"].id, title="First", question="First?", topic="line_mapping",
                           options=options)
    record_lesson(db, borrower_id=world["borrower"].id, topic="line_mapping", text="Taught after the first ask.",
                  written_by=world["analyst"].id, tag="a")
    second = raise_question(db, borrower_id=world["borrower"].id, title="Second", question="Second?",
                            topic="line_mapping", options=options)
    asks = {m["work_item_id"]: m for m in build_thread(db, world["borrower"].id, world["analyst"])["messages"]
            if m["type"] == "ask"}
    assert asks[str(first.id)]["habits"] == []
    assert [h["text"] for h in asks[str(second.id)]["habits"]] == ["Taught after the first ask."]


def test_a_client_on_a_template_with_no_section_is_listed_under_other_clients(db, world, monkeypatch):
    """Final review M15: a template the portfolio has no section for (here ci-1, with the section taken away) is
    listed under "Other clients", never dropped."""
    from app.squad import portfolio

    monkeypatch.setattr(portfolio, "SECTIONS", (("vc-1", "Innovation clients", "Runway (months)"),))
    world["other"].template_id = "ci-1"
    db.flush()
    out = build_portfolio(db, world["analyst"])
    other = next(s for s in out["sections"] if s["template_id"] == "other")
    assert other["title"] == "Other clients" and [r["name"] for r in other["rows"]] == [world["other"].name]
