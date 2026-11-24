"""The runtime with a scripted model: tool loop, scope, refusals, step cap, shape retry, trace."""
import uuid
from datetime import date

from app.agents.llm import LLMResponse, ScriptedClient
from app.agents.runtime import AgentSpec, run_agent
from app.agents.schema import strict_schema
from app.agents.tools import Refusal, Scope, Tool, ToolGateway, ToolInput
from app.core.ledger import LedgerEvent, verify_chain
from app.domain.agents import AgentRun, AgentSpecRecord, AgentStep
from pydantic import BaseModel
from sqlalchemy import select


class Answer(BaseModel):
    verdict: str
    note: str


class LookupIn(ToolInput):
    key: str


SEEN_SCOPES = []


def _lookup(ctx, args: LookupIn):
    SEEN_SCOPES.append(ctx.scope)
    if args.key == "missing":
        raise Refusal("no fact with that key for this period")
    return {"key": args.key, "fact_id": "f-1"}


GATEWAY = ToolGateway([Tool("lookup", "Look up a fact by key.", LookupIn, _lookup)])
SPEC = AgentSpec(name="test_agent", version="1", purpose="test", prompt_file="_test.md",
                 output_model=Answer, tools=("lookup",), max_steps=3)
SCOPE = Scope(borrower_id=None, period_end=date(2026, 9, 30), months=9)


def tool_call(name, inp, call_id=None):
    return LLMResponse(content=[{"type": "tool_use", "id": call_id or uuid.uuid4().hex, "name": name,
                                 "input": inp}], stop_reason="tool_use", usage={"input_tokens": 10, "output_tokens": 5})


def answer(text):
    return LLMResponse(content=[{"type": "text", "text": text}], stop_reason="end_turn",
                       usage={"input_tokens": 10, "output_tokens": 5})


def run(db, responses, spec=SPEC):
    llm = ScriptedClient(responses)
    outcome = run_agent(db, spec, task="unit", scope=SCOPE, content=[{"type": "text", "text": "go"}],
                        llm=llm, gateway=GATEWAY, record_key="test/unit")
    return outcome, llm


def test_tool_loop_then_answer_is_traced_and_ledgered(db):
    outcome, llm = run(db, [tool_call("lookup", {"key": "is.revenue"}),
                            answer('{"verdict": "ok", "note": "done"}')])
    assert outcome.ok and outcome.output.verdict == "ok"
    assert outcome.run.steps_count == 1 and outcome.run.input_tokens == 20
    steps = db.execute(select(AgentStep).where(AgentStep.run_id == outcome.run.id).order_by(AgentStep.n)).scalars().all()
    assert [(s.kind, s.name) for s in steps] == [("model", "response"), ("tool", "lookup"), ("model", "response")]
    # the tool result went back to the model in one user message
    last = llm.requests[1].messages[-1]
    assert last["role"] == "user" and last["content"][0]["type"] == "tool_result"
    actions = [e.action for e in db.execute(select(LedgerEvent).order_by(LedgerEvent.seq)).scalars()]
    assert actions == ["agent_spec.registered", "agent.run_started", "agent.tool_called", "agent.run_completed"]
    assert verify_chain(db)[0]


def test_scope_comes_from_code_and_extra_inputs_are_refused(db):
    SEEN_SCOPES.clear()
    outcome, llm = run(db, [
        tool_call("lookup", {"key": "is.revenue", "period_end": "2025-12-31", "borrower_id": "other"}),
        tool_call("lookup", {"key": "is.revenue"}),
        answer('{"verdict": "ok", "note": "done"}')])
    assert outcome.ok
    steps = db.execute(select(AgentStep).where(AgentStep.run_id == outcome.run.id, AgentStep.kind == "tool")
                       .order_by(AgentStep.n)).scalars().all()
    assert steps[0].refused and "Extra inputs" in steps[0].detail["output"]["error"]
    assert not steps[1].refused
    # the handler only ever ran with the scope set by code
    assert SEEN_SCOPES == [SCOPE]
    assert llm.requests[1].messages[-1]["content"][0]["is_error"] is True


def test_tool_schema_does_not_offer_scope_fields():
    props = GATEWAY.definitions(("lookup",))[0]["input_schema"]["properties"]
    assert set(props) == {"key"}
    assert GATEWAY.definitions(("lookup",))[0]["strict"] is True


def test_handler_refusal_goes_back_as_evidence(db):
    outcome, llm = run(db, [tool_call("lookup", {"key": "missing"}),
                            answer('{"verdict": "abstain", "note": "no fact"}')])
    assert outcome.ok and outcome.output.verdict == "abstain"
    assert "no fact with that key" in llm.requests[1].messages[-1]["content"][0]["content"]


def test_unknown_tool_is_refused(db):
    outcome, _ = run(db, [tool_call("delete_everything", {}), answer('{"verdict": "ok", "note": "x"}')])
    step = db.execute(select(AgentStep).where(AgentStep.run_id == outcome.run.id, AgentStep.kind == "tool")).scalar_one()
    assert step.refused


def test_spent_tool_budget_forces_one_final_turn_without_tools(db):
    outcome, llm = run(db, [tool_call("lookup", {"key": "a"}), tool_call("lookup", {"key": "b"}),
                            tool_call("lookup", {"key": "c"}), answer('{"verdict": "ok", "note": "late"}')])
    assert outcome.ok and outcome.cap_reached and outcome.output.note == "late"
    final = llm.requests[-1]
    assert final.tools == [] and final.messages[-1]["content"][-1]["type"] == "text"
    assert "abstain" in final.messages[-1]["content"][-1]["text"]
    assert len(llm.requests) == 4


def test_a_forced_turn_that_still_asks_for_tools_abstains(db):
    outcome, _ = run(db, [tool_call("lookup", {"key": "a"}), tool_call("lookup", {"key": "b"}),
                          tool_call("lookup", {"key": "c"}), tool_call("lookup", {"key": "d"})])
    assert outcome.status == "abstained" and outcome.reason == "step_cap" and outcome.output is None


def test_exchanges_are_capped_separately_from_tool_calls(db):
    spec = AgentSpec(name="test_agent_x", version="1", purpose="test", prompt_file="_test.md",
                     output_model=Answer, tools=("lookup",), max_steps=30, max_exchanges=2)
    outcome, llm = run(db, [tool_call("lookup", {"key": "a"}), tool_call("lookup", {"key": "b"}),
                            answer('{"verdict": "ok", "note": "x"}')], spec=spec)
    assert outcome.ok and outcome.cap_reached and outcome.run.steps_count == 2 and llm.requests[-1].tools == []


def test_parallel_calls_count_as_one_exchange_and_the_budget_still_bounds_them(db):
    many = LLMResponse(content=[{"type": "tool_use", "id": f"t{i}", "name": "lookup", "input": {"key": "a"}}
                                for i in range(5)], stop_reason="tool_use")
    outcome, llm = run(db, [many, answer('{"verdict": "ok", "note": "x"}')])
    assert outcome.ok and outcome.cap_reached and outcome.run.steps_count == 3  # budget of 3
    results = llm.requests[1].messages[-1]["content"]
    assert [r.get("is_error") for r in results if r["type"] == "tool_result"] == [False] * 3 + [True] * 2


def test_an_answer_inside_the_allowance_is_not_marked_capped(db):
    outcome, _ = run(db, [tool_call("lookup", {"key": "a"}), answer('{"verdict": "ok", "note": "x"}')])
    assert outcome.ok and not outcome.cap_reached


def test_bad_shape_gets_one_retry_without_tools(db):
    outcome, llm = run(db, [answer("I think it is fine."), answer('{"verdict": "ok", "note": "fixed"}')])
    assert outcome.ok and llm.requests[1].tools == []
    outcome2, _ = run(db, [answer("nope"), answer('{"verdict": 1}')])
    assert outcome2.status == "abstained" and outcome2.reason == "schema"


def test_refusal_and_cut_off_never_read_as_an_answer(db):
    refused, _ = run(db, [LLMResponse(content=[], stop_reason="refusal", stop_details={"category": None})])
    assert refused.status == "refused" and refused.output is None
    cut, _ = run(db, [LLMResponse(content=[{"type": "text", "text": '{"verdict": "ok"'}], stop_reason="max_tokens")])
    assert cut.status == "failed" and cut.output is None
    crashed, _ = run(db, [])
    assert crashed.status == "failed"


def test_spec_change_without_version_bump_is_refused(db):
    run(db, [answer('{"verdict": "ok", "note": "x"}')])
    changed = AgentSpec(name="test_agent", version="1", purpose="test", prompt_file="_test.md",
                        output_model=Answer, tools=("lookup",), max_steps=9)
    try:
        run(db, [answer('{"verdict": "ok", "note": "x"}')], spec=changed)
    except RuntimeError as exc:
        assert "bump the version" in str(exc)
    else:
        raise AssertionError("expected a refusal")
    assert db.execute(select(AgentSpecRecord)).scalars().all().__len__() == 1
    assert db.execute(select(AgentRun)).scalars().all().__len__() == 1


def test_strict_schema_closes_objects_and_requires_everything():
    schema = strict_schema(Answer)
    assert schema["additionalProperties"] is False and schema["required"] == ["verdict", "note"]
    assert "title" not in schema


def _typed(answer, _state):
    return ["a figure was typed"] if "2.41" in answer.note else []


def _run_checked(db, responses):
    llm = ScriptedClient(responses)
    outcome = run_agent(db, SPEC, task="unit", scope=SCOPE, content=[{"type": "text", "text": "go"}],
                        llm=llm, gateway=GATEWAY, record_key="test/unit", prose_check=_typed)
    return outcome, llm


def _checks(db, outcome):
    return [(s.name, s.detail.get("action")) for s in db.execute(
        select(AgentStep).where(AgentStep.run_id == outcome.run.id).order_by(AgentStep.n)).scalars()
        if s.kind == "guardrail"]


def test_a_typed_figure_is_sent_back_once_and_the_corrected_answer_is_kept(db):
    outcome, llm = _run_checked(db, [answer('{"verdict": "ok", "note": "leverage is 2.41x"}'),
                                     answer('{"verdict": "ok", "note": "leverage is {{fact:f-1}}"}')])
    assert outcome.ok and outcome.output.note == "leverage is {{fact:f-1}}"
    assert _checks(db, outcome) == [("number_check", "retry")]
    retry_prompt = llm.requests[1].messages[-1]["content"][0]["text"]
    assert "number check" in retry_prompt and "{{fact:<id>}}" in retry_prompt
    assert llm.requests[1].tools == []


def test_the_second_answer_is_returned_whatever_it_says_so_the_caller_withholds_it(db):
    outcome, llm = _run_checked(db, [answer('{"verdict": "ok", "note": "leverage is 2.41x"}'),
                                     answer('{"verdict": "ok", "note": "still 2.41x"}')])
    assert outcome.ok and outcome.output.note == "still 2.41x" and len(llm.requests) == 2
    assert _checks(db, outcome) == [("number_check", "retry")]


def test_a_clean_answer_is_not_sent_back(db):
    outcome, llm = _run_checked(db, [answer('{"verdict": "ok", "note": "leverage is {{fact:f-1}}"}')])
    assert outcome.ok and len(llm.requests) == 1 and _checks(db, outcome) == []
