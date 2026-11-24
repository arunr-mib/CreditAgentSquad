"""Request dependencies: the signed-in user and permission checks."""
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.roles import Permission, can
from app.core.security import token_digest
from app.domain.org import User, UserSession

SESSION_COOKIE = "squad_session"
# A page number in a path: a document has at least one page and far fewer than this many.
PageNumber = Annotated[int, Path(ge=1, le=100_000)]


def current_user(
    db: Session = Depends(get_db), squad_session: str | None = Cookie(default=None)
) -> User:
    if not squad_session:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in to continue.")
    row = db.execute(
        select(UserSession, User)
        .join(User, User.id == UserSession.user_id)
        .where(UserSession.token_hash == token_digest(squad_session))
    ).first()
    if row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in to continue.")
    session, user = row
    if session.revoked_at is not None or session.expires_at < datetime.now(UTC) or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your session has ended. Sign in again.")
    return user


def require(permission: Permission):
    """Dependency factory: refuse the request unless the user's role grants the permission."""

    def _check(user: User = Depends(current_user)) -> User:
        if not can(user.role, permission):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Your role cannot do this ({permission.value}).")
        return user

    return _check
