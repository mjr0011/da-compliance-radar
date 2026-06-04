# Architecture

This document describes how D&A Compliance Radar is wired internally. Read this once before contributing.

## 10,000-foot view

The platform is a classic **Postgres-backed Python web app with a Celery worker tier** and a separate Next.js frontend. Everything is a service in `docker-compose.yml`.

```
                       ┌──────────────────────────┐
                       │  Next.js 14 dashboard    │
                       │  (App Router + RQ + TW)  │
                       └────────────┬─────────────┘
                                    │ JWT
                                    ▼
┌──────────────────────────────────────────────────┐
│  FastAPI                                         │
│  /api/auth   /api/companies   /api/leads         │
│  /api/alerts /api/dashboard                      │
└────────────┬─────────────────────────────────────┘
             │
       ┌─────┴─────┐
       ▼           ▼
  ┌─────────┐ ┌─────────┐
  │Postgres │ │  Redis  │ ◄─── Celery Beat (schedules)
  └─────────┘ └────┬────┘
                   │
                   ▼
            ┌──────────────────────┐
            │  Celery Workers      │
            │  app.workers.tasks   │
            └──┬──────┬──────┬─────┘
               │      │      │
   ┌───────────┘      │      └──────────────┐
   ▼                  ▼                     ▼
┌─────────────┐  ┌──────────┐         ┌──────────────┐
│  Companies  │  │  OpenAI  │         │  Alert       │
│  House API  │  │  classify│         │  channels    │
└─────────────┘  └──────────┘         └──────────────┘
                                       (Slack/TG/Email)
```

## Why this split

- **API server** is stateless: it reads/writes Postgres and queues jobs. It's the only component the frontend talks to.
- **Workers** are where all third-party I/O happens. Companies House, OpenAI, Slack, CRMs — they all live here. The API only enqueues; never blocks on a remote call.
- **Beat** is a single replica that pushes schedule entries onto the queue. Periodic tasks live in `celery_app.beat_schedule`.
- **Postgres** is the system of record. The model graph is small (six tables) and indexed for the dashboard's filter combinations.

## Data flow: from signal to alert

1. **Beat** fires `scan_tracked_companies` every hour. It selects up to 100 stale companies and queues `fetch_and_store_company` for each.
2. **Worker** runs `fetch_and_store_company(company_number)`:
   - Calls Companies House `/company/{number}`.
   - Upserts a `Company` row and its `Compliance` child row.
   - Runs `score_lead()` (pure function, deterministic, tested).
   - Persists the lead score, risk score, and breakdown.
   - If `lead_score >= 40` and not on the suppression list → enqueues `_create_or_update_lead`.
3. `_create_or_update_lead(company_id)`:
   - Calls `classify_lead()` (OpenAI if configured, else rule-based fallback).
   - Upserts a `Lead` row keyed on (company, lead_type) for active statuses only.
   - If new and `lead_score >= 60` → enqueues `dispatch_alert_for_lead` and `push_lead_to_crm`.
4. `dispatch_alert_for_lead` renders a Markdown message and posts to every configured channel, persisting one `Alert` row per channel with `sent` / `failed` status.
5. `push_lead_to_crm` calls the first configured CRM (HubSpot, then Pipedrive) and stores the external ID on the `Lead`.

Each step is idempotent. A retry never duplicates anything because we upsert on natural keys (`company_number`, `(company_id, lead_type)`).

## Periodic tasks (Celery Beat)

| Task | Schedule | Purpose |
|---|---|---|
| `scan_tracked_companies` | Every 1h (configurable) | Refresh stale companies from CH |
| `poll_new_incorporations` | 07:00 Europe/London daily | Seed new entities from priority SIC codes |
| `process_pending_leads` | Every 5 min | Catch any high-scoring company that hasn't been turned into a Lead |

## Module map

```
app/
├── main.py              # FastAPI app + routers
├── config.py            # pydantic-settings; loads .env
├── database.py          # SQLAlchemy engine, Base, get_db()
├── models/              # ORM models (one per table)
├── schemas/             # Pydantic DTOs for the API
├── core/
│   ├── security.py      # password hashing, JWT sign/verify
│   └── deps.py          # FastAPI deps: current_user, require_role
├── api/                 # one router file per resource
├── services/            # external integrations + business logic
│   ├── companies_house.py
│   ├── lead_scoring.py       # pure-function scoring engine
│   ├── ai_classifier.py      # OpenAI + rule fallback
│   ├── alerts.py             # Slack / Telegram / Email
│   ├── crm.py                # HubSpot / Pipedrive
│   └── enrichment.py         # Google Places / Hunter
├── workers/
│   ├── celery_app.py    # Celery app + beat schedule
│   └── tasks.py         # @shared_task definitions
└── scripts/
    └── create_admin.py  # one-shot admin user seeder
```

## Design choices worth knowing

- **Sync SQLAlchemy + sync httpx.** The workload is heavy on external I/O latency, not concurrency. Celery's process-per-worker model already gives us parallelism. Async wouldn't pay for the complexity here.
- **Single-CRM-wins dispatcher.** If both HubSpot and Pipedrive credentials are set, only the first one that succeeds is recorded on the Lead. This is intentional: a Lead in two CRMs is a synchronization nightmare. Pick one per environment.
- **Rule-based AI fallback.** The classifier degrades gracefully without OpenAI. This keeps the demo loop usable even before the firm decides on AI spend.
- **Compliance and Company are 1-to-1.** They could be one table, but Compliance has its own update cadence (filing history check) and risk-level enum that benefits from isolation.
- **Suppression list checked at lead-creation time, not alert-dispatch time.** Once something is on the list, no Lead is created at all — it never reaches CRM, never reaches the dashboard outreach UI. Safer default.

## Scaling notes

- Postgres connection pool size is set to 10 + 20 overflow per process. For a single-box deployment that's fine. For multiple worker replicas, tune `pool_size` in `database.py` and consider PgBouncer.
- Companies House has a 600-requests-per-5-min limit. Workers respect this via `worker_prefetch_multiplier=1` and 1s exponential backoff on 429. If you scale to multiple worker pods, add a Redis-backed rate limiter (see `redis-rate-limit` recipe).
- Celery Beat must be a single replica. Running multiple Beats will double-schedule everything. Use a leader-election sidecar if you need HA there.

## Production hardening checklist

- Move CORS origin list to env-var driven config.
- Add Sentry SDK to both backend and frontend (skeletons are there in `requirements.txt` and `package.json` — wire them in).
- Replace SQLite-friendly types where used; the schema is already Postgres-only.
- Switch JWT to RS256 with a rotating key pair if you're issuing tokens to third parties.
- Add `aiohttp`-based streaming consumer for the Companies House streaming API (see `docs/DEPLOYMENT.md`).

## Hardened subsystems

The MVP shipped with the data flow above. The following subsystems were added in the hardening pass:

### Compliance risk engine — `app/services/risk_engine.py`

A separate signal from lead scoring. Lead score answers *"how good a prospect is this?"*; risk score answers *"how close is this company to a compliance disaster?"*. Different weights, different consumers (risk gates alert dispatch via `should_alert_on_risk()`; lead score gates Lead creation).

Tiered scoring for: accounts overdue at 30/90/180 days, confirmation statement overdue at 30/90 days, explicit strike-off warning, company status (dissolved/liquidation/administration), no filings in 24 months, officer churn (≥3 in 12 months), dormant→active reactivation. `predict_strike_off_window_days()` is a heuristic that gives outreach a clock to work against.

### Companies House streaming — `app/workers/streaming_consumer.py`

A standalone long-poll consumer for `stream.companieshouse.gov.uk/companies`. Persists the last received `timepoint` to the `stream_state` table so a restart resumes rather than re-fetches. Refreshes its tracked-company set every 60 seconds. Matched events enqueue `fetch_and_store_company`. Exponential backoff (1s→60s) on connection errors. SIGTERM-safe shutdown. Runs as its own docker-compose service (`streaming:`).

This is the real-time half of the data flow; the polling Beat schedule is the backstop.

### Audit log — `app/models/audit_log.py`

Append-only event store. Every login (success/failure/locked), logout, token refresh, user creation, suppression mutation, and CRM sync writes a row. Captures actor identity, IP, user-agent, target resource, and a JSON `detail` blob. Surfaced in the admin UI at `/admin/audit-log` (admin-only). Application code never updates or deletes rows.

### Refresh tokens & lockout — `app/core/security.py`, `app/core/login_tracker.py`

Login now issues an access token (short-lived) plus a refresh token (30 days). The frontend's `/lib/api.ts` auto-retries 401s after silent refresh. Failed-login tracker counts attempts per email in Redis (in-memory fallback for dev): 5 attempts in 15 minutes triggers a 30-minute lockout. Lockouts and failures are audit-logged.

### Suppression list — `app/models/suppression.py`

Extended from the original `(company_number|email|domain, reason)` to include `SuppressionSource` (USER_OPT_OUT, CTPS_MATCH, CLIENT_REQUEST, DSR_ERASURE, MANUAL), `lawful_basis`, and `request_received_at`. The Source field feeds the firm's GDPR compliance reports; the request timestamp is the audit trail for DSR responses. Managed via `/admin/suppression` (admin + manager).

### Structured logging — `app/core/logging_config.py`

`structlog` with JSON renderer in production and a console renderer in development. Routes stdlib `logging` calls through the same processor chain so every log entry — yours, FastAPI's, SQLAlchemy's, Celery's — has the same shape. Sentry is initialised from `SENTRY_DSN` if present, with `FastApiIntegration`, `SqlalchemyIntegration`, and `CeleryIntegration`.
