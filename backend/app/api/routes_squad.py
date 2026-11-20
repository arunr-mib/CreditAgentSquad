"""Endpoints for the Squad experience. Read models and thin writes; every rule lives in the domain."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.db import get_db
from app.domain.org import User
from app.squad.threads import build_thread

router = APIRouter(tags=["squad"])


@router.get("/threads/{borrower_id}")
def get_thread(borrower_id: uuid.UUID, db: Session = Depends(get_db), _: User = Depends(current_user)) -> dict:
    try:
        return build_thread(db, borrower_id)
    except LookupError as exc:
        raise HTTPException(404, "Client not found.") from exc
