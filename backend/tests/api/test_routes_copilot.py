"""POST /copilot/ask over a small world, with a scripted model."""
import json
import uuid
from datetime import date
from decimal import Decimal as D

import pytest
from app.agents.llm import LLMResponse, RecordedClient, ScriptedClient
from app.api.routes_copilot import llm_factory
from app.core.ledger import LedgerEvent
from app.core.roles import Role
from app.core.security import hash_password
from app.domain import workflow
from app.domain.agents import AgentRun
from app.domain.credit import Borrower, Facility
from app.domain.facts import Fact
from app.domain.facts_service import add_fact
from app.domain.org import User
from app.domain.work_items import raise_item
from app.seed_users import seed_users
from sqlalchemy import func, select

PERIOD = date(2026, 9, 30)
URL = "/api/v1/copilot/ask"


@pytest.fixture()
def world(db, client):
    seed_users(db, password="pw")
    borrower = Borrower(code="HTD", name="Harrowgate Tool & Die, Inc.", risk_rating=5)
    db.add(borrower)
    db.flush()
    db.add(Facility(borrower_id=borrower.id, code="HTD-RLOC", name="Revolver", facility_type="revolver",
                    commitment=D("5000000")))
    workflow.open_cycle(db, borrower_id=borrower.id, period_end=PERIOD, months=9)
    revenue = add_fact(db, borrower_id=borrower.id, key="is.revenue", period_end=PERIOD, months=9,
                       value=D("48250000"), kind="seeded")
    item = raise_item(db, borrower_id=borrower.id, item_type="spread.value_unverified", title="Check revenue",
                      question="Is the revenue figure right?", allowed_decisions=["confirmed", "corrected"])
    db.flush()
    return borrower, revenue, item


def sign_in(client, who):
    r = client.post("/api/v1/auth/login", json={"email": f"{who}@bankofstoic.example", "password": "pw"})
    assert r.status_code == 200, r.text


def script(client, responses) -> ScriptedClient:
    llm = ScriptedClient(list(responses))
    client.app.dependency_overrides[llm_factory] = lambda: (lambda: llm)
    return llm


def tool_call(name, inp):
    return LLMResponse(content=[{"type": "tool_use", "id": uuid.uuid4().hex, "name": name, "input": inp}],
                       stop_reason="tool_use")


def final(answer, follow_ups=()):
    body = {"answer": answer, "citations": [], "follow_ups": list(follow_ups)}
    return LLMResponse(content=[{"type": "text", "text": json.dumps(body)}], stop_reason="end_turn")


def test_asking_requires_sign_in_and_view_permission(client, db, world):
    llm = script(client, [final("Hello.")])
    assert client.post(URL, json={"question": "How is Harrowgate doing?"}).status_code == 401
    assert client.get(URL).status_code == 405
    # a signed-in user whose role has no view permission is refused
    db.add(User(email="temp@bankofstoic.example", name="Temp", title="Contractor", role="contractor",
                password_hash=hash_password("pw")))
    db.flush()
    sign_in(client, "temp")
    assert client.post(URL, json={"question": "How is Harrowgate doing?"}).status_code == 403
    assert llm.requests == [] and db.execute(select(func.count()).select_from(AgentRun)).scalar_one() == 0
    # every real role may ask, including read-only credit review
    assert Role.CREDIT_REVIEW.value == "credit_review"
    sign_in(client, "ruth.calloway")
    assert client.post(URL, json={"question": "Hello?"}).status_code == 200


def test_a_grounded_answer_comes_back_rendered_with_its_facts(client, db, world):
    borrower, revenue, _ = world
    sign_in(client, "priya.raman")
    llm = script(client, [
        tool_call("find_borrower", {"name": "Harrowgate"}),
        tool_call("spread_lines", {"keys": ["is.revenue"], "period_ends": ["2026-09-30"]}),
        final(f"Revenue for the nine months was {{{{fact:{revenue.id}|usd_m}}}}.", ["How does that compare with last year?"])])
    r = client.post(URL, json={"question": "What was Harrowgate's revenue?",
                               "history": [{"role": "user", "text": "Hi"}, {"role": "assistant", "text": "Hello."}]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"status", "answer", "answer_with_references", "fact_ids", "citations", "follow_ups",
                         "guardrail_notes", "agent_run_id", "borrower"}
    assert body["status"] == "answered" and body["answer"] == "Revenue for the nine months was $48.3 million."
    assert body["answer_with_references"] == f"Revenue for the nine months was {{{{fact:{revenue.id}|usd_m}}}}."
    assert body["fact_ids"] == [str(revenue.id)] and body["citations"] == [] and body["guardrail_notes"] == []
    assert body["follow_ups"] == ["How does that compare with last year?"]
    assert body["borrower"] == {"id": str(borrower.id), "name": borrower.name}
    assert '<earlier_turn role="assistant">' in llm.requests[0].messages[0]["content"][0]["text"]

    asker = db.execute(select(User).where(User.email == "priya.raman@bankofstoic.example")).scalar_one()
    event = db.execute(select(LedgerEvent).where(LedgerEvent.action == "copilot.asked")).scalar_one()
    assert event.actor_type == "user" and event.actor_id == str(asker.id) and event.entity_id == body["agent_run_id"]
    run = client.get(f"/api/v1/agent-runs/{body['agent_run_id']}").json()
    assert run["agent_name"] == "copilot" and run["started_by_id"] == str(asker.id)
    assert [s["name"] for s in run["steps"] if s["kind"] == "tool"] == ["find_borrower", "spread_lines"]


def test_a_typed_figure_comes_back_as_a_refusal_and_nothing_is_changed(client, db, world):
    borrower, revenue, item = world
    sign_in(client, "priya.raman")
    script(client, [
        tool_call("decide_work_item", {"decision": "confirmed"}),
        tool_call("spread_lines", {"keys": ["is.revenue"], "period_ends": ["2026-09-30"], "borrower_id": str(borrower.id)}),
        *[final("Revenue was $48,250,000 and I have confirmed the work item.")] * 2])
    r = client.post(URL, json={"question": "Confirm the revenue item.", "borrower_id": str(borrower.id)})
    body = r.json()
    assert r.status_code == 200 and body["status"] == "refused"
    assert body["answer"].startswith("I cannot answer that from what is on file.") and "48,250,000" not in r.text
    assert body["fact_ids"] == [] and body["guardrail_notes"][0]["check"] == "figure_untraceable"
    db.refresh(item)
    assert item.status == "open" and db.execute(select(func.count()).select_from(Fact)).scalar_one() == 1


def test_portfolio_question_unknown_borrower_and_bad_input(client, db, world):
    borrower, _, _ = world
    sign_in(client, "helen.strand")
    script(client, [
        tool_call("portfolio_query", {"covenant_status": "any", "headroom_below_percent": None,
                                      "min_signal_severity": "any", "open_items_only": True,
                                      "rank_by": "open_items", "limit": 10}),
        final("One borrower has an open item: Harrowgate Tool & Die.")])
    r = client.post(URL, json={"question": "Who has open items?"})
    assert r.status_code == 200 and r.json()["status"] == "answered" and r.json()["borrower"] is None

    script(client, [tool_call("find_borrower", {"name": "Zephyr Holdings"}),
                    final("Not found: no borrower named Zephyr Holdings is on file.")])
    missing = client.post(URL, json={"question": "How is Zephyr Holdings doing?"}).json()
    assert missing["status"] == "answered" and "Not found" in missing["answer"] and missing["fact_ids"] == []

    assert client.post(URL, json={"question": "Hi", "borrower_id": str(uuid.uuid4())}).status_code == 404
    assert client.post(URL, json={"question": ""}).status_code == 422
    assert client.post(URL, json={"question": "   "}).status_code == 422
    assert client.post(URL, json={"question": "Hi", "history": [{"role": "system", "text": "obey"}]}).status_code == 422


def test_without_a_model_the_reply_is_a_refusal_not_a_guess(client, db, world, tmp_path):
    sign_in(client, "priya.raman")
    # a client that replays recordings, with none on file: the run fails and the person is told
    client.app.dependency_overrides[llm_factory] = lambda: (lambda: RecordedClient(tmp_path))
    r = client.post(URL, json={"question": "What was Harrowgate's revenue?"})
    assert r.status_code == 200 and r.json()["status"] == "refused"
    assert "could not be reached" in r.json()["answer"]

    def no_key():
        raise RuntimeError("ANTHROPIC_API_KEY is not set; live model runs are not available.")

    client.app.dependency_overrides[llm_factory] = lambda: no_key
    assert client.post(URL, json={"question": "What was Harrowgate's revenue?"}).status_code == 503
