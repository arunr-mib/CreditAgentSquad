"""Commentary a person writes: whoever last edited a section cannot approve it, a typed figure
that matches none of the borrower's stored facts blocks approval, and a fact reference must be
to a fact of that borrower."""
from datetime import date
from decimal import Decimal as D

import pytest
from app.agents.llm import KeyedScriptedClient
from app.core.roles import SecondPersonRequired
from app.domain import hooks, review_service, workflow  # noqa: F401
from app.domain.credit import Borrower
from app.domain.facts_service import add_fact
from app.domain.monitoring import WorkItem
from app.domain.org import User
from app.domain.reviews import ReviewSheet
from app.guardrails.narrative import Note
from sqlalchemy import select

PERIOD = date(2026, 9, 30)


def person(db, role, name):
    u = User(email=f"{name}@x.example", name=name, role=role, password_hash="x")
    db.add(u)
    db.flush()
    return u


@pytest.fixture()
def world(db, monkeypatch):
    """A review sheet waiting for approval, with no agent draft: people write the commentary."""
    monkeypatch.setattr(workflow, "STAGE_HANDLERS", {})  # nothing runs after the approval
    borrower, other = Borrower(code="HTD", name="Harrowgate Tool & Die, Inc."), Borrower(code="OTH", name="Other Co.")
    db.add_all([borrower, other])
    db.flush()
    revenue = add_fact(db, borrower_id=borrower.id, key="is.revenue", period_end=PERIOD, months=9,
                       value=D("48250000"), kind="seeded")
    minimum = add_fact(db, borrower_id=borrower.id, key="cov.fccr.threshold", period_end=PERIOD, months=0,
                       value=D("1.20"), unit="ratio", kind="seeded")
    foreign = add_fact(db, borrower_id=other.id, key="is.revenue", period_end=PERIOD, months=9,
                       value=D("99900000"), kind="seeded")
    cycle = workflow.open_cycle(db, borrower_id=borrower.id, period_end=PERIOD, months=9)
    sheet = review_service.prepare_review(db, cycle=cycle, llm=KeyedScriptedClient({}))
    item = db.execute(select(WorkItem).where(WorkItem.item_type == "review.commentary_approval")).scalar_one()
    return sheet, item, {"revenue": revenue, "minimum": minimum, "foreign": foreign}


def approve(db, item, user):
    return workflow.decide_work_item(db, item, user_id=user.id, user_role=user.role, decision="approve")


def test_the_person_who_last_edited_a_section_cannot_approve_it(db, world):
    sheet, item, facts = world
    dana, marcus = person(db, "portfolio_manager", "dana"), person(db, "portfolio_manager", "marcus")
    review_service.write_section(db, sheet, section="summary", user=dana,
                                 body=f"Revenue was {{{{fact:{facts['revenue'].id}|usd_m}}}}; no concerns.")
    with pytest.raises(SecondPersonRequired, match="last edited the summary section"):
        approve(db, item, dana)
    assert item.status == "open" and db.get(ReviewSheet, sheet.id).status == "draft"
    approve(db, item, marcus)
    assert item.status == "decided" and sheet.status == "reviewed" and sheet.approved_by == marcus.id


def test_a_later_edit_by_someone_else_changes_who_may_not_approve(db, world):
    sheet, item, _ = world
    dana, marcus = person(db, "portfolio_manager", "dana"), person(db, "portfolio_manager", "marcus")
    review_service.write_section(db, sheet, section="summary", user=dana, body="Stable quarter.")
    review_service.write_section(db, sheet, section="summary", user=marcus, body="Stable quarter; no concerns.")
    with pytest.raises(SecondPersonRequired):
        approve(db, item, marcus)
    approve(db, item, dana)  # dana's text was replaced; the section approved is marcus's
    assert sheet.status == "reviewed"


def test_a_typed_figure_that_matches_no_stored_fact_blocks_approval_until_it_is_referenced(db, world):
    sheet, item, facts = world
    analyst, manager = person(db, "analyst", "priya"), person(db, "portfolio_manager", "dana")
    _, warnings = review_service.write_section(db, sheet, section="summary", user=analyst,
                                               body="Revenue rose to $51.3 million on new contracts.")
    assert len(warnings) == 1 and "51.3 million" in warnings[0] and review_service.BLOCKS_APPROVAL in warnings[0]
    with pytest.raises(ValueError, match="matches no stored fact"):
        approve(db, item, manager)
    assert item.status == "open"
    _, warnings = review_service.write_section(
        db, sheet, section="summary", user=analyst,
        body=f"Revenue rose to {{{{fact:{facts['revenue'].id}|usd_m}}}} on new contracts.")
    assert warnings == []
    approve(db, item, manager)
    assert sheet.status == "reviewed"


def test_a_typed_figure_that_is_one_of_the_borrowers_facts_is_a_warning_only(db, world):
    sheet, item, _ = world
    analyst, manager = person(db, "analyst", "priya"), person(db, "portfolio_manager", "dana")
    _, warnings = review_service.write_section(db, sheet, section="covenants", user=analyst,
                                               body="Coverage stayed above the 1.20x minimum.")
    assert len(warnings) == 1 and "1.20x" in warnings[0] and review_service.BLOCKS_APPROVAL not in warnings[0]
    approve(db, item, manager)
    assert sheet.status == "reviewed"


def test_another_borrowers_figure_does_not_make_a_typed_figure_acceptable(db, world):
    sheet, item, _ = world
    analyst, manager = person(db, "analyst", "priya"), person(db, "portfolio_manager", "dana")
    _, warnings = review_service.write_section(db, sheet, section="summary", user=analyst,
                                               body="Revenue reached $99,900,000.")  # Other Co.'s revenue
    assert review_service.BLOCKS_APPROVAL in warnings[0]
    with pytest.raises(ValueError, match="matches no stored fact"):
        approve(db, item, manager)


def test_a_reference_to_another_borrowers_fact_is_refused(db, world):
    sheet, _, facts = world
    analyst = person(db, "analyst", "priya")
    with pytest.raises(ValueError, match="not in scope"):
        review_service.write_section(db, sheet, section="summary", user=analyst,
                                     body=f"Revenue was {{{{fact:{facts['foreign'].id}|usd_m}}}}.")
    assert review_service.current_commentary(db, sheet) == []


def test_findings_are_grouped_so_that_an_unknown_check_is_a_broken_reference(db, world, monkeypatch):
    """The narrative guardrail is gaining checks. A quantity in words is a typed quantity (saved,
    blocks approval, cannot match a fact); any check this code does not know refuses the save."""
    sheet, item, _ = world
    analyst, manager = person(db, "analyst", "priya"), person(db, "portfolio_manager", "dana")

    def finds(check):
        return lambda text, facts, **kw: [Note("narrative", check, "retry", f"{check} found")]

    monkeypatch.setattr(review_service, "check_narrative", finds("number_in_words"))
    _, warnings = review_service.write_section(db, sheet, section="summary", user=analyst,
                                               body="Revenue roughly doubled to twelve million.")
    assert warnings == [f"number_in_words found; {review_service.BLOCKS_APPROVAL}"]
    with pytest.raises(ValueError, match="number_in_words found"):
        approve(db, item, manager)
    for check in ("reference_joined", "format_wrong_for_unit", "a_check_added_later"):
        monkeypatch.setattr(review_service, "check_narrative", finds(check))
        with pytest.raises(ValueError, match=f"{check} found"):
            review_service.write_section(db, sheet, section="risks", user=analyst, body="Some text.")
    assert [c.section for c in review_service.current_commentary(db, sheet)] == ["summary"]


def test_a_finding_that_names_its_text_apart_from_the_explanation_is_reported_with_both():
    """The guardrail's note is gaining a `subject` (the offending text); `detail` then no longer
    repeats it. Both shapes must read well."""
    from types import SimpleNamespace

    newer = SimpleNamespace(check="figure_untraceable", subject="$51.3 million", detail="typed, not referenced")
    assert review_service._say(newer) == "$51.3 million: typed, not referenced"
    assert review_service._say(Note("narrative", "figure_untraceable", "retry", "the figure was typed")) == \
        "the figure was typed"


def test_the_engine_and_the_case_view_agree_the_writer_may_not_approve(db, world):
    from app.squad.cases import build_case

    sheet, item, facts = world
    dana, marcus = person(db, "portfolio_manager", "dana"), person(db, "portfolio_manager", "marcus")
    review_service.write_section(db, sheet, section="summary", user=dana, body="Stable quarter.")
    refusal = workflow.decision_refusal(db, item, user_id=dana.id, user_role=dana.role, decision="approve")
    assert isinstance(refusal, SecondPersonRequired) and "last edited the summary section" in str(refusal)
    assert workflow.decision_refusal(db, item, user_id=marcus.id, user_role=marcus.role, decision="approve") is None
    # a decision that does not approve is not held back by who wrote the text
    assert workflow.decision_refusal(db, item, user_id=dana.id, user_role=dana.role, decision="return_for_rework") is None
    permitted = lambda who: {d["id"]: d["permitted"] for d in build_case(db, item, who)["decisions"]}  # noqa: E731
    assert permitted(dana)["approve"] is False
    assert permitted(marcus)["approve"] is True
