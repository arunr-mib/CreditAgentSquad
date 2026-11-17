"""The Copilot: ask a question about a borrower or the portfolio. Read-only: the route starts an
agent run and records the exchange; it changes nothing else."""
import uuid
from collections.abc import Callable
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents import copilot
from app.agents.llm import LLMClient, client_for
from app.api.deps import require
from app.core.db import get_db
from app.core.roles import Permission
from app.domain.org import User

router = APIRouter(tags=["copilot"])


class TurnIn(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(max_length=8000)


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=copilot.MAX_QUESTION_CHARS)
    borrower_id: uuid.UUID | None = None
    history: list[TurnIn] = Field(default_factory=list, max_length=40)


def llm_factory() -> Callable[[], LLMClient]:
    """How the route gets its model client. Tests replace this with a scripted client."""
    return client_for


@router.post("/copilot/ask")
def ask(body: AskIn, db: Session = Depends(get_db), user: User = Depends(require(Permission.VIEW)),
        make_llm: Callable[[], LLMClient] = Depends(llm_factory)) -> dict:
    """Answer one question. The reply carries the rendered answer, the same answer with its fact
    references, the facts used, the citations that were found on their pages, the guardrail
    notes and the agent run id. An answer that cannot be grounded comes back as a refusal."""
    try:
        llm = make_llm()
    except RuntimeError as exc:  # live mode without a key: say so, never fall back to a guess
        raise HTTPException(503, "The Copilot's model is not available.") from exc
    try:
        response = copilot.ask(db, question=body.question, user=user, llm=llm, borrower_id=body.borrower_id,
                               history=[turn.model_dump() for turn in body.history])
    except LookupError as exc:
        raise HTTPException(404, "Borrower not found.") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    db.commit()
    return response.to_json()
