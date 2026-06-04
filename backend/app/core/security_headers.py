"""
Security headers middleware.

Adds the standard set of defensive HTTP headers to every response:

  - Strict-Transport-Security : enforce HTTPS once the user has
    visited over TLS (only emitted in non-dev environments — sending
    HSTS over localhost would brick the dev environment)
  - X-Content-Type-Options    : prevent MIME-sniffing
  - X-Frame-Options           : clickjacking defence (DENY beats
    SAMEORIGIN; the dashboard is never iframed by intent)
  - Referrer-Policy           : leak minimal info to outbound links
  - Permissions-Policy        : refuse browser features we don't use
  - Content-Security-Policy   : tight default policy. The Swagger UI
    at /docs needs unsafe-inline + cdn.jsdelivr — we relax CSP for
    that specific path only.

CSP is in *report-only* mode in development so console warnings don't
break iteration; it's enforced in staging and production.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings


# Tight default. Frontend connects to API on a separate origin, so
# 'self' here means the API origin — no fonts, scripts, or styles are
# served by the API (except Swagger UI, handled below).
_BASE_CSP = (
    "default-src 'self'; "
    "img-src 'self' data: blob:; "
    "style-src 'self' 'unsafe-inline'; "
    "script-src 'self'; "
    "connect-src 'self' https://api.company-information.service.gov.uk "
    "https://stream.companieshouse.gov.uk https://api.openai.com; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)

# Relaxed CSP for Swagger UI / ReDoc — they require inline scripts and
# the jsdelivr CDN. Applied only on those specific paths.
_DOCS_CSP = (
    "default-src 'self'; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "connect-src 'self'; "
    "frame-ancestors 'none'"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        path = request.url.path
        is_docs = path in ("/docs", "/redoc") or path.startswith("/docs/") or path.startswith("/redoc/")
        csp = _DOCS_CSP if is_docs else _BASE_CSP

        # In production / staging enforce CSP; in dev only report.
        if settings.environment == "development":
            response.headers["Content-Security-Policy-Report-Only"] = csp
        else:
            response.headers["Content-Security-Policy"] = csp

        # Always-on hardening
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()"
        )

        # HSTS only over real TLS — Chrome ignores HSTS over plaintext
        # but sending it in development causes confusion when devs
        # later switch ports.
        if settings.environment != "development":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        return response
