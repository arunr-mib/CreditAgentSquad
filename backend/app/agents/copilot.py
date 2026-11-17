"""Copilot: answers a credit person's question about a borrower or the portfolio, from stored
facts and document pages only. It reads and never acts.

The model writes an answer with fact references and citations. Code then decides what the
person sees: each citation's quote must be on its page or the citation is dropped; every figure
must be a reference to a fact that a tool returned during this run, or a figure inside a
surviving quote; an answer that fails is replaced by a refusal written by code, never repaired
and never guessed. The exchange is recorded on the ledger with the user as the asker.
"""
import hashlib
import json
import uuid
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.copilot_tools import TOOL_NAMES, copilot_gateway
from app.agents.llm import LLMClient
from app.agents.runtime import AgentOutcome, AgentSpec, run_agent
from app.agents.tools import Scope
from app.core import ledger
from app.domain.agents import AgentRun, AgentStep
from app.domain.credit import Borrower
from app.domain.documents import Document, DocumentPage
from app.domain.org import User
from app.guardrails.narrative import FactView, check_narrative, referenced_fact_ids, render
from app.guardrails.numbers import extract_figures
from app.guardrails.quotes import quote_on_page

CANNOT_ANSWER = "I cannot answer that from what is on file."
MAX_FOLLOW_UPS = 3
MAX_HISTORY_TURNS = 8
MAX_TURN_CHARS = 2000
MAX_QUESTION_CHARS = 4000
MIN_QUOTE_WORDS = 4

# Why an answer was withheld, in words a person can act on. Code writes these; none has a figure.
_MISSING = {
    "figure_untraceable": "The draft answer stated a figure that was typed rather than taken from a stored fact.",
    "fact_unknown": "The draft answer referred to a fact that none of the lookups for this question returned.",
    "reference_malformed": "The draft answer contained a fact reference that could not be read.",
    "format_unknown": "The draft answer asked for a figure in a format that does not exist.",
    "no_grounding": "None of the quotes offered could be found on the pages cited, and no stored fact was referenced.",
    "empty_answer": "No answer was written.",
    "step_cap": "The lookups needed went past the limit for one question; ask about one thing at a time.",
    "schema": "The answer did not come back in a form that could be checked.",
    "max_tokens": "The answer was cut off before it could be checked.",
    "refusal": "The model declined to answer this question.",
    "error": "The model could not be reached, so nothing was looked up.",
}


class Citation(BaseModel):
    document_id: str
    page: int
    quote: str


class CopilotAnswer(BaseModel):
    answer: str
    citations: list[Citation]
    follow_ups: list[str]


SPEC = AgentSpec(
    name="copilot", version="1",
    purpose="Answer questions about a borrower or the portfolio from stored facts and documents. Read-only.",
    prompt_file="copilot.md", output_model=CopilotAnswer, tools=TOOL_NAMES, effort="medium", max_steps=16,
    max_tokens=8000)


@dataclass
class CopilotResponse:
    status: str  # answered | refused
    answer: str  # what the person reads: figures rendered by code
    answer_with_references: str  # the same text with {{fact:<id>}} in place of each figure
    fact_ids: list[str] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)  # verified on their pages
    follow_ups: list[str] = field(default_factory=list)
    guardrail_notes: list[dict[str, str]] = field(default_factory=list)
    agent_run_id: uuid.UUID | None = None
    borrower: dict[str, str] | None = None  # the borrower the answer is about, when there is one

    def to_json(self) -> dict[str, Any]:
        return {
            "status": self.status, "answer": self.answer, "answer_with_references": self.answer_with_references,
            "fact_ids": self.fact_ids, "citations": self.citations, "follow_ups": self.follow_ups,
            "guardrail_notes": self.guardrail_notes,
            "agent_run_id": str(self.agent_run_id) if self.agent_run_id else None, "borrower": self.borrower,
        }


def _note(layer: str, check: str, action: str, detail: str) -> dict[str, str]:
    return {"layer": layer, "check": check, "action": action, "detail": detail}


def _content(question: str, borrower: Borrower | None, history: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    parts = []
    turns = [t for t in (history or []) if str(t.get("text", "")).strip()][-MAX_HISTORY_TURNS:]
    if turns:
        parts.append("Earlier turns of this conversation, for context only. Figures in them are not in scope: "
                     "look a figure up again before you state it.")
        for turn in turns:
            role = "assistant" if turn.get("role") == "assistant" else "user"
            parts.append(f"<earlier_turn role=\"{role}\">\n{str(turn['text'])[:MAX_TURN_CHARS]}\n</earlier_turn>")
    parts.append(f"The borrower open in this conversation is {borrower.name}." if borrower is not None else
                 "No borrower is open in this conversation.")
    parts.append(f"<question>\n{question}\n</question>")
    return [{"type": "text", "text": "\n\n".join(parts)}]


def _verify_citations(db: Session, citations: list[Citation], borrowers: set[uuid.UUID],
                      notes: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Keep a citation only when its quote is on the cited page of a document that belongs to a
    borrower this run looked at. Code reads the page; the model's word is not evidence."""
    kept: list[dict[str, Any]] = []
    for n, citation in enumerate(citations, start=1):
        def drop(check: str, why: str, n: int = n) -> None:
            notes.append(_note("quotes", check, "citation_dropped", f"citation {n}: {why}"))

        try:
            doc = db.get(Document, uuid.UUID(citation.document_id.strip()))
        except ValueError:
            doc = None
        if doc is None or doc.borrower_id not in borrowers:
            drop("document_not_in_scope", "the document is not one this question looked at")
            continue
        page = db.execute(select(DocumentPage).where(
            DocumentPage.document_id == doc.id, DocumentPage.page_number == citation.page)).scalar_one_or_none()
        if page is None or not page.has_text:
            drop("page_not_readable", f"{doc.title} has no readable page with that number")
            continue
        if len(citation.quote.split()) < MIN_QUOTE_WORDS:
            drop("quote_too_short", "a quote must be a phrase from the page, not a word or a bare figure")
            continue
        if not quote_on_page(page.text, citation.quote):
            drop("quote_not_on_page", f"the quoted words are not on the cited page of {doc.title}")
            continue
        entry = {"document_id": str(doc.id), "document_title": doc.title, "page": page.page_number,
                 "quote": citation.quote.strip()}
        if entry not in kept:
            kept.append(entry)
    return kept


def _follow_ups(items: list[str], notes: list[dict[str, str]]) -> list[str]:
    """Suggested next questions are words only: one with a figure or a reference is left out."""
    kept: list[str] = []
    for item in items:
        text = " ".join(item.split())
        if not text or text in kept:
            continue
        if "{{" in text or extract_figures(text):
            notes.append(_note("narrative", "follow_up_has_figure", "follow_up_dropped",
                               "a suggested question contained a figure and was left out"))
            continue
        kept.append(text)
    return kept[:MAX_FOLLOW_UPS]


def _guard(db: Session, output: CopilotAnswer, facts: dict[str, FactView], borrowers: set[uuid.UUID],
           notes: list[dict[str, str]]) -> tuple[str | None, list[dict[str, Any]]]:
    """Apply the guardrails. Returns (why the answer is withheld or None, surviving citations)."""
    citations = _verify_citations(db, output.citations, borrowers, notes)
    if not output.answer.strip():
        notes.append(_note("narrative", "empty_answer", "refuse", "the answer was empty"))
        return "empty_answer", citations
    allowed = [figure.value for c in citations for figure in extract_figures(c["quote"])]
    problems = check_narrative(output.answer, facts, allowed_figures=allowed)
    if problems:
        for check in dict.fromkeys(p.check for p in problems):
            count = sum(1 for p in problems if p.check == check)
            # the model's own figure is never shown, not even in a note; the raw answer is on the run
            notes.append(_note("narrative", check, "refuse",
                               f"{_MISSING[check]} ({'once' if count == 1 else 'more than once'})"))
        return problems[0].check, citations
    if output.citations and not citations and not referenced_fact_ids(output.answer):
        notes.append(_note("quotes", "no_grounding", "refuse", _MISSING["no_grounding"]))
        return "no_grounding", citations
    return None, citations


def _trace(db: Session, run: AgentRun, notes: list[dict[str, str]]) -> None:
    last = db.execute(select(func.max(AgentStep.n)).where(AgentStep.run_id == run.id)).scalar() or 0
    for offset, note in enumerate(notes, start=1):
        db.add(AgentStep(run_id=run.id, n=last + offset, kind="guardrail", name=note["check"],
                         input_summary=note["layer"], output_summary=note["action"], detail=note))


def ask(
    db: Session, *, question: str, user: User, llm: LLMClient, borrower_id: uuid.UUID | None = None,
    history: list[dict[str, Any]] | None = None,
) -> CopilotResponse:
    """Answer one question. `borrower_id` scopes the conversation to a borrower (the model cannot
    move it); without it the model may open a borrower by name or query the portfolio. `history`
    is earlier turns as `{"role": "user" | "assistant", "text": ...}`, given as context only."""
    question = question.strip()
    if not question:
        raise ValueError("ask a question")
    if len(question) > MAX_QUESTION_CHARS:
        raise ValueError("the question is too long")
    borrower = None
    if borrower_id is not None:
        borrower = db.get(Borrower, borrower_id)
        if borrower is None:
            raise LookupError("borrower not found")

    # working memory shared with the tools: the facts they return, the borrowers they read
    state: dict[str, Any] = {"facts": {}, "borrowers": {borrower.id} if borrower else set(), "opened": []}
    digest = hashlib.sha256(json.dumps(
        [question, str(borrower_id), [[t.get("role"), t.get("text")] for t in history or []]]).encode()).hexdigest()
    outcome: AgentOutcome = run_agent(
        db, SPEC, task="answer_question", scope=Scope(borrower_id=borrower.id if borrower else None),
        content=_content(question, borrower, history), llm=llm, gateway=copilot_gateway(),
        record_key=f"copilot/{digest[:16]}", started_by=("user", str(user.id)), state=state)
    run = outcome.run
    facts: dict[str, FactView] = state["facts"]
    notes: list[dict[str, str]] = []
    about = borrower or (db.get(Borrower, state["opened"][-1]) if state["opened"] else None)
    response = CopilotResponse(
        status="refused", answer=CANNOT_ANSWER, answer_with_references=CANNOT_ANSWER, agent_run_id=run.id,
        borrower={"id": str(about.id), "name": about.name} if about else None)

    if not outcome.ok:
        reason = outcome.reason if outcome.reason in _MISSING else "error"
        notes.append(_note("runtime", reason, "refuse", _MISSING[reason]))
        withheld: str | None = reason
    else:
        output: CopilotAnswer = outcome.output  # type: ignore[assignment]
        withheld, citations = _guard(db, output, facts, state["borrowers"], notes)
        if withheld is None:
            response.status = "answered"
            response.answer_with_references = output.answer.strip()
            response.answer = render(response.answer_with_references, facts)
            response.fact_ids = referenced_fact_ids(response.answer_with_references)
            response.citations = citations
            response.follow_ups = _follow_ups(output.follow_ups, notes)
    if withheld is not None:
        response.answer = response.answer_with_references = f"{CANNOT_ANSWER} {_MISSING[withheld]}"
    response.guardrail_notes = notes

    _trace(db, run, notes)
    run.guardrail_notes = notes
    run.output = response.to_json()  # the answer after guardrails; the model's own text stays in raw_output
    if about is not None and run.borrower_id is None:
        run.borrower_id = about.id
    ledger.record(
        db, actor_type="user", actor_id=user.id, action="copilot.asked", entity_type="agent_run", entity_id=run.id,
        payload={"question": question[:MAX_TURN_CHARS], "borrower_id": about.id if about else None,
                 "status": response.status, "run_status": outcome.status,
                 "answer_with_references": response.answer_with_references[:MAX_QUESTION_CHARS],
                 "fact_ids": response.fact_ids,
                 "citations": [{"document_id": c["document_id"], "page": c["page"]} for c in response.citations],
                 "guardrail": [{"check": n["check"], "action": n["action"]} for n in notes]})
    db.flush()
    return response
