"""Password hashing + JWT access, refresh, and MFA-challenge tokens."""
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

ACCESS_TYPE = "access"
REFRESH_TYPE = "refresh"
MFA_CHALLENGE_TYPE = "mfa_challenge"
"""Short-lived token issued after password verification when MFA is enabled.
Holds the user id and is exchanged for full access/refresh via /api/auth/mfa/verify."""

REFRESH_TOKEN_EXPIRE_DAYS = 30
MFA_CHALLENGE_EXPIRE_MINUTES = 5


def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


def _build_token(
    subject: str | int,
    token_type: Literal["access", "refresh", "mfa_challenge"],
    extra_claims: Optional[dict[str, Any]] = None,
    expires_minutes: Optional[int] = None,
    expires_days: Optional[int] = None,
) -> str:
    now = datetime.now(timezone.utc)
    if expires_days is not None:
        delta = timedelta(days=expires_days)
    else:
        delta = timedelta(
            minutes=expires_minutes
            if expires_minutes is not None
            else settings.jwt_expire_minutes
        )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "typ": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + delta).timestamp()),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(
    subject: str | int,
    extra_claims: Optional[dict[str, Any]] = None,
    expires_minutes: Optional[int] = None,
) -> str:
    return _build_token(subject, ACCESS_TYPE, extra_claims, expires_minutes=expires_minutes)


def create_refresh_token(
    subject: str | int,
    extra_claims: Optional[dict[str, Any]] = None,
) -> str:
    return _build_token(
        subject, REFRESH_TYPE, extra_claims, expires_days=REFRESH_TOKEN_EXPIRE_DAYS
    )


def create_mfa_challenge_token(subject: str | int) -> str:
    """Short-lived token bridging password-verified login → MFA verification."""
    return _build_token(
        subject,
        MFA_CHALLENGE_TYPE,
        expires_minutes=MFA_CHALLENGE_EXPIRE_MINUTES,
    )


def decode_token(token: str, expected_type: Optional[str] = None) -> dict[str, Any]:
    """Decode + verify a JWT. Raises ValueError on bad token or wrong type."""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except JWTError as exc:
        raise ValueError(f"Invalid token: {exc}") from exc
    if expected_type and payload.get("typ") != expected_type:
        raise ValueError(
            f"Wrong token type: expected {expected_type}, got {payload.get('typ')}"
        )
    return payload


# Backwards-compatible alias used by deps.py
decode_access_token = decode_token
