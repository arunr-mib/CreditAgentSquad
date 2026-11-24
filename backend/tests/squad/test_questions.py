import uuid

import pytest
from app.core.ledger import LedgerEvent
from app.domain.agents import Lesson
from app.squad.questions import answer_question, raise_question
from sqlalchemy import func, select

from .conftest import sign_in

OPTIONS = [
    {"id": "map_to_arr", "label": "Map to ARR", "evidence": "The page labels it ARR."},
    {"id": "map_to_mrr", "label": "Map to MRR", "evidence": "The page also shows monthly."},
]
WHY = "The covenant is written on annual figures."


def _ask(db, borrower):
    return raise_question(db, borrower_id=borrower.id, title="How should I map this line?",
                          question="Is 'Recurring revenue' ARR or MRR?", options=OPTIONS, topic="line_mapping")


def _lessons(db):
    return db.execute(select(func.count()).select_from(Lesson)).scalar_one()


def test_raising_a_question_offers_exactly_its_options(db, world):
    item = _ask(db, world["borrower"])
    assert item.item_type == "question" and item.allowed_decisions == ["map_to_arr", "map_to_mrr"]
    assert item.evidence["options"][0]["label"] == "Map to ARR" and item.blocks_stage is False


@pytest.mark.parametrize("bad", [[], OPTIONS[:1], OPTIONS + [{"id": "map_to_arr", "label": "dup", "evidence": ""}],
                                 [{"id": "Has Space", "label": "x", "evidence": ""}, OPTIONS[1]]])
def test_a_question_needs_two_to_six_distinct_slug_options(db, world, bad):
    with pytest.raises(ValueError):
        raise_question(db, borrower_id=world["borrower"].id, title="t", question="Which?", options=bad)


def test_answering_records_the_choice_with_her_name_and_no_lesson_by_default(db, world):
    item = _ask(db, world["borrower"])
    answer_question(db, item, world["analyst"], "map_to_arr")
    assert item.status == "decided" and item.decision == "map_to_arr" and item.decided_by == world["analyst"].id
    assert _lessons(db) == 0


def test_remember_writes_exactly_one_lesson_from_her_written_reason(db, world):
    item = _ask(db, world["borrower"])
    answer_question(db, item, world["analyst"], "map_to_arr", remember=True, note=WHY)
    lessons = db.execute(select(Lesson)).scalars().all()
    assert len(lessons) == 1 and lessons[0].topic == "line_mapping"
    assert "Map to ARR" in lessons[0].text and WHY in lessons[0].text
    assert lessons[0].work_item_id == item.id and lessons[0].written_by == world["analyst"].id
    assert item.decision_reason == WHY


@pytest.mark.parametrize("note", ["", "   ", "x" * 2000])
def test_remember_needs_her_own_words_within_the_lesson_cap_and_a_refusal_records_nothing(db, world, note):
    item = _ask(db, world["borrower"])
    with pytest.raises(ValueError):
        answer_question(db, item, world["analyst"], "map_to_arr", remember=True, note=note)
    assert item.status == "open" and _lessons(db) == 0


def test_an_option_not_offered_is_refused_and_nothing_is_recorded(db, world):
    item = _ask(db, world["borrower"])
    with pytest.raises(ValueError):
        answer_question(db, item, world["analyst"], "map_to_nothing", remember=True, note=WHY)
    assert item.status == "open" and _lessons(db) == 0


def test_answering_twice_is_refused_and_writes_no_second_lesson(db, world):
    item = _ask(db, world["borrower"])
    answer_question(db, item, world["analyst"], "map_to_arr", remember=True, note=WHY)
    with pytest.raises(ValueError):
        answer_question(db, item, world["analyst"], "map_to_mrr", remember=True, note=WHY)
    assert _lessons(db) == 1


def test_only_a_question_can_be_answered_this_way(db, world):
    from app.domain.work_items import raise_item
    other = raise_item(db, borrower_id=world["borrower"].id, item_type="funding_slipped", title="t",
                       question="Review it?", allowed_decisions=["reviewed", "escalate_to_committee"])
    with pytest.raises(ValueError):
        answer_question(db, other, world["analyst"], "reviewed")


def test_endpoint_answers_remembers_and_the_ledger_has_her_name(db, client, world):
    item = _ask(db, world["borrower"])
    db.commit()
    sign_in(client, "priya.raman")
    r = client.post(f"/api/v1/work-items/{item.id}/answer",
                    json={"option_id": "map_to_arr", "remember": True, "note": WHY})
    assert r.status_code == 200 and r.json()["lesson_id"]
    event = db.execute(select(LedgerEvent).where(LedgerEvent.action == "work_item.decided")).scalars().one()
    assert event.actor_id == str(world["analyst"].id)
    again = client.post(f"/api/v1/work-items/{item.id}/answer", json={"option_id": "map_to_arr"})
    assert again.status_code == 422


def test_endpoint_refuses_remember_without_words_and_leaves_the_question_open(db, client, world):
    item = _ask(db, world["borrower"])
    db.commit()
    sign_in(client, "priya.raman")
    r = client.post(f"/api/v1/work-items/{item.id}/answer", json={"option_id": "map_to_arr", "remember": True})
    assert r.status_code == 422
    assert client.post(f"/api/v1/work-items/{item.id}/answer", json={"option_id": "map_to_arr"}).status_code == 200


def test_endpoint_refuses_a_role_that_cannot_decide_and_an_unknown_item(db, client, world):
    item = _ask(db, world["borrower"])
    db.commit()
    sign_in(client, "admin")
    assert client.post(f"/api/v1/work-items/{item.id}/answer", json={"option_id": "map_to_arr"}).status_code == 403
    assert client.post(f"/api/v1/work-items/{uuid.uuid4()}/answer", json={"option_id": "x"}).status_code == 404


def test_endpoint_answer_on_a_non_question_item_is_422(db, client, world):
    from app.domain.work_items import raise_item
    other = raise_item(db, borrower_id=world["borrower"].id, item_type="funding_slipped", title="t",
                       question="Review it?", allowed_decisions=["reviewed", "escalate_to_committee"])
    db.commit()
    sign_in(client, "priya.raman")
    assert client.post(f"/api/v1/work-items/{other.id}/answer", json={"option_id": "reviewed"}).status_code == 422


def test_a_refused_role_with_remember_and_a_note_writes_no_lesson(db, client, world):
    item = _ask(db, world["borrower"])
    db.commit()
    sign_in(client, "admin")
    r = client.post(f"/api/v1/work-items/{item.id}/answer",
                    json={"option_id": "map_to_arr", "remember": True, "note": WHY})
    assert r.status_code == 403
    assert _lessons(db) == 0 and db.get(type(item), item.id).status == "open"


def test_a_failing_lesson_write_rolls_the_decision_back_even_if_the_caller_carries_on(db, world, monkeypatch):
    item = _ask(db, world["borrower"])

    def boom(*a, **k):
        raise RuntimeError("lesson store down")

    monkeypatch.setattr("app.squad.questions.record_lesson", boom)
    with pytest.raises(RuntimeError):
        answer_question(db, item, world["analyst"], "map_to_arr", remember=True, note=WHY)
    db.refresh(item)
    assert item.status == "open" and item.decision is None


def _agent_options(label="Map to ARR", evidence="The page labels it ARR."):
    return [{"id": "a", "label": label, "evidence": evidence}, {"id": "b", "label": "Map to MRR", "evidence": ""}]


@pytest.mark.parametrize("field", ["label", "evidence"])
@pytest.mark.parametrize("text", ["Revenue was $4,500,000", "about 4.5 million", "a 12.5% decline", "1.25x cover", "USD4,500,000"])
def test_an_agent_cannot_type_a_figure_into_an_option(db, world, field, text):
    options = _agent_options(**{field: text})
    with pytest.raises(ValueError, match="fact"):
        raise_question(db, borrower_id=world["borrower"].id, title="t", question="Which?", options=options)


def test_an_agent_may_cite_a_figure_through_a_fact_reference(db, world):
    item = raise_question(db, borrower_id=world["borrower"].id, title="t", question="Which?",
                          options=_agent_options(evidence="Cash was {{fact:3f9a2b}} at quarter end."))
    assert item.evidence["options"][0]["evidence"] == "Cash was {{fact:3f9a2b}} at quarter end."


def test_a_person_may_write_their_own_figures_in_an_option(db, world):
    item = raise_question(db, borrower_id=world["borrower"].id, title="t", question="Which?",
                          options=_agent_options(label="Use 4,500,000"), actor=("user", str(world["analyst"].id)))
    assert item.evidence["options"][0]["label"] == "Use 4,500,000"
