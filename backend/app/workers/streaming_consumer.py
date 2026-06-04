"""
Companies House Streaming consumer.

Long-poll connection to https://stream.companieshouse.gov.uk/companies
that emits newline-delimited JSON for every filing event across the
entire UK register. We filter to tracked companies and enqueue a
re-fetch task for each.

Run as a dedicated service (see docker-compose.yml `streaming` service):

    python -m app.workers.streaming_consumer

Resume points: we persist the last seen `event.timepoint` to a small
state table so a restart resumes where it left off.
"""
from __future__ import annotations

import json
import logging
import signal
import sys
import time
from base64 import b64encode
from typing import Optional

import httpx
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models.company import Company
from app.models.stream_state import StreamState

logger = logging.getLogger(__name__)


class StreamingConsumer:
    """
    Reads the Companies House filing stream. For each event whose
    company_number is in our tracked set, enqueues a fetch_and_store
    Celery task.

    Designed to run forever. Reconnects on every disruption with
    exponential backoff (capped at 60s).
    """

    BACKOFF_INITIAL = 1.0
    BACKOFF_MAX = 60.0
    STREAM_PATH = "/companies"
    STATE_KEY = "filing_stream_timepoint"

    def __init__(self):
        if not settings.companies_house_api_key:
            raise RuntimeError("COMPANIES_HOUSE_API_KEY required for streaming")
        token = b64encode(f"{settings.companies_house_api_key}:".encode()).decode()
        self._auth_header = f"Basic {token}"
        self._stop = False
        self._tracked: set[str] = set()
        self._tracked_last_refresh = 0.0
        signal.signal(signal.SIGTERM, self._on_signal)
        signal.signal(signal.SIGINT, self._on_signal)

    def _on_signal(self, *_):
        logger.info("Shutdown signal received; finishing current event")
        self._stop = True

    # -- state persistence --

    def _load_timepoint(self) -> Optional[int]:
        db = SessionLocal()
        try:
            row = db.execute(
                select(StreamState).where(StreamState.key == self.STATE_KEY)
            ).scalar_one_or_none()
            return row.timepoint if row else None
        finally:
            db.close()

    def _save_timepoint(self, tp: int) -> None:
        db = SessionLocal()
        try:
            row = db.execute(
                select(StreamState).where(StreamState.key == self.STATE_KEY)
            ).scalar_one_or_none()
            if row:
                row.timepoint = tp
            else:
                row = StreamState(key=self.STATE_KEY, timepoint=tp)
                db.add(row)
            db.commit()
        finally:
            db.close()

    # -- tracked-set cache --

    def _refresh_tracked_set(self, ttl_seconds: float = 60.0) -> None:
        now = time.monotonic()
        if now - self._tracked_last_refresh < ttl_seconds and self._tracked:
            return
        db = SessionLocal()
        try:
            rows = db.execute(select(Company.company_number)).scalars().all()
            self._tracked = set(rows)
            self._tracked_last_refresh = now
            logger.info("Refreshed tracked set: %d companies", len(self._tracked))
        finally:
            db.close()

    # -- event handling --

    def _handle_event(self, event: dict) -> None:
        """Parse one stream event; dispatch fetch if interesting."""
        # The wrapping shape is documented as:
        # {"resource_kind": "company-profile|filing-history|...",
        #  "resource_id": "<company_number>", "data": {...},
        #  "event": {"timepoint": <int>, ...}}
        company_number = event.get("resource_id") or (
            event.get("data") or {}
        ).get("company_number")
        if not company_number:
            return
        company_number = company_number.upper().strip()
        self._refresh_tracked_set()
        if company_number not in self._tracked:
            return
        from app.workers.tasks import fetch_and_store_company  # avoid cycle
        fetch_and_store_company.delay(company_number)
        logger.info("Queued refresh for %s", company_number)

    # -- main loop --

    def run(self) -> None:
        backoff = self.BACKOFF_INITIAL
        while not self._stop:
            try:
                tp = self._load_timepoint()
                params = {"timepoint": tp} if tp else None
                url = f"{settings.companies_house_stream_url}{self.STREAM_PATH}"
                logger.info("Connecting to stream %s (timepoint=%s)", url, tp)
                with httpx.Client(timeout=None) as client:
                    with client.stream(
                        "GET",
                        url,
                        params=params,
                        headers={
                            "Authorization": self._auth_header,
                            "Accept": "application/json",
                        },
                    ) as response:
                        if response.status_code in (416, 429):
                            # 416 = bad timepoint; clear and retry
                            # 429 = rate limited
                            logger.warning(
                                "Stream returned %s; resetting timepoint",
                                response.status_code,
                            )
                            self._save_timepoint(0)
                            time.sleep(backoff)
                            backoff = min(backoff * 2, self.BACKOFF_MAX)
                            continue
                        response.raise_for_status()
                        backoff = self.BACKOFF_INITIAL  # successful connect

                        for raw_line in response.iter_lines():
                            if self._stop:
                                break
                            if not raw_line.strip():
                                continue  # heartbeat
                            try:
                                event = json.loads(raw_line)
                            except json.JSONDecodeError:
                                logger.warning("Bad event JSON: %r", raw_line[:200])
                                continue
                            self._handle_event(event)
                            tp_new = (event.get("event") or {}).get("timepoint")
                            if isinstance(tp_new, int):
                                self._save_timepoint(tp_new)
            except (httpx.HTTPError, httpx.RemoteProtocolError) as exc:
                logger.warning(
                    "Stream disconnected: %s. Reconnecting in %.1fs", exc, backoff
                )
                time.sleep(backoff)
                backoff = min(backoff * 2, self.BACKOFF_MAX)
            except Exception:
                logger.exception("Unexpected error in stream loop")
                time.sleep(backoff)
                backoff = min(backoff * 2, self.BACKOFF_MAX)

        logger.info("Streaming consumer exited cleanly")


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] streaming: %(message)s",
    )
    StreamingConsumer().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
