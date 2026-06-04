# Deployment

This is a Docker Compose stack first. Anything that runs Docker can run it: Railway, Fly.io, Render, Hetzner, DigitalOcean App Platform, AWS ECS, Kubernetes.

## Local development

```bash
cp .env.example .env
# Fill in at minimum:
#   COMPANIES_HOUSE_API_KEY
#   JWT_SECRET (anything 32+ chars)
#   POSTGRES_PASSWORD

docker compose up --build
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.scripts.create_admin
```

Dashboard: http://localhost:3000
API docs: http://localhost:8000/docs

## Railway (recommended for MVP)

Railway gives you Postgres, Redis, and three services (backend, worker, frontend) on one project for under £20/month.

1. Push the repo to GitHub.
2. New Railway project → "Deploy from GitHub" → select repo.
3. Add the `Postgres` and `Redis` plugins. Railway sets `DATABASE_URL` and `REDIS_URL` automatically.
4. Create three services from the same repo, with different Dockerfile paths and start commands:

| Service | Build context | Start command |
|---|---|---|
| backend | `./backend` | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| worker | `./backend` | `celery -A app.workers.celery_app worker --loglevel=info` |
| beat | `./backend` | `celery -A app.workers.celery_app beat --loglevel=info` |
| frontend | `./frontend` | `npm run build && npm start` |

5. Add the env-vars from `.env.example` to **every** service that needs them (backend + worker + beat share most).
6. Set `NEXT_PUBLIC_API_URL` on the frontend service to the backend's public URL.
7. SSH into the backend service: `railway run alembic upgrade head` and `railway run python -m app.scripts.create_admin`.

## Hetzner / DigitalOcean / single VPS

For a self-managed deployment, the same `docker-compose.yml` works. Add:

- **Caddy or Traefik** in front for TLS termination.
- **Backups**: `pg_dump` cron job sending to S3-compatible storage.
- **Monitoring**: a `watchtower` container for zero-touch image updates, or a CI/CD pipeline.

Example `docker-compose.prod.yml` overlay (production override):

```yaml
services:
  backend:
    restart: always
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
    environment:
      ENVIRONMENT: production
      DEBUG: "false"
  frontend:
    command: sh -c "npm run build && npm start"
  caddy:
    image: caddy:2-alpine
    restart: always
    ports: ["80:80", "443:443"]
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
    depends_on: [backend, frontend]

volumes:
  caddy_data:
```

Bring up with `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`.

## AWS (ECS Fargate)

For the eventual SaaS phase. Sketch:

- Push backend and frontend images to ECR.
- Two Fargate task definitions (backend, worker), one Lambda or task for Beat.
- RDS Postgres + ElastiCache Redis.
- ALB → backend; CloudFront → S3-hosted Next.js static export (or another ALB for SSR).
- Secrets in AWS Secrets Manager, fed in at task start.
- CloudWatch for logs, X-Ray for distributed tracing if you wire it up.

## Database migrations

Always run migrations before deploying new code:

```bash
docker compose exec backend alembic upgrade head
```

To generate a new migration after changing a model:

```bash
docker compose exec backend alembic revision --autogenerate -m "describe change"
# Inspect the file in alembic/versions/, then:
docker compose exec backend alembic upgrade head
```

## Companies House streaming (production-grade live updates)

The streaming consumer is shipped as its own docker-compose service (`streaming:`). It long-polls `https://stream.companieshouse.gov.uk/companies` for filing events across every company and:

1. Filters events down to the company numbers in the `companies` table (refreshed every 60s).
2. Enqueues `fetch_and_store_company.delay(...)` for each match.
3. Persists `event.timepoint` to the `stream_state` table after each batch so a restart resumes rather than re-fetches.

It's a single replica — two streamers would double-process. Restart policy is `unless-stopped`. Logs are JSON-structured (see Monitoring).

The Beat-scheduled `scan_tracked_companies` is the backstop: if the stream is down, polling closes the gap.

## Environments: dev, staging, production

`docker-compose.yml` is the dev baseline. `docker-compose.staging.yml` is a staging overlay that:

- Reads `.env.staging` instead of `.env`
- Removes source-bind mounts (image is immutable)
- Runs `uvicorn` with 4 workers, no `--reload`
- Runs the frontend as a production build (`npm run build && npm start`)
- Remaps host ports (backend 8001, frontend 3001) so staging can co-exist with dev on the same host
- Doesn't expose Postgres or Redis to the host
- Uses a namespaced Postgres volume (`postgres_data_staging`)

Bring up with:

```bash
cp .env.staging.example .env.staging
# Fill in staging-only values: separate JWT secret, separate API keys, separate Sentry project
docker compose -f docker-compose.yml -f docker-compose.staging.yml --env-file .env.staging up -d
docker compose -f docker-compose.yml -f docker-compose.staging.yml exec backend alembic upgrade head
```

For production, mirror the staging overlay shape with `.env.production` but deploy onto real infrastructure (managed Postgres, managed Redis, behind a load balancer with TLS). Hard rules:

- **Never** share a JWT secret across environments.
- **Never** share a Companies House API key across environments (rate-limit budget is per-key).
- **Always** use a separate Sentry project per environment so noise from staging doesn't drown prod alerts.
- **Always** point staging at a `#…-staging` Slack channel; never at the prod alert channel.

## Monitoring

### Sentry

Set `SENTRY_DSN` in the environment and the backend wires `FastApiIntegration`, `SqlalchemyIntegration`, and `CeleryIntegration` automatically (see `app/main.py` and `app/workers/celery_app.py`). Sample rate is 0.1 in production and 0 elsewhere — adjust to taste.

Per-environment Sentry projects keep stages clean. Tag releases with the git SHA at deploy time:

```bash
SENTRY_RELEASE=$(git rev-parse --short HEAD) docker compose up -d
```

### Structured logs

All log output is JSON in non-dev environments (see `app/core/logging_config.py`). Ship to whatever log aggregator the firm uses — CloudWatch, Datadog, Grafana Loki, Elastic. Don't write log-parsing scripts; the fields are already structured.

### Healthcheck & uptime

`GET /health` returns `{"status": "ok"}`. Wire it to your uptime monitor (UptimeRobot, Better Stack, Pingdom). Set a 30-second interval and alert on 2 consecutive failures.

### Optional: Flower

For Celery introspection (queued / active / failed tasks), add a fifth service:

```yaml
flower:
  build: ./backend
  command: celery -A app.workers.celery_app flower --port=5555
  ports: ["5555:5555"]
  env_file: .env
```

Don't expose it publicly without auth.

## Backups

Nightly Postgres dump to S3:

```bash
0 3 * * * docker compose exec -T postgres pg_dump -U $POSTGRES_USER $POSTGRES_DB \
  | gzip | aws s3 cp - s3://da-compliance-radar-backups/$(date +\%Y-\%m-\%d).sql.gz
```

Restore: `gunzip -c backup.sql.gz | docker compose exec -T postgres psql -U $POSTGRES_USER $POSTGRES_DB`.

## Common gotchas

- **`alembic upgrade head` runs against the database in `DATABASE_URL`.** Easy to forget when switching between local and a production database. The deploy script in CI should pin the URL explicitly.
- **CORS**: production deployments must add their frontend origin to `CORS_ALLOWED_ORIGINS` (comma-separated env var, read in `app/main.py`).
- **JWT secret rotation invalidates all sessions.** Plan a maintenance window or implement a graceful rollover (two-secret verification).
