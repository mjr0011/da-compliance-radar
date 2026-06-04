"""
MFA service — TOTP enrollment, verification, and backup codes.

We use PyOTP for the standard RFC 6238 implementation, with a 30-second
period and 6-digit codes. Backup codes are 8-character alphanumeric and
stored as bcrypt hashes (newline-separated) on the User row, like the
password_hash field.

Enrollment flow:
    1. /api/auth/mfa/setup → server generates a fresh secret, returns
       the otpauth:// provisioning URI + 10 plaintext backup codes
       (shown ONCE — server stores only the hashes).
    2. User scans into Google Authenticator / 1Password / Authy.
    3. /api/auth/mfa/confirm with the first 6-digit code → server
       verifies + flips `mfa_enabled = True`.

Login flow with MFA:
    1. /api/auth/login with email + password → if MFA is enabled,
       server returns a short-lived "challenge" token (5 min) and
       status `mfa_required` — NO access/refresh issued yet.
    2. /api/auth/mfa/verify with the challenge token + code →
       full access/refresh tokens.

Backup codes are single-use: each verified code is removed from the
hash list. When all are used, the user must re-enroll.
"""
from __future__ import annotations

import secrets
import string
from typing import Optional

import pyotp
from passlib.context import CryptContext

# Reuse the same bcrypt context as passwords for backup codes.
# Note: bcrypt has a 72-byte input limit; our 8-char codes are well under.
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

ISSUER_NAME = "D&A Compliance Radar"
BACKUP_CODE_COUNT = 10
BACKUP_CODE_LEN = 8

# Random source — secrets.choice is the standard for security-sensitive randomness.
_ALPHABET = string.ascii_uppercase + string.digits  # no lowercase to reduce eyeball confusion


def generate_secret() -> str:
    """Fresh base32 TOTP secret (160 bits, per RFC 4226 recommendation)."""
    return pyotp.random_base32()


def provisioning_uri(secret: str, account_email: str) -> str:
    """otpauth:// URI for authenticator app QR codes."""
    return pyotp.TOTP(secret).provisioning_uri(
        name=account_email,
        issuer_name=ISSUER_NAME,
    )


def verify_totp(secret: str, code: str) -> bool:
    """
    Verify a 6-digit code against the user's secret.

    `valid_window=1` allows codes from the previous or next 30-second
    window, tolerating small clock drift. This is the industry default;
    higher windows weaken security for marginal UX gain.
    """
    if not secret or not code:
        return False
    code = code.strip().replace(" ", "")
    if not code.isdigit() or len(code) != 6:
        return False
    return pyotp.TOTP(secret).verify(code, valid_window=1)


def generate_backup_codes() -> list[str]:
    """Ten 8-character alphanumeric backup codes."""
    return [
        "".join(secrets.choice(_ALPHABET) for _ in range(BACKUP_CODE_LEN))
        for _ in range(BACKUP_CODE_COUNT)
    ]


def hash_backup_codes(codes: list[str]) -> str:
    """Newline-joined bcrypt hashes for persistence on the User row."""
    return "\n".join(_pwd.hash(c) for c in codes)


def verify_backup_code(stored: Optional[str], submitted: str) -> Optional[str]:
    """
    Check `submitted` against the stored hashes.

    Returns the *new* stored value (with the consumed hash removed) on
    match, or None on no match. Callers should persist the new value.
    """
    if not stored or not submitted:
        return None
    submitted = submitted.strip().upper().replace(" ", "")
    hashes = [h for h in stored.split("\n") if h]
    for i, h in enumerate(hashes):
        try:
            if _pwd.verify(submitted, h):
                # Consume the matched code by removing it
                remaining = hashes[:i] + hashes[i + 1 :]
                return "\n".join(remaining)
        except ValueError:
            # Malformed hash — skip rather than crash
            continue
    return None
