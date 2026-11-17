"""Review Agent: drafts review commentary from the facts on the sheet. Every figure must be a
fact reference; code checks each section and drops any that types a figure. The draft is marked
as written by an agent until a person approves it."""
import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.llm import LLMClient
from app.agents.runtime import AgentSpec, run_agent
from app.agents.tools import Scope, ToolGateway
from app.domain.credit import Borrower
from app.domain.monitoring import Cycle
from app.guardrails.narrative import FactView, check_narrative, format_fact, referenced_fact_ids
from app.guardrails.policy import PROHIBITED_PHRASES

SECTIONS = ("summary", "performance", "covenants", "collateral", "risks")


class Section(BaseModel):
    section: Literal["summary", "performance", "covenants", "collateral", "risks"]
    body: str


class ReviewDraft(BaseModel):
    sections: list[Section]


SPEC = AgentSpec(name="review", version="1", purpose="Draft review commentary using fact references only.",
                 prompt_file="review.md", output_model=ReviewDraft, tools=(), effort="high", max_tokens=8000)


@dataclass
class DraftResult:
    run_id: uuid.UUID | None = None
    sections: dict[str, str] = field(default_factory=dict)  # section -> body with references
    notes: list[dict[str, Any]] = field(default_factory=list)


def draft_commentary(db: Session, *, borrower: Borrower, cycle: Cycle, sheet: dict[str, Any],
                     facts: dict[str, FactView], labels: dict[str, str], llm: LLMClient) -> DraftResult:
    """`sheet` is the structured review content; `facts` are the facts it references, by id;
    `labels` describe each fact in words."""
    result = DraftResult()
    listing = [{"id": fid, "what": labels.get(fid, ""), "value": format_fact(fact)} for fid, fact in facts.items()]
    content = [{"type": "text", "text": (
        f"Borrower: {borrower.name} ({borrower.industry}). Period ended {cycle.period_end:%B %-d, %Y}.\n\n"
        f"Review sheet (structure; figures appear as fact ids):\n{json.dumps(sheet, indent=1, default=str)}\n\n"
        f"Facts you may reference:\n{json.dumps(listing, indent=1)}")}]
    scope = Scope(borrower_id=borrower.id, period_end=cycle.period_end, months=cycle.months, cycle_id=cycle.id)
    outcome = run_agent(db, SPEC, task="draft_review_commentary", scope=scope, content=content, llm=llm,
                        gateway=ToolGateway(), record_key=f"review/{borrower.code}/{cycle.period_end}")
    result.run_id = outcome.run.id
    if not outcome.ok:
        result.notes.append({"layer": "runtime", "check": outcome.reason or "no_answer", "action": "no_draft",
                             "detail": "the Review Agent returned no usable draft"})
        return result
    for section in outcome.output.sections:  # type: ignore[union-attr]
        if section.section in result.sections:
            continue
        problems = check_narrative(section.body, facts)
        lowered = section.body.lower()
        phrase = next((p for p in PROHIBITED_PHRASES if p in lowered), None)
        if problems:
            result.notes.append({"layer": "narrative", "check": problems[0].check, "action": "section_dropped",
                                 "detail": f"{section.section}: {problems[0].detail}"})
        elif phrase:
            result.notes.append({"layer": "policy", "check": "prohibited_phrase", "action": "section_dropped",
                                 "detail": f"{section.section}: proposes an action reserved for a person ({phrase})"})
        elif not referenced_fact_ids(section.body) and section.section != "summary":
            result.notes.append({"layer": "narrative", "check": "no_facts", "action": "section_dropped",
                                 "detail": f"{section.section}: makes no reference to any fact"})
        else:
            result.sections[section.section] = section.body
    outcome.run.guardrail_notes = result.notes
    return result
