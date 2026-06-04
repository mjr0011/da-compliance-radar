"""Celery application + Beat schedule."""
import os

from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_process_init

from app.config import settings
from app.core.logging_config import setup_logging


@worker_process_init.connect
def _configure_worker(**_kwargs) -> None:
    """Each forked worker process needs its own logging + Sentry setup."""
    setup_logging()

    sentry_dsn = os.environ.get("SENTRY_DSN", "")
    if sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.celery import CeleryIntegration
            from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

            sentry_sdk.init(
                dsn=sentry_dsn,
                environment=settings.environment,
                traces_sample_rate=0.1 if settings.environment == "production" else 0.0,
                integrations=[CeleryIntegration(), SqlalchemyIntegration()],
                send_default_pii=False,
            )
        except ImportError:
            pass


celery_app = Celery(
    "da_compliance_radar",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/London",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_retry_delay=60,
    task_default_max_retries=3,
    # Per-task time limits so a stuck Companies House call doesn't
    # freeze a worker forever.
    task_soft_time_limit=120,
    task_time_limit=180,
)

# --- Periodic schedule ---
celery_app.conf.beat_schedule = {
    "scan-compliance-hourly": {
        "task": "app.workers.tasks.scan_tracked_companies",
        "schedule": settings.compliance_scan_interval_seconds,
    },
    "poll-new-incorporations-daily": {
        "task": "app.workers.tasks.poll_new_incorporations",
        "schedule": crontab(hour=7, minute=0),  # 07:00 London
    },
    "process-pending-leads": {
        "task": "app.workers.tasks.process_pending_leads",
        "schedule": 300.0,
    },
}
