"""Sign in, sign out, and who am I."""
from datetime import UTC, datetime

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import SESSION_COOKIE, current_user
from app.core import ledger
from app.core.config import get_settings
from app.core.db import get_db
from app.core.roles import Permission, can
from app.core.security import new_session_token, session_expiry, token_digest, verify_password
from app.domain.org import User, UserSession

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    title: str
    role: str
    permissions: list[str]


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=str(user.id), email=user.email, name=user.name, title=user.title, role=user.role,
        permissions=sorted(p.value for p in Permission if can(user.role, p)),
    )


@router.post("/login", response_model=UserOut)
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)) -> UserOut:
    user = db.execute(select(User).where(User.email == body.email.strip().lower())).scalar_one_or_none()
    if user is None or not user.is_active or not verify_password(user.password_hash, body.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email or password is not correct.")
    settings = get_settings()
    token, digest = new_session_token()
    db.add(UserSession(user_id=user.id, token_hash=digest, expires_at=session_expiry(settings.session_hours)))
    ledger.record(db, actor_type="user", actor_id=user.id, action="auth.signed_in",
                  entity_type="user", entity_id=user.id)
    db.commit()
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax",
                        max_age=settings.session_hours * 3600, path="/")
    return _user_out(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response, db: Session = Depends(get_db), user: User = Depends(current_user),
    squad_session: str | None = Cookie(default=None),
) -> None:
    session = db.execute(
        select(UserSession).where(UserSession.token_hash == token_digest(squad_session or ""))
    ).scalar_one_or_none()
    if session is not None:
        session.revoked_at = datetime.now(UTC)
    ledger.record(db, actor_type="user", actor_id=user.id, action="auth.signed_out",
                  entity_type="user", entity_id=user.id)
    db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)) -> UserOut:
    return _user_out(user)
