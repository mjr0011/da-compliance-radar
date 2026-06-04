# D&A Compliance Radar

**Lead Intelligence & Compliance Monitoring Platform for Dennis & Associates Accountants.**

A production-ready foundation for autonomously monitoring UK companies via the Companies House API, detecting overdue filings and compliance risk, scoring leads with AI, and pushing alerts into Slack/Telegram/Email and your CRM.

---

## What's in this build

The platform shipped as a Phase 1 MVP and went through three hardening passes. It runs end-to-end on Docker.

### Core platform

- ✅ FastAPI backend with role-based access, full REST API, structured JSON logs
- ✅ PostgreSQL schema (Alembic migrations 0001, 0002, 0003): Companies, Compliance, Leads, Alerts, Users, Suppression, AuditLog, StreamState — plus MFA columns on users
- ✅ **Companies House** — REST integration **and** real-time streaming consumer (`stream.companieshouse.gov.uk`) with timepoint-resumed long polling, plus a **circuit breaker** for graceful API-outage handling
- ✅ **Lead scoring engine** — the exact +35/+20/+15 weights from the spec, pure functions, fully tested
- ✅ **Compliance risk engine** — separate from lead score, tiered scoring for accounts/confirmation overdue, strike-off, insolvency, dormant reactivation, officer churn; includes `predict_strike_off_window_days()`
- ✅ **AI classification** — OpenAI for lead categorisation + urgency + summary, with deterministic rule-based fallback
- ✅ **Celery + Redis workers** for polling, enrichment, alerting; Beat for scheduled scans
- ✅ **Alert dispatcher** — Slack, Telegram, branded HTML email (Resend) with SPF/DKIM/DMARC guidance
- ✅ **CRM workflow automation** — HubSpot/Pipedrive with pipeline rules, suggested next actions, due-hour assignment
- ✅ **Next.js 14 dashboard** (App Router + Tailwind + React Query) — homepage with live ticker + animated dashboard mock, login with MFA challenge step, dashboard, companies, leads, alerts, admin pages for analytics + audit log + suppression + MFA management
- ✅ Docker Compose for the entire stack including the streaming consumer service
- ✅ Pytest suite: **92 passing tests** (lead scoring, Companies House parsing, AI fallback, risk engine)

### Security & compliance

- ✅ **TOTP MFA with backup codes** — pyotp + RFC 6238, 10 single-use 8-character recovery codes per user, full enrollment UI at `/admin/mfa`
- ✅ **Refresh tokens** — short-lived access token + 30-day refresh, with single-flight auto-retry on the frontend
- ✅ **Failed-login lockout** — 5 attempts in 15 min → 30 min lock, Redis-backed with in-memory fallback
- ✅ **API rate limiting** — `slowapi` with per-endpoint limits and Redis backend; 120/min default, tighter on login + refresh
- ✅ **Companies House circuit breaker** — open after 5 consecutive failures, half-open after 60s, surfaced in `/ready` for monitoring
- ✅ **Append-only audit log** — every login, logout, refresh, user creation, suppression mutation captured with IP + user-agent
- ✅ **GDPR-ready suppression list** — extended with `SuppressionSource` enum (USER_OPT_OUT / CTPS_MATCH / CLIENT_REQUEST / DSR_ERASURE / MANUAL), `lawful_basis`, `request_received_at` for DSAR audit trails
- ✅ **Sentry integration** — `SENTRY_DSN` env var wires FastAPI + SQLAlchemy + Celery integrations
- ✅ **Structured logging** — `structlog` with JSON output in production, console renderer in dev
- ✅ **Security headers** — CSP, HSTS, X-Frame-Options, Referrer-Policy, Permissions-Policy on every response (backend middleware + Next.js config)
- ✅ **Non-root Docker containers** — both backend (uid 10001, nologin shell) and frontend (alpine `node` user); build tools dropped from runtime image
- ✅ **Environment separation** — `docker-compose.staging.yml` overlay + `.env.staging.example` template

### Operations & observability

- ✅ **Health endpoints** — `/health` (liveness, used by Docker HEALTHCHECK), `/live` (alias), `/ready` (deep readiness: DB connectivity + CH circuit breaker)
- ✅ **Admin analytics** — `/admin/analytics` page with lead funnel, urgency donut, alert delivery health, risk distribution, top audit events, pipeline value
- ✅ **Session expiry handling** — inline re-auth modal preserves user's current page (custom `SESSION_EXPIRED_EVENT` with ack handshake)
- ✅ **Frontend error boundaries** — `error.tsx` for route crashes, `global-error.tsx` for root-layout failures
- ✅ **Database backup script** — `scripts/backup.sh` for `pg_dump` + gzip + manifest, optional S3 upload, retention pruning
- ✅ **Demo seeder** — `python -m app.scripts.seed_demo_data` generates 1,000 plausible UK companies with realistic names/CRNs/postcodes/SIC codes, lead scores via the real scoring engine, 280+ leads, 450+ alerts, GDPR-varied suppression entries, 30-day audit-log history. Deterministic (`random.seed(42)`).

### What still needs your hand to finish

These have **clean stubs and integration points** but need your API keys or business decisions:

- 🔌 CRM credentials — service is wired, plug in HubSpot or Pipedrive tokens
- 🔌 Enrichment APIs (Google Places, Hunter) — interface defined, add keys
- 🔌 Intent monitoring (DataForSEO/SerpApi) — worker scheduler defined, scraper not implemented
- 🔌 Social monitoring (Reddit/X) — worker placeholder
- 🔌 CTPS suppression — `SuppressionSource.CTPS_MATCH` is ready; you need a daily job to load the CTPS file before running telephone outreach
- 🔌 Production hosting (Railway/AWS/Hetzner) — Docker Compose ready, pick your target
- 🔌 Uptime monitoring (BetterStack/UptimeRobot) — point at `/ready` + frontend URL
- 🔌 Per-environment Sentry projects — DSN config is wired, projects must be created externally

---

## Quick start

```bash
# 1. Clone, then copy env template
cp .env.example .env

# 2. Add at minimum these to .env:
#    COMPANIES_HOUSE_API_KEY=...   (free at developer.company-information.service.gov.uk)
#    JWT_SECRET=<random 64 chars>
#    POSTGRES_PASSWORD=<anything>
#    OPENAI_API_KEY=...            (optional but unlocks AI classification)

# 3. Bring the stack up
docker compose up --build

# 4. Run migrations & create first admin user
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.scripts.create_admin

# 5. (Optional) Seed 1,000 demo companies for a populated dashboard
docker compose exec backend python -m app.scripts.seed_demo_data
```

Then open:

- Dashboard: **http://localhost:3000**
- API docs (Swagger): **http://localhost:8000/docs**
- API docs (ReDoc): **http://localhost:8000/redoc**
- Health: **http://localhost:8000/health** · Readiness: **http://localhost:8000/ready**

---

## Architecture

```
                ┌──────────────────────────────────┐
                │   Next.js 14 dashboard           │
                │   homepage · login · dashboard   │
                │   companies · leads · alerts     │
                │   admin: audit-log, suppression  │
                └─────────────────┬────────────────┘
                                  │ access + refresh JWT
                                  ▼
                ┌──────────────────────────────────┐
                │   FastAPI                        │
                │   /api/auth /api/companies       │
                │   /api/leads /api/alerts         │
                │   /api/dashboard /api/admin      │
                └─────────────────┬────────────────┘
                                  │
                 ┌────────────────┼─────────────────┐
                 ▼                ▼                 ▼
          ┌──────────┐     ┌──────────┐      ┌──────────┐
          │ Postgres │     │  Redis   │ ◄─── │  Beat    │
          └──────────┘     └────┬─────┘      └──────────┘
                                │
                ┌───────────────┼──────────────────┐
                ▼               ▼                  ▼
       ┌──────────────┐   ┌──────────┐   ┌──────────────────┐
       │  Celery      │   │ Streaming│   │  Risk engine /   │
       │  workers     │   │ consumer │   │  lead scoring    │
       └──┬───────────┘   └────┬─────┘   │  (pure funcs)    │
          │                    │         └──────────────────┘
          │                    │
  ┌───────┼────────────────────┼──────────────────┐
  ▼       ▼                    ▼                  ▼
┌──────────┐  ┌──────────┐  ┌──────────────┐  ┌────────┐
│Companies │  │  OpenAI  │  │Slack/TG/Email│  │ HubSpot│
│  House   │  │ classify │  │  dispatcher  │  │   /PD  │
└──────────┘  └──────────┘  └──────────────┘  └────────┘
```

See `docs/ARCHITECTURE.md` for the full design, `docs/DEPLOYMENT.md` for staging/production hardening, and `docs/COMPLIANCE.md` for the GDPR/PECR posture.

---

## Project layout

```
da-compliance-radar/
├── docker-compose.yml              # dev stack
├── docker-compose.staging.yml      # staging overlay
├── .env.example                    # dev secrets template
├── .env.staging.example            # staging secrets template
├── backend/                        # FastAPI + SQLAlchemy + Celery
│   ├── app/
│   │   ├── main.py                 # FastAPI entrypoint, Sentry init
│   │   ├── config.py               # pydantic-settings
│   │   ├── database.py             # SQLAlchemy session
│   │   ├── models/                 # 8 tables (incl. audit_log, stream_state)
│   │   ├── schemas/                # Pydantic DTOs
│   │   ├── api/                    # auth, companies, leads, alerts, dashboard, admin
│   │   ├── core/                   # security, deps, login_tracker, logging_config
│   │   ├── services/               # Companies House, scoring, risk engine, AI, alerts, CRM, audit
│   │   └── workers/                # Celery app, tasks, streaming_consumer
│   ├── alembic/versions/           # migrations 0001_initial + 0002_hardening
│   └── tests/                      # 92 passing tests
├── frontend/                       # Next.js 14 (App Router)
│   ├── app/
│   │   ├── page.tsx                # marketing homepage
│   │   ├── login/                  # auth entry
│   │   ├── dashboard/ companies/ leads/ alerts/
│   │   └── admin/audit-log/  admin/suppression/
│   ├── components/                 # AppShell, ui primitives
│   └── lib/                        # api client (refresh-token aware)
└── docs/                           # ARCHITECTURE, DEPLOYMENT, API, COMPLIANCE
```

---

## Compliance & legal

This platform processes only **publicly available company information** from Companies House under their official API terms, with optional B2B enrichment under UK GDPR Article 6(1)(f) legitimate interests. A suppression list table is included; you should run a Legitimate Interest Assessment (LIA) before live B2B outreach. See `docs/COMPLIANCE.md`.

---

## Licence

Proprietary — Dennis & Associates Accountants.
