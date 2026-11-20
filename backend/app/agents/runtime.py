"""Runs one agent on one bounded task: the tool loop, the step cap, the trace and the ledger.

The runtime returns the model's validated answer. It does not decide what happens next:
each agent module applies its guardrails to the answer, and the workflow (code) owns the stages.
"""
import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.agents.llm import LLMClient, LLMRequest, LLMResponse, spec_stamp
from app.agents.schema import strict_schema
from app.agents.tools import Scope, ToolContext, ToolGateway, _next_n, summarise
from app.core import ledger
from app.core.config import get_settings
from app.domain.agents import AgentRun, AgentSpecRecord, AgentStep

SPECS_DIR = Path(__file__).parent / "specs"


@dataclass(frozen=True)
class AgentSpec:
    name: str
    version: str
    purpose: str
    prompt_file: str
    output_model: type[BaseModel]
    tools: tuple[str, ...] = ()
    effort: str = "high"
    max_steps: int = 12
    max_tokens: int = 32000
    model: str | None = None  # None = the configured default model

    def prompt(self) -> str:
        return (SPECS_DIR / self.prompt_file).read_text()

    def resolved_model(self) -> str:
        return self.model or get_settings().squad_model

    def prompt_sha256(self) -> str:
        return hashlib.sha256(self.prompt().encode()).hexdigest()

    def spec_sha256(self) -> str:
        body = {"name": self.name, "version": self.version, "model": self.resolved_model(),
                "effort": self.effort, "max_steps": self.max_steps, "tools": list(self.tools),
                "prompt": self.prompt_sha256(), "output": strict_schema(self.output_model)}
        return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


@dataclass
class AgentOutcome:
    run: AgentRun
    status: str  # completed | abstained | failed | refused
    output: BaseModel | None = None
    reason: str | None = None  # why there is no output: step_cap | schema | max_tokens | refusal | error

    @property
    def ok(self) -> bool:
        return self.status == "completed" and self.output is not None


def register_spec(db: Session, spec: AgentSpec) -> AgentSpecRecord:
    """Record this agent version in the inventory if it is not there yet."""
    from sqlalchemy import select

    row = db.execute(select(AgentSpecRecord).where(
        AgentSpecRecord.name == spec.name, AgentSpecRecord.version == spec.version)).scalar_one_or_none()
    digest = spec.spec_sha256()
    if row is None:
        row = AgentSpecRecord(
            name=spec.name, version=spec.version, model=spec.resolved_model(), effort=spec.effort,
            max_steps=spec.max_steps, tools=list(spec.tools), prompt_sha256=spec.prompt_sha256(),
            spec_sha256=digest, purpose=spec.purpose)
        db.add(row)
        db.flush()
        ledger.record(db, actor_type="system", actor_id="runtime", action="agent_spec.registered",
                      entity_type="agent_spec", entity_id=row.id,
                      payload={"name": spec.name, "version": spec.version, "spec_sha256": digest})
    elif row.spec_sha256 != digest:
        raise RuntimeError(
            f"agent {spec.name}@{spec.version} changed without a new version; bump the version")
    return row


def _add_step(ctx: ToolContext, kind: str, name: str, inp: Any, out: Any, detail: dict[str, Any]) -> None:
    ctx.db.add(AgentStep(run_id=ctx.run.id, n=_next_n(ctx), kind=kind, name=name,
                         input_summary=summarise(inp), output_summary=summarise(out), detail=detail))


def _finish(db: Session, run: AgentRun, status: str, reason: str | None) -> None:
    run.status = status
    run.error = reason if status in ("failed", "refused") else run.error
    run.finished_at = datetime.now(UTC)
    ledger.record(db, actor_type="agent", actor_id=f"{run.agent_name}@{run.agent_version}",
                  action=f"agent.run_{status}", entity_type="agent_run", entity_id=run.id,
                  payload={"task": run.task, "steps": run.steps_count, "reason": reason,
                           "input_tokens": run.input_tokens, "output_tokens": run.output_tokens})
    db.flush()


def _parse(spec: AgentSpec, response: LLMResponse) -> tuple[BaseModel | None, str | None]:
    text = response.text().strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[4:] if text.lower().startswith("json") else text
    try:
        return spec.output_model.model_validate(json.loads(text)), None
    except (json.JSONDecodeError, ValidationError) as exc:
        return None, str(exc)[:600]


def run_agent(
    db: Session,
    spec: AgentSpec,
    *,
    task: str,
    scope: Scope,
    content: list[dict[str, Any]],
    llm: LLMClient,
    gateway: ToolGateway,
    record_key: str,
    started_by: tuple[str, str] = ("system", "workflow"),
    state: dict[str, Any] | None = None,
    prose_check: Callable[[BaseModel, dict[str, Any]], list[str]] | None = None,
) -> AgentOutcome:
    """Run the agent until it answers, is refused, fails, or reaches its step cap.

    `prose_check(answer, state)` returns what in a valid answer's text fails the number check. A
    first failure is sent back once, asking for fact references in place of typed figures; the
    second answer is returned whatever it says, and the caller's guardrails withhold what still
    fails. The model gets one chance to correct itself, never a loop."""
    register_spec(db, spec)
    run = AgentRun(
        agent_name=spec.name, agent_version=spec.version, model=spec.resolved_model(), task=task,
        borrower_id=scope.borrower_id, facility_id=scope.facility_id, cycle_id=scope.cycle_id,
        period_end=scope.period_end, scope=scope.to_json(), llm_mode=llm.mode,
        started_by_type=started_by[0], started_by_id=started_by[1])
    db.add(run)
    db.flush()
    ledger.record(db, actor_type="agent", actor_id=f"{spec.name}@{spec.version}", action="agent.run_started",
                  entity_type="agent_run", entity_id=run.id,
                  payload={"task": task, "scope": scope.to_json(), "model": run.model, "mode": llm.mode})
    ctx = ToolContext(db=db, scope=scope, run=run, state=dict(state or {}))
    messages: list[dict[str, Any]] = [{"role": "user", "content": content}]
    tools = gateway.definitions(spec.tools)
    schema = strict_schema(spec.output_model)
    system = spec.prompt()
    stamp, prompt_hash = spec_stamp(spec.name, spec.version, system=system, tools=tools, schema=schema,
                                    effort=spec.effort, max_tokens=spec.max_tokens, model=run.model)
    retried_shape = False
    retried_prose = False
    exchange = 0

    while True:
        exchange += 1
        request = LLMRequest(
            model=run.model, system=system, messages=list(messages), tools=list(tools),
            output_schema=schema,
            effort=spec.effort, max_tokens=spec.max_tokens, record_key=f"{record_key}/{exchange:02d}",
            spec=stamp, spec_prompt=prompt_hash)
        try:
            response = llm.create(request)
        except Exception as exc:  # noqa: BLE001 - a failure never reads as a recommendation
            _finish(db, run, "failed", f"{type(exc).__name__}: {exc}"[:600])
            return AgentOutcome(run, "failed", reason="error")
        run.served_model = response.model or run.served_model
        # tokens written to the prompt cache are input the model read for the first time: count them as
        # input, or a cached run looks as if it read almost nothing
        run.input_tokens += response.usage.get("input_tokens", 0) + response.usage.get("cache_creation_input_tokens", 0)
        run.output_tokens += response.usage.get("output_tokens", 0)
        run.cache_read_tokens += response.usage.get("cache_read_input_tokens", 0)
        _add_step(ctx, "model", "response", f"exchange {exchange}", response.stop_reason,
                  {"stop_reason": response.stop_reason, "usage": response.usage,
                   "request_id": response.request_id, "tool_calls": [t["name"] for t in response.tool_uses()]})

        if response.stop_reason == "refusal":
            _finish(db, run, "refused", json.dumps(response.stop_details or {}))
            return AgentOutcome(run, "refused", reason="refusal")
        if response.stop_reason == "max_tokens":
            _finish(db, run, "failed", "the answer was cut off at the output limit")
            return AgentOutcome(run, "failed", reason="max_tokens")

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            results = []
            for call in response.tool_uses():
                if run.steps_count >= spec.max_steps:
                    results.append({"type": "tool_result", "tool_use_id": call["id"], "is_error": True,
                                    "content": "step cap reached; no further tool calls are possible"})
                    continue
                outcome = gateway.call(ctx, call["name"], call.get("input"), allowed=spec.tools)
                results.append({"type": "tool_result", "tool_use_id": call["id"],
                                "is_error": outcome.refused,
                                "content": json.dumps(outcome.content, default=str)})
            messages.append({"role": "user", "content": results})
            if run.steps_count >= spec.max_steps:
                run.raw_output = {"note": "step cap reached before an answer"}
                _add_step(ctx, "guardrail", "step_cap", run.steps_count, "abstain",
                          {"layer": "runtime", "check": "step_cap", "action": "abstain"})
                _finish(db, run, "abstained", "step_cap")
                return AgentOutcome(run, "abstained", reason="step_cap")
            continue

        # the model has answered
        parsed, problem = _parse(spec, response)
        run.raw_output = {"text": response.text()}
        if parsed is not None and prose_check is not None and not retried_prose:
            problems = prose_check(parsed, ctx.state)
            if problems:
                retried_prose = True
                _add_step(ctx, "guardrail", "number_check", len(problems), "retry",
                          {"layer": "narrative", "check": "number_check", "action": "retry",
                           "problems": len(problems)})
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": [{"type": "text", "text": (
                    "Some of your text did not pass the number check:\n- " + "\n- ".join(problems[:12]) +
                    "\nRewrite those parts. Every figure must be a {{fact:<id>}} reference to a fact you were "
                    "given or read; never type a digit for an amount, ratio or percentage, and never write "
                    "figures in words. Keep everything else as it was. Return the full corrected JSON object. "
                    "Do not call tools.")}]})
                tools = []
                continue
        if parsed is not None:
            run.output = parsed.model_dump(mode="json")
            _finish(db, run, "completed", None)
            return AgentOutcome(run, "completed", output=parsed)
        if retried_shape:
            _add_step(ctx, "guardrail", "schema", problem, "abstain",
                      {"layer": "runtime", "check": "schema", "action": "abstain", "detail": problem})
            _finish(db, run, "abstained", "schema")
            return AgentOutcome(run, "abstained", reason="schema")
        retried_shape = True
        _add_step(ctx, "guardrail", "schema", problem, "retry",
                  {"layer": "runtime", "check": "schema", "action": "retry", "detail": problem})
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": [{"type": "text", "text": (
            "Your answer did not match the required shape: " + (problem or "") +
            "\nReturn only the corrected JSON object. Do not call tools.")}]})
        tools = []
