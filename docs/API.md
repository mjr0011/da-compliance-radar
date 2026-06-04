# API reference

The live, interactive Swagger UI is at `http://localhost:8000/docs`. ReDoc is at `/redoc`. This document is the high-level summary.

## Authentication

All endpoints except `/api/auth/login`, `/api/auth/refresh`, `/health`, and `/` require a Bearer JWT.

```
POST /api/auth/login
Content-Type: application/json

{
  "email": "you@dennisandassociates.co.uk",
  "password": "..."
}
```

Response:

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user": { "id": 1, "name": "...", "email": "...", "role": "admin", "is_active": true, "created_at": "..." }
}
```

Attach the `access_token` to every subsequent request as `Authorization: Bearer <token>`. When it expires (60 minutes by default), exchange the refresh token for a new access token:

```
POST /api/auth/refresh
Content-Type: application/json

{ "refresh_token": "eyJ..." }
```

The frontend client in `frontend/lib/api.ts` does this automatically on any 401, with single-flight protection so concurrent requests don't trigger multiple refreshes.

### Failed-login lockout

Five failed login attempts in 15 minutes lock the account for 30 minutes. Locked attempts return `429 Too Many Requests` and are recorded in the audit log. Successful login clears the counter.

## Roles

- `viewer` — read-only on every resource.
- `manager` — viewer + update Lead status, fire alerts, trigger CRM sync.
- `admin` — manager + create new users.

## Endpoints

### Auth
| Method | Path | Role | Purpose |
|---|---|---|---|
| `POST` | `/api/auth/login` | public | Exchange email+password for access + refresh tokens |
| `POST` | `/api/auth/refresh` | public | Exchange refresh token for fresh access token |
| `POST` | `/api/auth/logout` | any | Audit-log a logout |
| `GET`  | `/api/auth/me` | any | Current user info |
| `POST` | `/api/auth/users` | admin | Create new user |

### Admin
| Method | Path | Role | Purpose |
|---|---|---|---|
| `GET` | `/api/admin/audit-log` | admin | Paginated append-only event log |
| `GET` | `/api/admin/suppression` | manager+ | Paginated suppression list |
| `POST` | `/api/admin/suppression` | manager+ | Add an entry (with `source` + optional `lawful_basis`) |
| `DELETE` | `/api/admin/suppression/{id}` | admin | Remove an entry |

Audit-log filters: `event_type` (partial match), `actor_email`, `limit`, `offset`.
Suppression filters: `source`, `limit`, `offset`.

### Companies
| Method | Path | Role | Purpose |
|---|---|---|---|
| `GET`  | `/api/companies` | any | List with filters (see below) |
| `GET`  | `/api/companies/{number}` | any | One company + its compliance row |
| `POST` | `/api/companies/{number}/refresh` | any | Queue a Companies House re-fetch |

Filters on the list endpoint:

- `q` — substring match on name or company number
- `sic_prefix` — e.g. `43`
- `locality` — substring match
- `min_lead_score`, `min_risk_score` — int 0–100
- `overdue_only` — boolean
- `limit` (default 25, max 200), `offset` — pagination

### Leads
| Method | Path | Role | Purpose |
|---|---|---|---|
| `GET`  | `/api/leads` | any | List with filters |
| `GET`  | `/api/leads/{id}` | any | One lead with company joined |
| `PATCH`| `/api/leads/{id}` | manager+ | Update status / assignee / notes |
| `POST` | `/api/leads/{id}/sync-crm` | manager+ | Queue CRM push |
| `POST` | `/api/leads/{id}/alert` | any | Re-fire the alert |

List filters: `status`, `urgency`, `lead_type`, `min_score`, `limit`, `offset`.

### Alerts
| Method | Path | Role | Purpose |
|---|---|---|---|
| `GET` | `/api/alerts` | any | List dispatched alerts |

List filters: `channel` (slack/telegram/email), `status` (sent/pending/failed), `limit`.

### Dashboard
| Method | Path | Role | Purpose |
|---|---|---|---|
| `GET` | `/api/dashboard` | any | Aggregated stats + sector breakdown |

### Meta
| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `GET` | `/` | Service descriptor |

## Error format

All errors are JSON with a `detail` field:

```json
{ "detail": "Lead not found" }
```

Status codes:

- `400` — validation error
- `401` — missing/invalid token
- `403` — wrong role
- `404` — resource missing
- `409` — conflict (e.g. duplicate email on user creation)
- `429` — Companies House rate-limit propagated (rare; workers retry transparently)

## Webhooks (not yet implemented)

A natural Phase 2 addition: outbound webhooks for `lead.created`, `lead.status_changed`, `alert.failed`. The Alert model already has the right shape to support fanning out to webhook URLs alongside Slack/Telegram/Email.
