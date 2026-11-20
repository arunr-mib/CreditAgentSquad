"""Endpoints for the Squad experience. Read models and thin writes; every rule lives in the domain."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import current_user, require
from app.core.db import get_db
from app.core.roles import Permission
from app.domain.org import User
from app.squad.briefing import build_briefing
from app.squad.threads import build_thread

router = APIRouter(tags=["squad"])


@router.get("/threads/{borrower_id}")
def get_thread(borrower_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(require(Permission.VIEW))) -> dict:
    try:
        return build_thread(db, borrower_id)
    except LookupError as exc:
        raise HTTPException(404, "Client not found.") from exc


@router.get("/me/briefing")
def my_briefing(db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    return build_briefing(db, user)
