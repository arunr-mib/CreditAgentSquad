"""The Copilot: read-only tools over a seeded book, and the guardrail pass over its answers.
Every model response here is scripted; no model is called."""
import json
import os
import subprocess
import sys
import uuid
from datetime import date
from pathlib import Path

import pytest
from app.agents import copilot_tools as ct
from app.agents.tools import Scope, ToolContext
from app.core.config import get_settings
from app.domain import hooks  # noqa: F401
from app.domain.agents import AgentRun
from app.domain.credit import Borrower
from app.domain.documents import Document, DocumentPage
from app.domain.facts import Fact
from app.domain.monitoring import CovenantTest
from app.seed_book import seed_book
from sqlalchemy import select
from sqlalchemy.orm import Session

REPO = Path(__file__).resolve().parents[3]
BORROWERS = ["kestrel-bay-packaging", "vantry-freight", "briarstone-beverage", "sablewood-dental"]
Q3 = date(2026, 9, 30)


@pytest.fixture(scope="module")
def book_conn(engine, tmp_path_factory):
    """Four borrowers of the synthetic book, seeded once for the module inside a transaction
    that is rolled back at the end."""
    out = tmp_path_factory.mktemp("book")
    subprocess.run([sys.executable, "-m", "synthetic.generate", "--out", str(out)], cwd=REPO, check=True,
                   capture_output=True)
    os.environ["FILE_STORE_DIR"] = str(tmp_path_factory.mktemp("files"))
    get_settings.cache_clear()
    conn = engine.connect()
    outer = conn.begin()
    seed = Session(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
    seed_book(seed, root=out, current="seeded", only=BORROWERS)
    seed.commit()
    seed.close()
    yield conn
    outer.rollback()
    conn.close()
    os.environ.pop("FILE_STORE_DIR", None)
    get_settings.cache_clear()


@pytest.fixture()
def db(book_conn):
    """A session per test over the seeded book; whatever the test writes is rolled back."""
    savepoint = book_conn.begin_nested()
    session = Session(bind=book_conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        savepoint.rollback()


def borrower(db, code) -> Borrower:
    return db.execute(select(Borrower).where(Borrower.code == code)).scalar_one()


class Desk:
    """Calls Copilot tools through the gateway the way the runtime does."""

    def __init__(self, db, borrower_id=None):
        run = AgentRun(agent_name="copilot", agent_version="test", model="none", task="tools")
        db.add(run)
        db.flush()
        self.ctx = ToolContext(db=db, scope=Scope(borrower_id=borrower_id), run=run, state={})
        self.gateway = ct.copilot_gateway()

    def call(self, tool, /, **inp):
        return self.gateway.call(self.ctx, tool, inp, allowed=ct.TOOL_NAMES)

    def ok(self, tool, /, **inp):
        outcome = self.call(tool, **inp)
        assert not outcome.refused, outcome.content
        json.dumps(outcome.content, default=str)  # every result must go back to the model as JSON
        return outcome.content

    @property
    def facts(self):
        return ct.facts_seen(self.ctx)


def fact_ids_in(node) -> set[str]:
    found = set()
    if isinstance(node, dict):
        if isinstance(node.get("fact_id"), str):
            found.add(node["fact_id"])
        for value in node.values():
            found |= fact_ids_in(value)
    elif isinstance(node, list):
        for value in node:
            found |= fact_ids_in(value)
    return found


# ---- tools ----------------------------------------------------------------------------------

def test_no_copilot_tool_writes_or_takes_an_identifier_for_scope():
    assert all(not tool.writes for tool in ct.COPILOT_TOOLS)
    assert {"list_documents", "search_documents", "read_page", "find_borrower", "portfolio_query"} <= set(ct.TOOL_NAMES)
    for definition in ct.copilot_gateway().definitions(ct.TOOL_NAMES):
        props = set(definition["input_schema"]["properties"])
        assert not props & {"borrower_id", "borrower", "facility_id", "loan_id", "cycle_id", "user_id"}, definition["name"]
        assert definition["strict"] is True


def test_borrower_tools_refuse_until_a_borrower_is_open(db):
    desk = Desk(db)
    for name, inp in (("borrower_overview", {}), ("covenant_tests", {"period_end": None}), ("signals", {}),
                      ("work_items", {}), ("terms", {}), ("list_documents", {}),
                      ("metrics", {"names": ["leverage"]})):
        outcome = desk.call(name, **inp)
        assert outcome.refused and "open a borrower" in outcome.content["error"], name
    # a borrower id cannot be passed in: the input is refused before any handler runs
    kestrel = borrower(db, "kestrel-bay-packaging")
    smuggled = desk.call("covenant_tests", period_end=None, borrower_id=str(kestrel.id))
    assert smuggled.refused and "Extra inputs" in smuggled.content["error"]
    assert desk.facts == {}


def test_find_borrower_opens_only_a_borrower_that_exists(db):
    desk = Desk(db)
    missing = desk.ok("find_borrower", name="Zephyr Holdings")
    assert missing["found"] is False and missing["opened"] is None and "not found" in missing["message"]
    assert desk.call("borrower_overview").refused
    found = desk.ok("find_borrower", name="kestrel bay")
    assert found["opened"]["name"] == "Kestrel Bay Packaging Corp."
    assert desk.ok("borrower_overview")["name"] == "Kestrel Bay Packaging Corp."
    # the full legal name and the code also match; an id typed by the model does not
    assert desk.ok("find_borrower", name="Vantry Freight Systems, LLC")["opened"]["name"].startswith("Vantry")
    assert desk.ok("find_borrower", name=str(borrower(db, "sablewood-dental").id))["found"] is False


def test_a_scoped_conversation_cannot_be_moved_to_another_borrower(db):
    kestrel = borrower(db, "kestrel-bay-packaging")
    desk = Desk(db, borrower_id=kestrel.id)
    assert desk.ok("borrower_overview")["name"] == kestrel.name
    moved = desk.call("find_borrower", name="Vantry")
    assert moved.refused and "another borrower" in moved.content["error"]
    assert desk.ok("covenant_tests", period_end=None)["tests"][0]["covenant"] in ("Current Ratio", "Total Leverage Ratio")


def test_overview_and_covenant_tests_return_facts_with_ids(db):
    kestrel = borrower(db, "kestrel-bay-packaging")
    desk = Desk(db, borrower_id=kestrel.id)
    overview = desk.ok("borrower_overview")
    assert overview["risk_rating"]["in_words"] == "six" and len(overview["loans"]) == 2
    assert overview["latest_cycle"]["period_end"] == "2026-09-30"
    assert overview["open_work_items"]["items"][0]["type"] == "covenant.reported_mismatch"
    assert overview["exposure_from_the_system_of_record"]["revolver_commitment"]["value"] == "15500000"

    latest = desk.ok("covenant_tests", period_end=None)
    assert latest["period_end"] == "2026-09-30" and "2025-03-31" in latest["periods_tested"]
    leverage = next(t for t in latest["tests"] if t["covenant"] == "Total Leverage Ratio")
    assert leverage["outcome"] == "breach_reported_compliant" and leverage["passed"] is False
    assert leverage["value"]["value"] == "2.6" and leverage["threshold"]["value"] == "2.5"
    assert leverage["headroom_pct"]["value"] == "-0.04" and leverage["reported_on_certificate"]["value"] == "2.41"
    stored = db.get(CovenantTest, db.execute(select(CovenantTest.id).where(
        CovenantTest.calc_run_id == uuid.UUID(leverage["calculation_id"]))).scalar_one())
    assert str(stored.value_fact_id) == leverage["value"]["fact_id"]
    earlier = desk.ok("covenant_tests", period_end="2026-06-30")
    assert all(t["outcome"] == "compliant" for t in earlier["tests"])
    assert desk.ok("covenant_tests", period_end="2019-03-31")["tests"] == []
    assert desk.call("covenant_tests", period_end="last quarter").refused
    # every fact id a tool returned is in scope for the answer, and nothing else is
    assert fact_ids_in(overview) | fact_ids_in(latest) | fact_ids_in(earlier) == set(desk.facts)


def test_calculation_breakdown_names_every_input_fact_and_stays_inside_the_borrower(db):
    kestrel, vantry = borrower(db, "kestrel-bay-packaging"), borrower(db, "vantry-freight")
    desk = Desk(db, borrower_id=kestrel.id)
    leverage = next(t for t in desk.ok("covenant_tests", period_end=None)["tests"]
                    if t["covenant"] == "Total Leverage Ratio")
    calc = desk.ok("calculation_breakdown", calculation_id=leverage["calculation_id"])
    assert calc["formula"] == "covenant.total_leverage" and len(calc["inputs"]) == 16
    assert all(i["fact"]["fact_id"] in desk.facts for i in calc["inputs"])
    assert {"added", "subtracted"} == {i["role"] for i in calc["inputs"]}
    assert leverage["value"]["fact_id"] in {r["fact_id"] for r in calc["results"]}
    other = db.execute(select(CovenantTest.calc_run_id).where(
        CovenantTest.borrower_id == vantry.id, CovenantTest.calc_run_id.is_not(None))).scalars().first()
    assert desk.call("calculation_breakdown", calculation_id=str(other)).refused
    assert desk.call("calculation_breakdown", calculation_id="not-an-id").refused


def test_spread_lines_and_metrics(db):
    kestrel = borrower(db, "kestrel-bay-packaging")
    desk = Desk(db, borrower_id=kestrel.id)
    listing = desk.ok("spread_lines", keys=[], period_ends=[])
    assert {"is.revenue", "bs.cash"} <= {line["key"] for line in listing["lines_available"]}
    lines = desk.ok("spread_lines", keys=["is.revenue", "bs.cash"], period_ends=["2026-09-30", "2019-03-31"])
    revenue = lines["lines"][0]["values"]
    assert revenue[0]["fact"]["fact_id"] in desk.facts and revenue[0]["source"]["kind"] == "seeded"
    assert revenue[1]["fact"] is None and "not on file" in revenue[1]["note"]
    assert desk.call("spread_lines", keys=["is.unicorns"], period_ends=["2026-09-30"]).refused

    before = db.execute(select(Fact).where(Fact.borrower_id == kestrel.id, Fact.key.like("metric.%"))).scalars().all()
    metrics = desk.ok("metrics", names=["leverage", "ebitda", "liquidity"], period_end=None)
    by_name = {m["metric"]: m for m in metrics["metrics"]}
    assert metrics["period_end"] == "2026-09-30" and by_name["leverage"]["fact"]["value"] == "2.6"
    assert by_name["ebitda"]["fact"]["value"] == "12743000" and by_name["ebitda"]["calculation_id"]
    stored = db.get(Fact, uuid.UUID(by_name["leverage"]["fact"]["fact_id"]))
    assert stored.key == "metric.leverage" and stored.kind == "calculated" and stored.calc_run_id is not None
    # asking again reuses the stored fact; a metric that cannot be measured is null, never zero
    again = desk.ok("metrics", names=["leverage"], period_end="2026-09-30")
    assert again["metrics"][0]["fact"]["fact_id"] == by_name["leverage"]["fact"]["fact_id"]
    unmeasured = desk.ok("metrics", names=["leverage"], period_end="2019-03-31")["metrics"][0]
    assert unmeasured["fact"] is None and "not zero" in unmeasured["note"] and unmeasured["missing"]
    assert desk.call("metrics", names=["vibes"], period_end=None).refused
    after = db.execute(select(Fact).where(Fact.borrower_id == kestrel.id, Fact.key.like("metric.%"))).scalars().all()
    assert len(after) - len(before) <= 3


def test_signals_work_items_calendar_terms_and_borrowing_base(db):
    vantry = borrower(db, "vantry-freight")
    desk = Desk(db, borrower_id=vantry.id)
    signals = desk.ok("signals")
    assert {"covenant_headroom_low", "leverage_increase", "ebitda_margin_decline"} <= {s["rule"] for s in signals["signals"]}
    low = next(s for s in signals["signals"] if s["rule"] == "covenant_headroom_low")
    assert low["facts"][0]["key"] == "cov.total_leverage.headroom_pct" and low["facts"][0]["fact_id"] in desk.facts

    items = desk.ok("work_items")["work_items"]
    mismatch = next(i for i in items if i["type"] == "covenant.reported_mismatch")
    assert mismatch["severity"] == "critical" and "waiver_requested" in mismatch["decisions_a_person_may_take"]
    assert len(mismatch["evidence_facts"]) == 2 and mismatch["calculation_id"]

    calendar = desk.ok("reporting_calendar", outstanding_only=True)
    assert calendar["as_of"] == "2026-11-17" and all(o["status"] in ("due", "overdue") for o in calendar["obligations"])
    assert "days_late" not in json.dumps(calendar["obligations"])

    terms = desk.ok("terms")
    loan = terms["loans"][0]
    assert loan["versions"][0]["status"] == "approved" and loan["versions"][0]["governs_the_latest_period"]
    clause = loan["shown"]["covenants"][0]["clauses"][0]
    page = db.execute(select(DocumentPage).where(DocumentPage.document_id == uuid.UUID(clause["document_id"]),
                                                 DocumentPage.page_number == clause["page"])).scalar_one()
    assert clause["quote"] in " ".join(page.text.split())
    assert desk.ok("terms", version=9)["loans"] == []

    assert desk.ok("borrowing_base_review", period_end=None)["review"] is None
    briar = Desk(db, borrower_id=borrower(db, "briarstone-beverage").id)
    review = briar.ok("borrowing_base_review", period_end=None)["review"]
    assert review["outcome"] == "over_advance" and review["over_advanced"] is True
    assert review["availability"]["value"] == "-81949" and review["availability"]["fact_id"] in briar.facts
    assert briar.ok("review_sheet")["review_sheet"] is None


def test_document_tools_read_the_open_borrower_only(db):
    desk = Desk(db)
    desk.ok("find_borrower", name="Kestrel Bay")
    docs = desk.ok("list_documents")["documents"]
    agreement = next(d for d in docs if d["type"] == "credit_agreement")
    hits = desk.ok("search_documents", query="Total Leverage Ratio exceed", document_type="credit_agreement")["hits"]
    assert hits and hits[0]["document_id"] == agreement["document_id"]
    assert "Total Leverage Ratio" in desk.ok("read_page", document_id=agreement["document_id"], page=hits[0]["page"])["text"]
    foreign = db.execute(select(Document.id).where(
        Document.borrower_id == borrower(db, "vantry-freight").id)).scalars().first()
    assert desk.call("read_page", document_id=str(foreign), page=1).refused


def test_portfolio_query_needs_no_open_borrower(db):
    desk = Desk(db)
    tight = desk.ok("portfolio_query", headroom_below_percent=10, rank_by="headroom")
    names = [row["borrower"] for row in tight["borrowers"]]
    assert names == ["Vantry Freight Systems, LLC", "Kestrel Bay Packaging Corp."] and tight["matched_in_words"] == "two"
    vantry = tight["borrowers"][0]
    assert [c["covenant"] for c in vantry["covenants"]] == ["Total Leverage Ratio"]
    assert vantry["covenants"][0]["headroom_pct"]["value"] == "-0.045"
    assert vantry["covenants"][0]["headroom_pct"]["fact_id"] in desk.facts
    kestrel = tight["borrowers"][1]
    assert [c["covenant"] for c in kestrel["covenants"]] == ["Total Leverage Ratio", "Current Ratio"]

    breaches = desk.ok("portfolio_query", covenant_status="breach", rank_by="exposure")
    assert [row["borrower"] for row in breaches["borrowers"]] == ["Kestrel Bay Packaging Corp.", "Vantry Freight Systems, LLC"]
    everyone = desk.ok("portfolio_query", rank_by="name", limit=2)
    assert everyone["matched_in_words"] == "four" and len(everyone["borrowers"]) == 2
    critical = desk.ok("portfolio_query", open_items_only=True, rank_by="open_items")
    assert critical["borrowers"][0]["open_work_items"]["most_severe"] == "critical"
    assert desk.ok("portfolio_query", covenant_status="cannot_test")["borrowers"] == []
    assert desk.call("portfolio_query", headroom_below_percent=250).refused
    # no figure is returned without the id of its stored fact
    assert all(isinstance(row["exposure_from_the_system_of_record"], dict) for row in everyone["borrowers"])
    assert "borrower_id" not in desk.ctx.state
