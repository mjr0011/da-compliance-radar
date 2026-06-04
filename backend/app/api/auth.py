"""
Authentication routes — refresh tokens, lockout, MFA, audit logging.

Login flow:
    POST /api/auth/login
      → if MFA disabled: returns access + refresh + user
      → if MFA enabled : returns mfa_required + challenge_token (5 min)

    POST /api/auth/mfa/verify
      → exchanges challenge_token + 6-digit code (or backup code)
        for full access + refresh tokens

MFA enrollment (authenticated):
    POST /api/auth/mfa/setup    → fresh secret + provisioning URI + 10 backup codes
    POST /api/auth/mfa/confirm  → verify first code, flip mfa_enabled=True
    POST /api/auth/mfa/disable  → password re-auth required, clears MFA fields
"""
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, require_role
from app.core.login_tracker import LOCKOUT_SECONDS, MAX_ATTEMPTS, get_tracker
from app.core import mfa as mfa_service
from app.core.rate_limit import limiter
from app.core.security import (
    MFA_CHALLENGE_TYPE,
    REFRESH_TYPE,
    create_access_token,
    create_mfa_challenge_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import LoginRequest, Token, UserCreate, UserOut
from app.services import audit

router = APIRouter(prefix="/api/auth", tags=["auth"])


# --- Schemas ---


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenWithRefresh(Token):
    refresh_token: str


class LoginResponse(BaseModel):
    """
    Either a full token pair (no MFA) OR a challenge for MFA verification.
    Discriminated by `mfa_required`.
    """
    mfa_required: bool = False
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    challenge_token: Optional[str] = None
    user: Optional[UserOut] = None


class MFAVerifyRequest(BaseModel):
    challenge_token: str
    code: str
    """6-digit TOTP code OR 8-character backup code."""


class MFASetupResponse(BaseModel):
    secret: str
    provisioning_uri: str
    backup_codes: list[str]
    """Shown once. Server only stores hashes. User MUST save these."""


class MFAConfirmRequest(BaseModel):
    code: str


class MFADisableRequest(BaseModel):
    password: str
    """Re-auth gate before disabling MFA."""


# --- Helpers ---


def _client_meta(request: Request) -> tuple[str, str]:
    """Extract IP + user agent for audit logging."""
    forwarded = request.headers.get("x-forwarded-for")
    ip = forwarded.split(",")[0].strip() if forwarded else (
        request.client.host if request.client else ""
    )
    ua = request.headers.get("user-agent", "")
    return ip, ua


def _issue_session(db: Session, user: User, ip: str, ua: str) -> TokenWithRefresh:
    """Common code path for issuing access+refresh tokens after auth."""
    access = create_access_token(user.id, {"role": user.role})
    refresh = create_refresh_token(user.id)
    audit.record(db, "auth.login.success", actor=user, actor_ip=ip, actor_user_agent=ua)
    return TokenWithRefresh(
        access_token=access,
        refresh_token=refresh,
        user=UserOut.model_validate(user),
    )


# --- Login ---


@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")
def login(
    request: Request,
    payload: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
):
    ip, ua = _client_meta(request)
    email = payload.email.lower()
    tracker = get_tracker()

    if tracker.is_locked(email):
        audit.record(
            db, "auth.login.locked",
            actor_email=email, actor_ip=ip, actor_user_agent=ua,
            detail={"reason": "account_locked"},
        )
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Too many failed attempts. Try again in {LOCKOUT_SECONDS // 60} minutes.",
        )

    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        count = tracker.record_failure(email)
        audit.record(
            db, "auth.login.failed",
            actor_email=email, actor_ip=ip, actor_user_agent=ua,
            detail={"attempt": count, "max": MAX_ATTEMPTS},
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    if not user.is_active:
        audit.record(
            db, "auth.login.failed",
            actor_email=email, actor_ip=ip, actor_user_agent=ua,
            detail={"reason": "inactive"},
        )
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account disabled")

    tracker.clear(email)

    # MFA gate: if enabled, return a challenge instead of a session.
    if user.mfa_enabled:
        challenge = create_mfa_challenge_token(user.id)
        audit.record(db, "auth.login.mfa_challenge", actor=user, actor_ip=ip, actor_user_agent=ua)
        return LoginResponse(mfa_required=True, challenge_token=challenge)

    session = _issue_session(db, user, ip, ua)
    return LoginResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        user=session.user,
    )


# --- MFA verify (completes login when MFA is enabled) ---


@router.post("/mfa/verify", response_model=TokenWithRefresh)
@limiter.limit("15/minute")
def mfa_verify(
    request: Request,
    payload: MFAVerifyRequest,
    db: Annotated[Session, Depends(get_db)],
):
    ip, ua = _client_meta(request)
    try:
        claims = decode_token(payload.challenge_token, expected_type=MFA_CHALLENGE_TYPE)
    except ValueError:
        audit.record(
            db, "auth.mfa.failed",
            actor_ip=ip, actor_user_agent=ua,
            detail={"reason": "invalid_challenge"},
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired challenge")

    user = db.get(User, int(claims["sub"]))
    if not user or not user.is_active or not user.mfa_enabled or not user.mfa_secret:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "MFA not configured for this user")

    code = payload.code.strip().replace(" ", "")
    if len(code) == 6 and code.isdigit():
        # TOTP path
        if not mfa_service.verify_totp(user.mfa_secret, code):
            audit.record(
                db, "auth.mfa.failed",
                actor=user, actor_ip=ip, actor_user_agent=ua,
                detail={"kind": "totp"},
            )
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid code")
        audit.record(db, "auth.mfa.verified", actor=user, actor_ip=ip, actor_user_agent=ua, detail={"kind": "totp"})
    else:
        # Backup code path
        new_stored = mfa_service.verify_backup_code(user.mfa_backup_codes, code)
        if new_stored is None:
            audit.record(
                db, "auth.mfa.failed",
                actor=user, actor_ip=ip, actor_user_agent=ua,
                detail={"kind": "backup"},
            )
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid code")
        user.mfa_backup_codes = new_stored
        db.add(user)
        db.commit()
        audit.record(
            db, "auth.mfa.verified",
            actor=user, actor_ip=ip, actor_user_agent=ua,
            detail={"kind": "backup", "remaining": new_stored.count("\n") + (1 if new_stored else 0)},
        )

    return _issue_session(db, user, ip, ua)


# --- Refresh token ---


@router.post("/refresh", response_model=Token)
@limiter.limit("30/minute")
def refresh(
    request: Request,
    payload: RefreshRequest,
    db: Annotated[Session, Depends(get_db)],
):
    ip, ua = _client_meta(request)
    try:
        claims = decode_token(payload.refresh_token, expected_type=REFRESH_TYPE)
    except ValueError:
        audit.record(
            db, "auth.token.refresh.failed",
            actor_ip=ip, actor_user_agent=ua,
            detail={"reason": "invalid_token"},
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")

    user_id = claims.get("sub")
    user = db.get(User, int(user_id)) if user_id else None
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or disabled")

    new_access = create_access_token(user.id, {"role": user.role})
    audit.record(db, "auth.token.refresh", actor=user, actor_ip=ip, actor_user_agent=ua)
    return Token(access_token=new_access, user=UserOut.model_validate(user))


# --- Logout / me ---


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    ip, ua = _client_meta(request)
    audit.record(db, "auth.logout", actor=user, actor_ip=ip, actor_user_agent=ua)
    return None


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user


# --- MFA enrollment ---


@router.post("/mfa/setup", response_model=MFASetupResponse)
def mfa_setup(
    request: Request,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    """Begin MFA enrollment. Returns secret + provisioning URI + plaintext backup codes."""
    if user.mfa_enabled:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "MFA already enabled. Disable it first to re-enroll.",
        )

    secret = mfa_service.generate_secret()
    codes = mfa_service.generate_backup_codes()
    user.mfa_secret = secret
    user.mfa_backup_codes = mfa_service.hash_backup_codes(codes)
    # NOT setting mfa_enabled yet — that flips only after /confirm
    db.add(user)
    db.commit()

    ip, ua = _client_meta(request)
    audit.record(db, "auth.mfa.setup_started", actor=user, actor_ip=ip, actor_user_agent=ua)

    return MFASetupResponse(
        secret=secret,
        provisioning_uri=mfa_service.provisioning_uri(secret, user.email),
        backup_codes=codes,
    )


@router.post("/mfa/confirm", status_code=status.HTTP_204_NO_CONTENT)
def mfa_confirm(
    request: Request,
    payload: MFAConfirmRequest,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    """Verify the first TOTP code and activate MFA."""
    if user.mfa_enabled:
        raise HTTPException(status.HTTP_409_CONFLICT, "MFA already enabled")
    if not user.mfa_secret:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No pending MFA setup. Call /mfa/setup first.")
    if not mfa_service.verify_totp(user.mfa_secret, payload.code):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid code. Please try again.")

    user.mfa_enabled = True
    db.add(user)
    db.commit()

    ip, ua = _client_meta(request)
    audit.record(db, "auth.mfa.enabled", actor=user, actor_ip=ip, actor_user_agent=ua)
    return None


@router.post("/mfa/disable", status_code=status.HTTP_204_NO_CONTENT)
def mfa_disable(
    request: Request,
    payload: MFADisableRequest,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    """Password re-auth required to disable MFA."""
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Password incorrect")

    user.mfa_enabled = False
    user.mfa_secret = None
    user.mfa_backup_codes = None
    db.add(user)
    db.commit()

    ip, ua = _client_meta(request)
    audit.record(db, "auth.mfa.disabled", actor=user, actor_ip=ip, actor_user_agent=ua)
    return None


# --- Admin: user creation ---


@router.post(
    "/users",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def create_user(
    request: Request,
    payload: UserCreate,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    if db.query(User).filter(User.email == payload.email.lower()).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    new_user = User(
        name=payload.name,
        email=payload.email.lower(),
        role=payload.role,
        password_hash=hash_password(payload.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    ip, ua = _client_meta(request)
    audit.record(
        db, "user.created",
        actor=user, actor_ip=ip, actor_user_agent=ua,
        target_type="user", target_id=new_user.id,
        detail={"email": new_user.email, "role": new_user.role},
    )
    return new_user
