"""The tool gateway: the only way an agent touches data.

- A tool's inputs never include borrower, loan, period or cycle. Those come from the run's
  scope, which code sets. The model cannot choose the evidence it is checked against.
- Inputs are validated against a closed schema. A bad call is refused and the refusal goes
  back to the model as evidence; nothing is calculated or written on a refusal.
- Every call is written to the run's trace and to the ledger.
"""
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy.orm import Session

from app.agents.schema import strict_schema
from app.core import ledger
from app.domain.agents import AgentRun, AgentStep

SUMMARY_LIMIT = 240


@dataclass(frozen=True)
class Scope:
    borrower_id: uuid.UUID | None = None
    facility_id: uuid.UUID | None = None
    period_end: date | None = None
    months: int | None = None
    cycle_id: uuid.UUID | None = None
    document_ids: tuple[uuid.UUID, ...] = ()

    def to_json(self) -> dict[str, Any]:
        return {
            "borrower_id": str(self.borrower_id) if self.borrower_id else None,
            "facility_id": str(self.facility_id) if self.facility_id else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "months": self.months,
            "cycle_id": str(self.cycle_id) if self.cycle_id else None,
            "document_ids": [str(d) for d in self.document_ids],
        }


class ToolInput(BaseModel):
    """Base class for tool inputs: unknown fields are refused."""

    model_config = ConfigDict(extra="forbid")


@dataclass
class ToolContext:
    db: Session
    scope: Scope
    run: AgentRun
    state: dict[str, Any] = field(default_factory=dict)  # per-run working memory for tools


class Refusal(Exception):
    """Raise inside a tool handler to refuse a call with a reason the model can act on."""


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_model: type[ToolInput]
    handler: Callable[[ToolContext, Any], dict[str, Any]]
    writes: bool = False  # read-only tools may be given to the Copilot


@dataclass
class ToolOutcome:
    content: dict[str, Any]
    refused: bool = False


def summarise(value: Any) -> str:
    text = value if isinstance(value, str) else repr(value)
    return text if len(text) <= SUMMARY_LIMIT else text[: SUMMARY_LIMIT - 1] + "…"


class ToolGateway:
    def __init__(self, tools: list[Tool] | None = None):
        self._tools: dict[str, Tool] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"tool {tool.name!r} is already registered")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        return self._tools[name]

    def definitions(self, names: tuple[str, ...] | list[str]) -> list[dict[str, Any]]:
        """Tool definitions in the order given (a stable order keeps the prompt cache valid)."""
        return [
            {"name": t.name, "description": t.description, "strict": True,
             "input_schema": strict_schema(t.input_model)}
            for t in (self._tools[n] for n in names)
        ]

    def call(self, ctx: ToolContext, name: str, raw_input: Any, *, allowed: tuple[str, ...]) -> ToolOutcome:
        started = time.monotonic()
        outcome = self._execute(ctx, name, raw_input, allowed)
        run = ctx.run
        run.steps_count += 1
        step = AgentStep(
            run_id=run.id, n=_next_n(ctx), kind="tool", name=name,
            input_summary=summarise(raw_input), output_summary=summarise(outcome.content),
            detail={"input": raw_input if isinstance(raw_input, dict) else {"raw": str(raw_input)},
                    "output": outcome.content},
            refused=outcome.refused, duration_ms=int((time.monotonic() - started) * 1000),
        )
        ctx.db.add(step)
        ledger.record(
            ctx.db, actor_type="agent", actor_id=f"{run.agent_name}@{run.agent_version}",
            action="agent.tool_refused" if outcome.refused else "agent.tool_called",
            entity_type="agent_run", entity_id=run.id,
            payload={"tool": name, "step": step.n, "input": step.input_summary,
                     "output": step.output_summary},
        )
        ctx.db.flush()
        return outcome

    def _execute(self, ctx: ToolContext, name: str, raw_input: Any, allowed: tuple[str, ...]) -> ToolOutcome:
        if name not in allowed or name not in self._tools:
            return ToolOutcome({"error": f"tool {name!r} is not available to this agent"}, refused=True)
        tool = self._tools[name]
        if not isinstance(raw_input, dict):
            return ToolOutcome({"error": "tool input must be a JSON object"}, refused=True)
        try:
            args = tool.input_model.model_validate(raw_input)
        except ValidationError as exc:
            problems = "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors())
            return ToolOutcome({"error": f"input refused: {problems}"}, refused=True)
        try:
            # a savepoint, so a tool that fails part-way leaves nothing behind
            with ctx.db.begin_nested():
                return ToolOutcome(tool.handler(ctx, args))
        except Refusal as exc:
            return ToolOutcome({"error": str(exc)}, refused=True)


def _next_n(ctx: ToolContext) -> int:
    ctx.state["_step_n"] = ctx.state.get("_step_n", 0) + 1
    return ctx.state["_step_n"]
