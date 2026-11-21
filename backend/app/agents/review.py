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

# Written by code when the sheet has nothing to say about risks: no model text, and no figure.
NO_RISKS_SENTENCE = "No signals fired and no items are open for this period."

SECTIONS = ("summary", "performance", "covenants", "collateral", "risks")


class Section(BaseModel):
    section: Literal["summary", "performance", "covenants", "collateral", "risks"]
    body: str


class ReviewDraft(BaseModel):
    sections: list[Section]


SPEC = AgentSpec(name="review", version="1", purpose="Draft review commentary using fact references only.",
                 prompt_file="review.md", output_model=ReviewDraft, tools=(), effort="high", max_tokens=8000)


def nothing_to_say(sheet: dict[str, Any]) -> bool:
    """True when the sheet has no fired signal, no open item, no covenant test that is not a clean pass and no
    collateral that disagrees: only then is "nothing" the whole truth about risks, so code may say it."""
    collateral = sheet.get("collateral")
    return (not sheet.get("signals")
            and not any(i.get("status") == "open" for i in sheet.get("work_items", []))
            and all(c.get("outcome") == "compliant" for c in sheet.get("covenants", []))
            and (collateral is None or (collateral.get("outcome") == "agrees" and not collateral.get("mismatched_lines"))))


@dataclass
class DraftResult:
    run_id: uuid.UUID | None = None
    sections: dict[str, str] = field(default_factory=dict)  # section -> body with references
    notes: list[dict[str, Any]] = field(default_factory=list)
    code_sections: set[str] = field(default_factory=set)  # sections written by code, not by the model


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
    def typed_figures(answer, _state) -> list[str]:
        return [f"{section.section}: {problem.detail}" for section in answer.sections
                for problem in check_narrative(section.body, facts)]

    outcome = run_agent(db, SPEC, task="draft_review_commentary", scope=scope, content=content, llm=llm,
                        gateway=ToolGateway(), record_key=f"review/{borrower.code}/{cycle.period_end}",
                        prose_check=typed_figures)
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
                                 "section": section.section, "reason": problems[0].detail,
                                 "detail": f"{section.section}: {problems[0].detail}"})
        elif phrase:
            reason = f"proposes an action reserved for a person ({phrase})"
            result.notes.append({"layer": "policy", "check": "prohibited_phrase", "action": "section_dropped",
                                 "section": section.section, "reason": reason,
                                 "detail": f"{section.section}: {reason}"})
        elif not referenced_fact_ids(section.body) and section.section != "summary":
            result.notes.append({"layer": "narrative", "check": "no_facts", "action": "section_dropped",
                                 "section": section.section, "reason": "makes no reference to any fact",
                                 "detail": f"{section.section}: makes no reference to any fact"})
        else:
            result.sections[section.section] = section.body
    # a sheet with no fired signal and no open item has nothing for a risks section to cite: code writes the
    # sentence, whatever the model drafted (a model's "risks" there could only be invented or empty)
    if nothing_to_say(sheet):
        result.sections["risks"] = NO_RISKS_SENTENCE
        result.code_sections.add("risks")
        result.notes = [n for n in result.notes if n.get("section") != "risks"]
    outcome.run.guardrail_notes = result.notes
    return result
