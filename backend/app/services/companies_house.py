"""
Companies House API client.

Wraps the official UK government Companies House API:
    https://developer.company-information.service.gov.uk

Authentication: HTTP Basic with the API key as the username and an empty
password. We use httpx with retries + sensible timeouts.

The service is intentionally thin and returns plain dicts — mapping to
our ORM happens in the workers (`app.workers.tasks`).
"""
from __future__ import annotations

import logging
from base64 import b64encode
from datetime import date, datetime
from typing import Any, Iterable, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings

logger = logging.getLogger(__name__)


class CompaniesHouseError(Exception):
    """Raised when Companies House returns an unexpected response."""


class CompaniesHouseClient:
    """Synchronous client suitable for Celery workers."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 15.0,
    ) -> None:
        self.api_key = api_key or settings.companies_house_api_key
        if not self.api_key:
            raise CompaniesHouseError(
                "COMPANIES_HOUSE_API_KEY is not set in environment."
            )
        self.base_url = (base_url or settings.companies_house_base_url).rstrip("/")
        # CH uses Basic auth: key as username, empty password
        token = b64encode(f"{self.api_key}:".encode()).decode()
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Basic {token}", "Accept": "application/json"},
            timeout=timeout,
        )

    # --- Public methods ---

    @retry(
        retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    def _get(self, path: str, params: Optional[dict] = None) -> dict[str, Any]:
        # Circuit breaker — fail-fast during sustained CH outages so
        # workers don't burn through their concurrency on guaranteed errors.
        from app.core.circuit_breaker import (
            CircuitOpenError,
            companies_house_breaker,
        )

        if not companies_house_breaker.allow():
            raise CompaniesHouseError(
                "Companies House circuit open — refusing call until cooldown elapses"
            )

        try:
            resp = self._client.get(path, params=params)
            if resp.status_code == 404:
                # 404 is a normal data condition, not an outage signal —
                # don't count it as a breaker failure.
                raise CompaniesHouseError(f"404 not found: {path}")
            if resp.status_code == 429:
                companies_house_breaker.record_failure()
                raise httpx.HTTPStatusError(
                    "Rate limited by Companies House",
                    request=resp.request,
                    response=resp,
                )
            resp.raise_for_status()
        except CompaniesHouseError:
            # 404 path — don't trip the breaker
            raise
        except (httpx.TransportError, httpx.HTTPStatusError):
            companies_house_breaker.record_failure()
            raise
        except CircuitOpenError:
            raise
        else:
            companies_house_breaker.record_success()
            return resp.json()

    def get_company_profile(self, company_number: str) -> dict[str, Any]:
        """GET /company/{number}"""
        return self._get(f"/company/{company_number.upper().strip()}")

    def get_filing_history(
        self, company_number: str, items_per_page: int = 50
    ) -> dict[str, Any]:
        """GET /company/{number}/filing-history"""
        return self._get(
            f"/company/{company_number.upper().strip()}/filing-history",
            params={"items_per_page": items_per_page},
        )

    def get_officers(self, company_number: str) -> dict[str, Any]:
        """GET /company/{number}/officers"""
        return self._get(f"/company/{company_number.upper().strip()}/officers")

    def search_companies(
        self,
        query: str,
        items_per_page: int = 20,
        start_index: int = 0,
    ) -> dict[str, Any]:
        """GET /search/companies?q={query}"""
        return self._get(
            "/search/companies",
            params={
                "q": query,
                "items_per_page": items_per_page,
                "start_index": start_index,
            },
        )

    def search_by_sic_code(
        self, sic_code: str, items_per_page: int = 100
    ) -> dict[str, Any]:
        """Advanced search by SIC code.

        See: /advanced-search/companies
        Used to seed the platform with target industries (e.g. CIS = 41/43).
        """
        return self._get(
            "/advanced-search/companies",
            params={"sic_codes": sic_code, "size": items_per_page},
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "CompaniesHouseClient":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()


# --- Parsing helpers ---

def parse_date(value: Optional[str]) -> Optional[date]:
    """Companies House returns ISO dates as strings; tolerate None."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        logger.warning("Could not parse CH date: %r", value)
        return None


def extract_compliance_fields(profile: dict) -> dict[str, Any]:
    """
    Pull the compliance-relevant fields out of a `/company/{number}` profile.

    Returns dict suitable for direct assignment onto a Compliance row.
    """
    accounts = profile.get("accounts", {}) or {}
    cs = profile.get("confirmation_statement", {}) or {}

    next_accounts = accounts.get("next_due") or accounts.get("next_made_up_to")
    last_accounts = accounts.get("last_accounts", {}) or {}

    accounts_due_date = parse_date(next_accounts)
    confirmation_due_date = parse_date(cs.get("next_due"))

    today = date.today()
    accounts_overdue = bool(accounts_due_date and accounts_due_date < today)
    confirmation_overdue = bool(confirmation_due_date and confirmation_due_date < today)

    # earliest upcoming deadline
    upcoming = [d for d in (accounts_due_date, confirmation_due_date) if d]
    next_deadline = min(upcoming) if upcoming else None
    days_until = (next_deadline - today).days if next_deadline else None

    return {
        "accounts_due_date": accounts_due_date,
        "accounts_last_made_up_to": parse_date(last_accounts.get("made_up_to")),
        "accounts_overdue": accounts_overdue,
        "confirmation_due_date": confirmation_due_date,
        "confirmation_last_made_up_to": parse_date(cs.get("last_made_up_to")),
        "confirmation_overdue": confirmation_overdue,
        "in_insolvency": bool(profile.get("has_insolvency_history")),
        "has_charges": bool(profile.get("has_charges")),
        "next_deadline": next_deadline,
        "days_until_next_deadline": days_until,
    }


def extract_company_fields(profile: dict) -> dict[str, Any]:
    """Pull the company-level fields out of a CH profile."""
    addr = profile.get("registered_office_address", {}) or {}
    sics: Iterable[str] = profile.get("sic_codes") or []
    sic_code = next(iter(sics), None)

    return {
        "company_number": profile["company_number"],
        "company_name": profile.get("company_name", ""),
        "status": profile.get("company_status"),
        "company_type": profile.get("type"),
        "sic_code": sic_code,
        "incorporation_date": parse_date(profile.get("date_of_creation")),
        "address_line_1": addr.get("address_line_1"),
        "address_line_2": addr.get("address_line_2"),
        "locality": addr.get("locality"),
        "region": addr.get("region"),
        "postal_code": addr.get("postal_code"),
        "country": addr.get("country"),
    }
