"""Sign in, sign out, and who am I."""
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import SESSION_COOKIE, current_user
from app.core import ledger
from app.core.config import get_settings
from app.core.db import get_db
from app.core.ledger import LedgerEvent
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


SIGN_IN_FAILED, SIGNED_IN = "auth.sign_in_failed", "auth.signed_in"


def _now() -> datetime:
    return datetime.now(UTC)


def _recent_failures(db: Session, user: User, minutes: int) -> list[datetime]:
    """When this account's sign-in failed, oldest first: inside the window and since its last
    successful sign-in. The ledger is the record, so the count cannot be reset by editing a row."""
    mine = (LedgerEvent.entity_type == "user", LedgerEvent.entity_id == str(user.id))
    last_ok = db.execute(select(func.max(LedgerEvent.seq)).where(LedgerEvent.action == SIGNED_IN, *mine)).scalar() or 0
    return list(db.execute(select(LedgerEvent.ts).where(
        LedgerEvent.action == SIGN_IN_FAILED, *mine, LedgerEvent.seq > last_ok,
        LedgerEvent.ts > _now() - timedelta(minutes=minutes)).order_by(LedgerEvent.seq)).scalars())


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=str(user.id), email=user.email, name=user.name, title=user.title, role=user.role,
        permissions=sorted(p.value for p in Permission if can(user.role, p)),
    )


@router.post("/login", response_model=UserOut)
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)) -> UserOut:
    user = db.execute(select(User).where(User.email == body.email.strip().lower())).scalar_one_or_none()
    settings = get_settings()
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email or password is not correct.")
    failures = _recent_failures(db, user, settings.login_lockout_minutes)
    limit = settings.login_max_failures
    if len(failures) >= limit:
        # locked: the password is not even checked, so guessing cannot continue
        wait = failures[-limit] + timedelta(minutes=settings.login_lockout_minutes) - _now()
        seconds = max(1, int(wait.total_seconds()))
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Too many failed sign-in attempts. Try again in about {-(-seconds // 60)} minutes.",
            headers={"Retry-After": str(seconds)})
    if not verify_password(user.password_hash, body.password):
        ledger.record(db, actor_type="system", actor_id="auth", action=SIGN_IN_FAILED, entity_type="user",
                      entity_id=user.id, payload={"failures_in_window": len(failures) + 1})
        if len(failures) + 1 >= limit:
            ledger.record(db, actor_type="system", actor_id="auth", action="auth.locked_out", entity_type="user",
                          entity_id=user.id, payload={"failures": len(failures) + 1,
                                                      "minutes": settings.login_lockout_minutes})
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email or password is not correct.")
    token, digest = new_session_token()
    db.add(UserSession(user_id=user.id, token_hash=digest, expires_at=session_expiry(settings.session_hours)))
    ledger.record(db, actor_type="user", actor_id=user.id, action=SIGNED_IN,
                  entity_type="user", entity_id=user.id)
    db.commit()
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", secure=settings.cookie_secure,
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
