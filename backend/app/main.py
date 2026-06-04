"""
FastAPI application entry point.

Wires up:
  - Sentry (if SENTRY_DSN is set)
  - Structured JSON logging
  - CORS (env-driven origin list)
  - SlowAPI rate limiter
  - Security-headers middleware
  - All routers
  - /health, /live, /ready meta endpoints
"""
from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app import __version__
from app.api import admin, alerts, auth, companies, dashboard, leads
from app.config import settings
from app.core.circuit_breaker import companies_house_breaker
from app.core.logging_config import get_logger, setup_logging
from app.core.rate_limit import limiter
from app.core.security_headers import SecurityHeadersMiddleware
from app.database import engine

setup_logging()
logger = get_logger(__name__)


# --- Sentry (optional) ---
SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            environment=settings.environment,
            release=f"da-compliance-radar@{__version__}",
            traces_sample_rate=0.1 if settings.environment == "production" else 0.0,
            profiles_sample_rate=0.1 if settings.environment == "production" else 0.0,
            integrations=[FastApiIntegration(), SqlalchemyIntegration()],
            send_default_pii=False,
        )
        logger.info("sentry.initialised", environment=settings.environment)
    except ImportError:
        logger.warning(
            "sentry.unavailable",
            note="Install sentry-sdk to enable error reporting",
        )


app = FastAPI(
    title="D&A Compliance Radar API",
    description=(
        "Lead intelligence & compliance monitoring platform for "
        "Dennis & Associates Accountants."
    ),
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
)

# --- Rate limiter ---
# Both wiring lines are needed: state for the limiter to read its config,
# and the exception handler so 429 responses come out clean.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
app.add_middleware(SlowAPIMiddleware)


# --- Security headers (HSTS, CSP, X-Frame, etc.) ---
app.add_middleware(SecurityHeadersMiddleware)


# --- CORS ---
ALLOWED_ORIGINS = (
    os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Routers ---
app.include_router(auth.router)
app.include_router(companies.router)
app.include_router(leads.router)
app.include_router(alerts.router)
app.include_router(dashboard.router)
app.include_router(admin.router)


# --- Generic error handler ---
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Catch-all to ensure error responses never leak stack traces.
    Sentry (when enabled) still captures via its own integration.
    """
    logger.exception("unhandled_exception", path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# --- Meta endpoints ---
# /health is the cheap liveness probe.
# /live is its alias for k8s/ingress conventions — same response.
# /ready is the deep readiness probe: succeeds only when the API can
# actually serve requests (DB reachable, breaker not stuck open, etc.).
# Splitting them lets load balancers route around an instance that's
# degraded without restarting it.


@app.get("/health", tags=["meta"])
@app.get("/live", tags=["meta"])
def liveness():
    """Process is up. Used by Docker HEALTHCHECK + load balancers."""
    return {"status": "ok", "version": __version__, "environment": settings.environment}


@app.get("/ready", tags=["meta"])
def readiness():
    """Deep readiness — succeeds only when the API can serve real traffic."""
    checks: dict[str, Any] = {}
    overall_ok = True

    # 1. Database
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = {"ok": True}
    except SQLAlchemyError as exc:
        checks["database"] = {"ok": False, "error": str(exc)[:200]}
        overall_ok = False

    # 2. Companies House circuit breaker
    cb_state = companies_house_breaker.state
    checks["companies_house_breaker"] = {
        "ok": cb_state != "open",
        "state": cb_state,
    }
    # Open breaker is degraded but the API can still serve cached data,
    # so readiness reports it without failing — surfaces it for monitoring.

    body = {
        "status": "ok" if overall_ok else "degraded",
        "version": __version__,
        "environment": settings.environment,
        "checks": checks,
    }
    code = status.HTTP_200_OK if overall_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=code, content=body)


@app.get("/", tags=["meta"])
def root():
    return {
        "service": "D&A Compliance Radar",
        "version": __version__,
        "docs": "/docs",
    }
