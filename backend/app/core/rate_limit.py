"""
Shared SlowAPI rate limiter.

Single instance imported by routes that want a `@limiter.limit("...")`
decorator. Storage backend is Redis when REDIS_URL is set, otherwise an
in-memory dict (fine for dev / single-process). The Redis backend is
required for production because rate limits must be consistent across
all uvicorn workers.

Limits are conservative defaults intended to stop credential-stuffing
and accidental load spikes — not to throttle legitimate users.
"""
from __future__ import annotations

import os

from slowapi import Limiter
from slowapi.util import get_remote_address


def _storage_uri() -> str:
    """
    Redis-backed when available; falls back to in-memory.

    SlowAPI accepts a `memory://` URI explicitly; the empty string
    triggers the same fallback but is less obvious in logs.
    """
    return os.environ.get("REDIS_URL") or "memory://"


# Key function uses X-Forwarded-For when behind a reverse proxy; the
# `get_remote_address` helper handles both the direct and proxied cases.
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_storage_uri(),
    # Default applied to any route that doesn't override.
    default_limits=["120/minute"],
    headers_enabled=True,  # send X-RateLimit-* response headers
)
