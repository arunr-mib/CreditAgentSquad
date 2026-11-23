"""A cycle never advances or stalls in silence, and every decision a person is offered does
something: found by an independent review, each case here failed before its fix."""
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal as D

import pymupdf
import pytest
from app.agents import terms_agent
from app.calc import template
from app.core.config import get_settings
from app.core.ledger import LedgerEvent
from app.domain import corrections, hooks, stages, workflow  # noqa: F401
from app.domain.covenant_service import run_covenant_tests
from app.domain.credit import Borrower, Facility
from app.domain.documents_service import ingest_pdf
from app.domain.facts_service import add_fact, current_fact
from app.domain.monitoring import STAGES, CovenantTest, WorkItem
from app.domain.org import User
from app.domain.terms import TermsVersion
from app.domain.terms_service import propose_terms
from app.domain.work_items import raise_item
from app.guardrails.numbers import parse_printed_figure
from sqlalchemy import select
from support.statement_pdf import ABSENT, COMPUTED, PAGES, PRIOR_FYE_CASH_THOUSANDS, build_pdf

FY = date(2025, 12, 31)
Q3 = date(2026, 9, 30)


def cite(section):
    return [{"document_id": "agreement", "section": section, "page": 7, "quote": "..."}]


def terms():
    return {
        "definitions": {"ebitda": {"base": "ebitda", "addbacks": []}},
        "covenants": [
            {"id": "leverage", "name": "Total Leverage Ratio", "archetype": "leverage",
             "params": {"debt": "total_debt", "ebitda": "ebitda"},
             "test": {"operator": "<=", "threshold": "3.50", "unit": "ratio"},
             "measurement": {"basis": "ttm", "frequency": "quarterly"},
             "rounding": {"dp": 2, "mode": "half_up"}, "citations": cite("7.12")},
        ],
        "reporting_requirements": [], "borrowing_base": None,
    }


# leverage = (3,000,000 + 1,200,000 + 8,300,000 + 0) / (2,000,000 + 900,000 + 600,000 + 1,100,000) = 2.72
FLOWS = {"is.net_income": "2000000", "is.interest_expense": "900000", "is.income_tax_expense": "600000",
         "is.depreciation_amortization": "1100000"}
POINTS = {"bs.revolver": "3000000", "bs.cpltd": "1200000", "bs.long_term_debt": "8300000",
          "bs.subordinated_debt": "0"}


def person(db, role):
    u = User(email=f"{uuid.uuid4().hex}@x.example", name=f"A {role}", role=role, password_hash="x")
    db.add(u)
    db.flush()
    if role == "analyst":  # the test's analyst owns the test's client: an analyst acts only on her own clients (owner answer 9)
        from app.domain.credit import Borrower
        for b in db.query(Borrower).filter(Borrower.analyst_id.is_(None)):
            b.analyst_id = u.id
        db.flush()
    return u


def open_items(db, item_type=None):
    query = select(WorkItem).where(WorkItem.status == "open").order_by(WorkItem.created_at)
    if item_type:
        query = query.where(WorkItem.item_type == item_type)
    return list(db.execute(query).scalars())


def stage_status(db, cycle, stage):
    return next(s.status for s in workflow.stages(db, cycle) if s.stage == stage)


def events(db, action):
    return list(db.execute(select(LedgerEvent).where(LedgerEvent.action == action).order_by(LedgerEvent.seq)).scalars())


@pytest.fixture()
def world(db, tmp_path, monkeypatch):
    monkeypatch.setenv("FILE_STORE_DIR", str(tmp_path))
    get_settings.cache_clear()

    class NoModel:
        def create(self, request):
            raise AssertionError("no model call is expected in this test")

    monkeypatch.setattr(stages, "LLM_FACTORY", NoModel)
    borrower = Borrower(code="HTD", name="Harrowgate Tool & Die, Inc.")
    db.add(borrower)
    db.flush()
    facility = Facility(borrower_id=borrower.id, code="HTD-TL", name="Term loan", facility_type="term_loan",
                        commitment=D("10000000"), origination_date=date(2024, 1, 15))
    db.add(facility)
    db.flush()
    yield borrower, facility
    get_settings.cache_clear()


def approve(db, row):
    row.status, row.approved_by, row.approved_at = "approved", person(db, "credit_officer").id, datetime.now(UTC)
    db.flush()


def add_terms(db, facility, status="approved", version=1):
    row = TermsVersion(facility_id=facility.id, version=version, status="proposed",
                       effective_from=date(2024, 1, 15), terms=terms(), prepared_by_type="agent",
                       prepared_by_id="terms@1")
    db.add(row)
    db.flush()
    if status == "approved":
        approve(db, row)
    return row


def cycle_at(db, borrower, stage, period_end=FY, months=12):
    cycle = workflow.open_cycle(db, borrower_id=borrower.id, period_end=period_end, months=months)
    for st in workflow.stages(db, cycle):
        if STAGES.index(st.stage) < STAGES.index(stage):
            st.status = "done"
    db.flush()
    return cycle


def run_stage(db, cycle):
    workflow.advance(db, cycle)
    workflow.run_next_job(db)


# ---- no approved terms ---------------------------------------------------------------------


def test_a_loan_with_no_approved_terms_stops_the_cycle_and_asks_a_person_once(db, world):
    borrower, facility = world
    add_terms(db, facility, status="proposed")
    cycle = cycle_at(db, borrower, "covenant_testing")
    run_stage(db, cycle)
    items = open_items(db, "covenant.cannot_test")
    assert len(items) == 1 and items[0].blocks_stage and "no approved terms" in items[0].title
    assert stage_status(db, cycle, "covenant_testing") == "needs_person" and cycle.stage == "covenant_testing"
    # looking again asks nothing new and keeps one record of the gap
    hooks._back_to_pending(db, items[0], "covenant_testing", person(db, "admin"))
    run_stage(db, cycle)
    assert len(open_items(db, "covenant.cannot_test")) == 1
    markers = db.execute(select(CovenantTest).where(CovenantTest.covenant_id == "*",
                                                    CovenantTest.superseded.is_(False))).scalars().all()
    assert len(markers) == 1


def test_a_loan_covered_by_a_sister_loans_approved_terms_raises_no_gap(db, world):
    borrower, facility = world
    revolver = Facility(borrower_id=borrower.id, code="HTD-RLOC", name="Revolver", facility_type="revolver",
                        commitment=D("5000000"))
    db.add(revolver)
    db.flush()
    add_terms(db, facility)  # one agreement, boarded on the term loan
    cycle = cycle_at(db, borrower, "covenant_testing")
    run_stage(db, cycle)
    assert db.execute(select(CovenantTest).where(CovenantTest.covenant_id == "*")).first() is None
    assert all("no approved terms" not in i.title for i in open_items(db))


def test_terms_approved_runs_the_tests_and_asks_again_while_nothing_governs(db, world, monkeypatch):
    borrower, facility = world
    for key, value in FLOWS.items():
        add_fact(db, borrower_id=borrower.id, key=key, period_end=FY, months=12, value=D(value), kind="seeded")
    for key, value in POINTS.items():
        add_fact(db, borrower_id=borrower.id, key=key, period_end=FY, months=0, value=D(value), kind="seeded")
    version = add_terms(db, facility, status="proposed")
    cycle = cycle_at(db, borrower, "covenant_testing")
    run_stage(db, cycle)
    officer = person(db, "credit_officer")
    first = open_items(db, "covenant.cannot_test")[0]
    # the person says the terms are approved, but they are not: the question comes straight back
    workflow.decide_work_item(db, first, user_id=officer.id, user_role=officer.role, decision="terms_approved")
    again = open_items(db, "covenant.cannot_test")
    assert first.status == "decided" and len(again) == 1 and again[0].id != first.id
    assert cycle.stage == "covenant_testing" and stage_status(db, cycle, "covenant_testing") == "needs_person"
    # once a version is approved the same decision tests the covenants
    approve(db, version)
    monkeypatch.setattr(workflow, "STAGE_HANDLERS", {})  # later stages are not under test
    workflow.decide_work_item(db, again[0], user_id=officer.id, user_role=officer.role, decision="terms_approved")
    live = db.execute(select(CovenantTest).where(CovenantTest.superseded.is_(False))).scalars().all()
    assert [(t.covenant_id, t.outcome, t.value) for t in live] == [("leverage", "compliant", D("2.72"))]
    assert open_items(db, "covenant.cannot_test") == []


# ---- a covenant that cannot be tested ---------------------------------------------------------


def untestable(db, borrower, facility):
    """Approved terms, but one input of the leverage test is not on file."""
    add_terms(db, facility)
    for key, value in FLOWS.items():
        if key != "is.interest_expense":
            add_fact(db, borrower_id=borrower.id, key=key, period_end=FY, months=12, value=D(value), kind="seeded")
    for key, value in POINTS.items():
        add_fact(db, borrower_id=borrower.id, key=key, period_end=FY, months=0, value=D(value), kind="seeded")
    tests = run_covenant_tests(db, borrower=borrower, facility=facility, period_end=FY)
    assert [t.outcome for t in tests] == ["cannot_test"]
    return tests[0], open_items(db, "covenant.cannot_test")[0]


def test_not_applicable_needs_a_reason_and_is_recorded_against_the_test(db, world):
    borrower, facility = world
    test, item = untestable(db, borrower, facility)
    analyst = person(db, "analyst")
    with pytest.raises(ValueError, match="needs a reason"):
        workflow.decide_work_item(db, item, user_id=analyst.id, user_role=analyst.role, decision="not_applicable")
    assert item.status == "open" and events(db, "covenant.judged_not_applicable") == []
    workflow.decide_work_item(db, item, user_id=analyst.id, user_role=analyst.role, decision="not_applicable",
                              reason="The covenant is suspended this quarter under the waiver on file.")
    judged = events(db, "covenant.judged_not_applicable")
    assert len(judged) == 1 and judged[0].entity_id == str(test.id) and judged[0].actor_id == str(analyst.id)
    assert judged[0].payload["judged_by"] == analyst.name and "waiver" in judged[0].payload["reason"]


def test_input_provided_is_checked_by_running_the_test_again(db, world):
    borrower, facility = world
    _, item = untestable(db, borrower, facility)
    analyst = person(db, "analyst")
    # nothing was provided: the decision is recorded, the test is run again and the question returns
    workflow.decide_work_item(db, item, user_id=analyst.id, user_role=analyst.role, decision="input_provided")
    again = open_items(db, "covenant.cannot_test")
    assert item.status == "decided" and len(again) == 1 and again[0].id != item.id
    assert "is.interest_expense" in again[0].question
    # the figure is now on file: the same decision produces the test result
    add_fact(db, borrower_id=borrower.id, key="is.interest_expense", period_end=FY, months=12, value=D("900000"),
             kind="seeded")
    workflow.decide_work_item(db, again[0], user_id=analyst.id, user_role=analyst.role, decision="input_provided")
    live = db.execute(select(CovenantTest).where(CovenantTest.superseded.is_(False))).scalars().all()
    assert [(t.outcome, t.value) for t in live] == [("compliant", D("2.72"))]
    assert open_items(db, "covenant.cannot_test") == []


# ---- a stage that fails -----------------------------------------------------------------------


@pytest.fixture()
def handlers(monkeypatch):
    table = {s: (lambda db, cycle, st: "done") for s in STAGES}
    monkeypatch.setattr(workflow, "STAGE_HANDLERS", table)
    return table


def test_a_failed_stage_asks_a_person_and_retry_runs_it_again(db, world, handlers):
    borrower, _ = world

    def boom(db, cycle, st):
        raise RuntimeError("model endpoint timed out")

    handlers["intake"] = boom
    cycle = workflow.open_cycle(db, borrower_id=borrower.id, period_end=Q3, months=9)
    workflow.advance(db, cycle)
    workflow.drain(db)
    for _ in range(3):  # ticking a failed cycle neither moves it nor asks twice
        workflow.tick(db)
        workflow.drain(db)
    items = open_items(db, "cycle.stage_failed")
    assert len(items) == 1 and items[0].blocks_stage and items[0].stage == "intake"
    assert "model endpoint timed out" in items[0].evidence["error"]
    assert items[0].allowed_decisions == ["retry", "escalate"] and stage_status(db, cycle, "intake") == "failed"
    failed = [e for e in events(db, "cycle.stage_changed") if e.payload["to"] == "failed"]
    assert len(failed) == 1 and "timed out" in failed[0].payload["error"]

    analyst = person(db, "analyst")
    handlers["intake"] = lambda db, cycle, st: "done"  # the cause is fixed
    workflow.decide_work_item(db, items[0], user_id=analyst.id, user_role=analyst.role, decision="retry")
    requeued = [e for e in events(db, "cycle.stage_changed")
                if e.payload["from"] == "failed" and e.payload["to"] == "pending"]
    assert len(requeued) == 1 and requeued[0].actor_id == str(analyst.id)
    workflow.drain(db)
    assert cycle.status == "closed" and open_items(db) == []


def test_escalating_a_failed_stage_needs_a_reason_and_goes_to_an_administrator(db, world, handlers):
    borrower, _ = world

    def boom(db, cycle, st):
        raise RuntimeError("extraction service unavailable")

    handlers["spreading"] = boom
    cycle = workflow.open_cycle(db, borrower_id=borrower.id, period_end=Q3, months=9)
    workflow.advance(db, cycle)
    workflow.drain(db)
    item = open_items(db, "cycle.stage_failed")[0]
    analyst, admin = person(db, "analyst"), person(db, "admin")
    with pytest.raises(ValueError, match="needs a reason"):
        workflow.decide_work_item(db, item, user_id=analyst.id, user_role=analyst.role, decision="escalate")
    workflow.decide_work_item(db, item, user_id=analyst.id, user_role=analyst.role, decision="escalate",
                              reason="Failed twice this morning; needs someone with access to the service.")
    escalated = open_items(db, "cycle.stage_failed")
    assert len(escalated) == 1 and escalated[0].id != item.id and escalated[0].severity == "critical"
    assert escalated[0].evidence["escalated_by"] == str(analyst.id) and escalated[0].blocks_stage
    assert stage_status(db, cycle, "spreading") == "failed" and cycle.status == "open"
    with pytest.raises(PermissionError):
        workflow.decide_work_item(db, escalated[0], user_id=analyst.id, user_role=analyst.role, decision="retry")
    workflow.decide_work_item(db, escalated[0], user_id=admin.id, user_role=admin.role, decision="retry")
    workflow.drain(db)  # it fails again, and asks again
    assert stage_status(db, cycle, "spreading") == "failed" and len(open_items(db, "cycle.stage_failed")) == 1


def test_a_handler_that_returns_nonsense_fails_its_stage_instead_of_leaving_it_running(db, world, handlers):
    borrower, _ = world
    handlers["intake"] = lambda db, cycle, st: "finished"
    cycle = workflow.open_cycle(db, borrower_id=borrower.id, period_end=Q3, months=9)
    workflow.advance(db, cycle)
    workflow.drain(db)
    assert stage_status(db, cycle, "intake") == "failed" and len(open_items(db, "cycle.stage_failed")) == 1


# ---- a scanned statement keyed by hand -------------------------------------------------------


def scanned_pdf() -> bytes:
    pdf = pymupdf.open(stream=build_pdf(), filetype="pdf")
    pdf.new_page()  # a page with no text layer
    return pdf.tobytes()


def key_statement(db, borrower, analyst, skip=()):
    """Key every input line of the test statement in whole dollars, as the facts route does."""
    for rows in PAGES.values():
        for key, _label, printed, _prior in rows:
            if key in COMPUTED or key in skip:
                continue
            line = template.LINE_BY_KEY[key]
            figure = parse_printed_figure(printed)
            value = D(0) if figure.is_dash else figure.value * 1000 * line.presentation_sign
            corrections.enter(db, borrower_id=borrower.id, key=key, period_end=Q3, months=9 if line.flow else 0,
                              value=value, user_id=analyst.id, reason="Keyed from the scanned statement.")
    for key in ABSENT:
        line = template.LINE_BY_KEY[key]
        corrections.enter(db, borrower_id=borrower.id, key=key, period_end=Q3, months=9 if line.flow else 0,
                          value=D(0), user_id=analyst.id, reason="Not on the statement.")


@pytest.fixture()
def scanned(db, world):
    borrower, _ = world
    analyst = person(db, "analyst")
    add_fact(db, borrower_id=borrower.id, key="bs.cash", period_end=FY, months=0,
             value=D(PRIOR_FYE_CASH_THOUSANDS * 1000), kind="seeded")
    doc = ingest_pdf(db, borrower_id=borrower.id, data=scanned_pdf(), file_name="scan.pdf",
                     doc_type="interim_statements", doc_type_source="system", period_end=Q3,
                     received_date=date(2026, 10, 30))
    cycle = cycle_at(db, borrower, "spreading", period_end=Q3, months=9)
    run_stage(db, cycle)
    item = open_items(db, "spread.image_only")[0]
    return borrower, analyst, doc, cycle, item


def test_key_by_hand_finishes_the_spread_from_the_keyed_figures(db, scanned, monkeypatch):
    borrower, analyst, _, cycle, item = scanned
    key_statement(db, borrower, analyst)
    monkeypatch.setattr(workflow, "STAGE_HANDLERS", {})  # stop after spreading
    workflow.decide_work_item(db, item, user_id=analyst.id, user_role=analyst.role, decision="key_by_hand")
    assert item.status == "decided" and open_items(db) == []
    assert current_fact(db, borrower.id, "bs.total_assets", Q3, 0).value == D("34500000")
    assert current_fact(db, borrower.id, "is.net_income", Q3, 9).value == D("2340000")
    assert stage_status(db, cycle, "spreading") == "done"


def test_key_by_hand_with_figures_missing_asks_the_footing_question_and_never_dead_ends(db, scanned):
    borrower, analyst, _, cycle, item = scanned
    key_statement(db, borrower, analyst, skip=("bs.inventory",))
    workflow.decide_work_item(db, item, user_id=analyst.id, user_role=analyst.role, decision="key_by_hand")
    held = open_items(db)
    assert item.status == "decided" and [i.item_type for i in held] == ["spread.does_not_foot"]
    assert cycle.stage == "spreading" and current_fact(db, borrower.id, "bs.total_assets", Q3, 0) is None
    # saying it is corrected when it is not asks again; the stage is never released on a claim
    workflow.decide_work_item(db, held[0], user_id=analyst.id, user_role=analyst.role, decision="values_corrected")
    again = open_items(db)
    assert [i.item_type for i in again] == ["spread.does_not_foot"] and again[0].id != held[0].id
    assert cycle.stage == "spreading" and stage_status(db, cycle, "spreading") == "needs_person"


def test_a_stage_sent_back_by_a_decision_is_on_the_ledger_under_the_persons_name(db, scanned):
    _, analyst, doc, cycle, item = scanned
    before = len(events(db, "cycle.stage_changed"))
    workflow.decide_work_item(db, item, user_id=analyst.id, user_role=analyst.role,
                              decision="request_new_document", reason="Ask for a text PDF.")
    changed = events(db, "cycle.stage_changed")[before:]
    assert doc.status == "rejected"
    assert [(e.payload["stage"], e.payload["to"], e.actor_type, e.actor_id) for e in changed][0] == (
        "spreading", "pending", "user", str(analyst.id))


def test_a_stage_that_waits_records_the_change_back_to_pending(db, world, handlers):
    borrower, _ = world
    handlers["awaiting_package"] = lambda db, cycle, st: "waiting"
    cycle = workflow.open_cycle(db, borrower_id=borrower.id, period_end=Q3, months=9)
    workflow.advance(db, cycle)
    workflow.drain(db)
    moves = [(e.payload["from"], e.payload["to"]) for e in events(db, "cycle.stage_changed")]
    assert moves == [("pending", "running"), ("running", "pending")]


# ---- decisions that used to do nothing -------------------------------------------------------


def test_decisions_nothing_can_carry_out_are_not_offered(db, world):
    borrower, _ = world
    listing = raise_item(db, borrower_id=borrower.id, item_type="bb.certificate_mismatch",
                         title="The borrowing base could not be recalculated",
                         question="Correct the listing, or request a new certificate?",
                         allowed_decisions=["listing_corrected", "borrower_to_resubmit"])
    restated = raise_item(db, borrower_id=borrower.id, item_type="spread.restatement", blocks_stage=False,
                          title="Prior-period figures differ", question="Has the borrower restated?",
                          allowed_decisions=["restated_update_prior", "keep_prior", "ask_borrower"])
    assert listing.allowed_decisions == ["borrower_to_resubmit"]
    assert restated.allowed_decisions == ["keep_prior", "ask_borrower"]
    # an item stored before the decision was withdrawn refuses it too
    listing.allowed_decisions = ["listing_corrected", "borrower_to_resubmit"]
    db.flush()
    analyst = person(db, "analyst")
    with pytest.raises(ValueError, match="not one of the allowed decisions"):
        workflow.decide_work_item(db, listing, user_id=analyst.id, user_role=analyst.role,
                                  decision="listing_corrected")


def unread_certificate(db, borrower, facility):
    """The item the borrowing base stage raises when the certificate cannot be read in full."""
    doc = ingest_pdf(db, borrower_id=borrower.id, data=build_pdf(), file_name="bbc.pdf",
                     doc_type="borrowing_base_certificate", doc_type_source="system", period_end=Q3)
    cycle = cycle_at(db, borrower, "borrowing_base", period_end=Q3, months=9)
    item = raise_item(db, borrower_id=borrower.id, facility_id=facility.id, cycle_id=cycle.id,
                      stage="borrowing_base", item_type="bb.certificate_mismatch",
                      title="The borrowing base certificate could not be read in full",
                      question="Read the certificate again, or ask the borrower for a new one?",
                      allowed_decisions=["retry", "borrower_to_resubmit"],
                      evidence={"document_id": str(doc.id), "items": [{"what": "units"}]})
    for st in workflow.stages(db, cycle):
        if st.stage == "borrowing_base":
            st.status = "needs_person"
    db.flush()
    return doc, cycle, item


@pytest.mark.parametrize("decision, document_status", [("retry", "indexed"), ("borrower_to_resubmit", "rejected")])
def test_an_unread_certificate_is_read_again_or_set_aside_for_a_new_one(db, world, monkeypatch, decision,
                                                                       document_status):
    borrower, facility = world
    doc, cycle, item = unread_certificate(db, borrower, facility)
    analyst = person(db, "analyst")
    ran = []
    monkeypatch.setattr(workflow, "STAGE_HANDLERS",
                        {"borrowing_base": lambda db, cycle, st: ran.append(st.stage) or "waiting"})
    workflow.decide_work_item(db, item, user_id=analyst.id, user_role=analyst.role, decision=decision,
                              reason="Units line is cut off.")
    workflow.run_next_job(db)
    assert ran == ["borrowing_base"] and doc.status == document_status and cycle.stage == "borrowing_base"


def test_retry_is_refused_when_there_is_no_open_cycle_to_run_the_stage_in(db, world):
    borrower, facility = world
    _, cycle, item = unread_certificate(db, borrower, facility)
    cycle.status = "closed"
    db.flush()
    analyst = person(db, "analyst")
    with pytest.raises(ValueError, match="no stage to run again"):
        workflow.decide_work_item(db, item, user_id=analyst.id, user_role=analyst.role, decision="retry")
    assert item.status == "open" and stage_status(db, cycle, "borrowing_base") == "needs_person"


def terms_item(db, borrower, facility):
    """The item the Terms Agent raises when it cannot build terms: here the agreement is a scan."""
    blank = pymupdf.open()
    blank.new_page()
    agreement = ingest_pdf(db, borrower_id=borrower.id, data=blank.tobytes(), file_name="agreement.pdf",
                           doc_type="credit_agreement", doc_type_source="system")
    result = terms_agent.extract_terms(db, facility=facility, documents=[agreement], llm=None)
    assert result.version is None and result.work_item.allowed_decisions == ["board_by_hand", "retry"]
    return result.work_item


def test_retry_on_the_terms_item_runs_the_terms_agent_again(db, world):
    borrower, facility = world
    item = terms_item(db, borrower, facility)
    admin = person(db, "credit_admin")
    workflow.decide_work_item(db, item, user_id=admin.id, user_role=admin.role, decision="retry")
    again = [i for i in open_items(db) if "terms could not be built" in i.title]
    assert item.status == "decided" and len(again) == 1 and again[0].id != item.id
    assert len(events(db, "work_item.raised")) == 2


def test_board_by_hand_is_refused_until_a_person_has_entered_terms(db, world):
    borrower, facility = world
    item = terms_item(db, borrower, facility)
    admin, other = person(db, "credit_admin"), person(db, "credit_admin")
    with pytest.raises(ValueError, match="no terms have been entered"):
        workflow.decide_work_item(db, item, user_id=admin.id, user_role=admin.role, decision="board_by_hand")
    assert item.status == "open"
    _, approval = propose_terms(db, facility=facility, terms=terms(), effective_from=date(2024, 1, 15),
                                source_document_ids=[], prepared_by=("user", str(admin.id)))
    workflow.decide_work_item(db, item, user_id=admin.id, user_role=admin.role, decision="board_by_hand")
    assert item.status == "decided" and approval.status == "open" and approval.requires_second_person
    assert approval.prepared_by_id == str(admin.id) and other.id != admin.id
