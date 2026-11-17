"""Password hashing and server-side sessions."""
import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, Exception):  # noqa: BLE001 - any failure is a refusal
        return False


def new_session_token() -> tuple[str, str]:
    """Return (token for the cookie, sha256 of the token for storage)."""
    token = secrets.token_urlsafe(32)
    return token, token_digest(token)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def session_expiry(hours: int) -> datetime:
    return datetime.now(UTC) + timedelta(hours=hours)
