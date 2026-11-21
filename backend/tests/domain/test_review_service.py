"""Review sheet and commentary on a seeded clean borrower: code builds the sheet, the Review
Agent drafts with fact references, a person approves, and the cycle runs to its close."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from app.agents.llm import KeyedScriptedClient, LLMResponse
from app.core.config import get_settings
from app.domain import hooks, review_service, stages, workflow  # noqa: F401
from app.domain.credit import Borrower
from app.domain.facts import Fact
from app.domain.monitoring import Cycle, WorkItem
from app.domain.org import User
from app.domain.reviews import Commentary, ReviewSheet
from app.seed_book import seed_book
from sqlalchemy import select

REPO = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def book(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("book")
    subprocess.run([sys.executable, "-m", "synthetic.generate", "--out", str(out)], cwd=REPO, check=True,
                   capture_output=True)
    return out


@pytest.fixture()
def world(db, book, tmp_path, monkeypatch):
    monkeypatch.setenv("FILE_STORE_DIR", str(tmp_path))
    get_settings.cache_clear()
    seed_book(db, root=book, current="seeded", only=["sablewood-dental"])
    borrower = db.execute(select(Borrower).where(Borrower.code == "sablewood-dental")).scalar_one()
    cycle = db.execute(select(Cycle).where(Cycle.borrower_id == borrower.id, Cycle.status == "open")).scalar_one()
    yield borrower, cycle
    get_settings.cache_clear()
    os.environ.pop("FILE_STORE_DIR", None)


def user(db, role):
    u = User(email=f"{role}@review.example", name=role, role=role, password_hash="x")
    db.add(u)
    db.flush()
    return u


def script(monkeypatch, sections):
    # twice: a draft that fails the number check is sent back once, and answered the same way again
    client = KeyedScriptedClient({"review/": [LLMResponse(
        content=[{"type": "text", "text": json.dumps({"sections": sections})}], stop_reason="end_turn")] * 2})
    monkeypatch.setattr(stages, "LLM_FACTORY", lambda: client)
    return client


def refs(sheet):
    revenue = next(m for m in sheet["metrics"] if m["metric"] == "revenue_ttm")
    covenant = sheet["covenants"][0]
    return revenue, covenant


def test_sheet_is_built_from_facts_that_all_have_a_source(db, world):
    _, cycle = world
    sheet, facts, labels = review_service.build_sheet(db, cycle)
    assert len(sheet["metrics"]) >= 8 and len(sheet["covenants"]) >= 2 and sheet["work_items"] == []
    revenue, covenant = refs(sheet)
    assert revenue["current"] in facts and revenue["year_earlier"] in facts
    assert covenant["value"] in facts and covenant["threshold"] in facts and covenant["headroom_pct"] in facts
    assert set(labels) == set(facts)
    for fid in facts:
        fact = db.get(Fact, fid)
        assert fact.kind in ("calculated", "seeded") and (fact.calc_run_id or fact.kind == "seeded")
    # building again reuses the metric facts instead of storing duplicates
    again, facts_again, _ = review_service.build_sheet(db, cycle)
    assert set(facts_again) == set(facts)


def test_draft_is_checked_stored_as_agent_written_and_needs_a_person(db, world, monkeypatch):
    borrower, cycle = world
    sheet, _, _ = review_service.build_sheet(db, cycle)
    revenue, covenant = refs(sheet)
    script(monkeypatch, [
        {"section": "summary", "body": "The borrower remains in compliance with every covenant this quarter."},
        {"section": "performance", "body": f"Revenue was {{{{fact:{revenue['current']}|usd_m}}}} against "
                                           f"{{{{fact:{revenue['year_earlier']}|usd_m}}}} a year earlier."},
        {"section": "covenants", "body": f"{covenant['covenant']} calculated to {{{{fact:{covenant['value']}}}}} "
                                         "against a minimum of 1.20x."},  # a typed figure
        {"section": "risks", "body": f"With a cushion of {{{{fact:{covenant['headroom_pct']}}}}}, we should "
                                     "waive the covenant if it tightens."},  # reserved for people
    ])
    workflow.advance(db, cycle)
    workflow.drain(db)
    assert cycle.stage == "review_prep"
    sheet_row = db.execute(select(ReviewSheet).where(ReviewSheet.cycle_id == cycle.id)).scalar_one()
    stored = {c.section: c for c in db.execute(select(Commentary).where(Commentary.review_sheet_id == sheet_row.id)).scalars()}
    # the risks draft was refused by policy, but this sheet has no signal and no open item: code wrote that section
    assert set(stored) == {"summary", "performance", "risks"}
    assert stored["risks"].body == "No signals fired and no items are open for this period."
    assert all(c.author_type == "agent" and c.status == "draft" for c in stored.values())
    text = review_service.rendered(db, stored["performance"])
    assert "{{" not in text and text.count("million") == 2 and "$" in text
    item = db.execute(select(WorkItem).where(WorkItem.item_type == "review.commentary_approval")).scalar_one()
    dropped = {n["check"] for n in item.guardrail_notes}
    assert dropped == {"figure_untraceable"} and item.status == "open"

    analyst, manager = user(db, "analyst"), user(db, "portfolio_manager")
    with pytest.raises(PermissionError):
        workflow.decide_work_item(db, item, user_id=analyst.id, user_role=analyst.role, decision="approve")
    # the analyst edits a section first; a typed figure is reported back, an unknown fact is refused
    _, warnings = review_service.write_section(
        db, sheet_row, section="covenants", user=analyst,
        body=f"{covenant['covenant']} calculated to {{{{fact:{covenant['value']}}}}}, above the 1.20x minimum.")
    assert len(warnings) == 1 and "1.20x" in warnings[0]
    with pytest.raises(ValueError, match="not in scope"):
        review_service.write_section(db, sheet_row, section="risks", user=analyst,
                                     body="See {{fact:00000000-0000-4000-8000-000000000009}}.")
    # 1.20 is not a figure on file for this borrower, so the typed minimum blocks approval
    with pytest.raises(ValueError, match="matches no stored fact"):
        workflow.decide_work_item(db, item, user_id=manager.id, user_role=manager.role, decision="approve")
    _, warnings = review_service.write_section(
        db, sheet_row, section="covenants", user=analyst,
        body=f"{covenant['covenant']} calculated to {{{{fact:{covenant['value']}}}}}, above the "
             f"{{{{fact:{covenant['threshold']}}}}} minimum.")
    assert warnings == []
    workflow.decide_work_item(db, item, user_id=manager.id, user_role=manager.role, decision="approve")
    workflow.drain(db)
    assert sheet_row.status == "reviewed" and sheet_row.approved_by == manager.id
    current = {c.section: c.status for c in review_service.current_commentary(db, sheet_row)}
    assert current == {"summary": "approved", "performance": "approved", "covenants": "approved", "risks": "approved"}
    assert cycle.status == "closed"  # nothing else was open, so the cycle ran to its close


def test_no_draft_still_asks_a_person_and_approval_needs_commentary(db, world, monkeypatch):
    _, cycle = world
    monkeypatch.setattr(stages, "LLM_FACTORY", lambda: KeyedScriptedClient({}))
    workflow.advance(db, cycle)
    workflow.drain(db)
    item = db.execute(select(WorkItem).where(WorkItem.item_type == "review.commentary_approval")).scalar_one()
    assert "No commentary could be drafted" in item.question
    manager = user(db, "portfolio_manager")
    with pytest.raises(ValueError, match="no commentary to approve"):
        workflow.decide_work_item(db, item, user_id=manager.id, user_role=manager.role, decision="approve")
    assert item.status == "open" and cycle.stage == "review_prep"


def test_withheld_sections_are_named_to_the_approver_with_the_reason(db, world, monkeypatch):
    """A draft with sections withheld by the checks used to be raised as "ready for approval" with
    nothing saying a section was missing. The item now says how many and which, and the sheet
    lists each withheld section with the check that withheld it and why."""
    from app.api.routes_reviews import _sheet_out

    borrower, cycle = world
    sheet, _, _ = review_service.build_sheet(db, cycle)
    revenue, covenant = refs(sheet)
    script(monkeypatch, [
        {"section": "summary", "body": "The borrower remains in compliance with every covenant this quarter."},
        {"section": "performance", "body": f"Revenue was {{{{fact:{revenue['current']}|usd_m}}}}."},
        {"section": "covenants", "body": f"{covenant['covenant']} calculated to {{{{fact:{covenant['value']}}}}} "
                                         "against a minimum of 1.20x."},  # a typed figure
        {"section": "collateral", "body": "Collateral coverage stood at 2.4 times the line."},  # a typed figure
    ])
    workflow.advance(db, cycle)
    workflow.drain(db)
    item = db.execute(select(WorkItem).where(WorkItem.item_type == "review.commentary_approval")).scalar_one()
    assert item.title == f"{borrower.name}: review sheet is ready for approval, 2 sections withheld by the number check"
    assert "collateral and covenants" in item.question and item.question.endswith("?")
    withheld = item.evidence["withheld_sections"]
    assert [w["section"] for w in withheld] == ["collateral", "covenants"]
    assert all(w["withheld_by"] == "number check" and w["check"] == "figure_untraceable" for w in withheld)
    # the reason says why; the typed figure itself is not repeated, as the agent's figure is unverified
    reason = next(w for w in withheld if w["section"] == "covenants")["reason"]
    assert reason.startswith("a figure was typed, not referenced") and "1.20" not in reason
    assert item.evidence["sections"] == ["performance", "risks", "summary"]

    sheet_row = db.execute(select(ReviewSheet).where(ReviewSheet.cycle_id == cycle.id)).scalar_one()
    shown = _sheet_out(db, sheet_row)
    assert [w["section"] for w in shown["withheld_sections"]] == ["collateral", "covenants"]
    assert {c["section"] for c in shown["commentary"]} == {"summary", "performance", "risks"}


def test_a_full_draft_says_nothing_was_withheld(db, world, monkeypatch):
    borrower, cycle = world
    script(monkeypatch, [
        {"section": "summary", "body": "The borrower remains in compliance with every covenant this quarter."}])
    workflow.advance(db, cycle)
    workflow.drain(db)
    item = db.execute(select(WorkItem).where(WorkItem.item_type == "review.commentary_approval")).scalar_one()
    assert item.title == f"{borrower.name}: review sheet is ready for approval"
    assert item.evidence["withheld_sections"] == []


def _draft(db, world, monkeypatch, sheet, sections):
    from app.agents.review import draft_commentary
    borrower, cycle = world
    script(monkeypatch, sections)
    client = stages.LLM_FACTORY()
    return draft_commentary(db, borrower=borrower, cycle=cycle, sheet=sheet, facts={}, labels={}, llm=client)


def test_a_sheet_with_no_signals_and_no_open_items_gets_a_risks_sentence_written_by_code(db, world, monkeypatch):
    from app.agents.review import NO_RISKS_SENTENCE
    sheet = {"signals": [], "work_items": [{"type": "x", "status": "closed", "decision": "approve"}]}
    # the model drafted nothing citeable for risks (or nothing at all): the section is still there
    for risks in ([{"section": "risks", "body": "Nothing to report."}], []):
        draft = _draft(db, world, monkeypatch, sheet, [{"section": "summary", "body": "A steady quarter."}, *risks])
        assert draft.sections["risks"] == NO_RISKS_SENTENCE and "risks" not in {n.get("section") for n in draft.notes}
    assert not any(c.isdigit() for c in NO_RISKS_SENTENCE)


def test_a_sheet_with_a_signal_or_an_open_item_still_needs_a_risks_section_that_cites_a_fact(db, world, monkeypatch):
    body = [{"section": "risks", "body": "Nothing to report."}]
    for sheet in ({"signals": [{"rule": "r", "severity": "high"}], "work_items": []},
                  {"signals": [], "work_items": [{"type": "x", "status": "open", "decision": None}]}):
        draft = _draft(db, world, monkeypatch, sheet, body)
        assert "risks" not in draft.sections
        assert [n["section"] for n in draft.notes] == ["risks"] and draft.notes[0]["check"] == "no_facts"
