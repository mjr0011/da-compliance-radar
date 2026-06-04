"""
Contact & business enrichment.

Each enricher is opt-in: if its key is empty it's skipped. Returns a
dict of fields to merge onto the Company row.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def enrich_via_google_places(company_name: str, locality: Optional[str]) -> dict[str, Any]:
    """
    Use Google Places Text Search to find a business's website, phone, rating.
    Free tier: $200/mo credit.
    """
    if not settings.google_places_api_key:
        return {}
    query = f"{company_name} {locality or ''}".strip()
    try:
        r = httpx.get(
            "https://maps.googleapis.com/maps/api/place/textsearch/json",
            params={"query": query, "key": settings.google_places_api_key},
            timeout=8.0,
        )
        r.raise_for_status()
        data = r.json()
        results = data.get("results") or []
        if not results:
            return {}
        top = results[0]
        place_id = top.get("place_id")

        # Details call to get website + phone
        if not place_id:
            return {}
        d = httpx.get(
            "https://maps.googleapis.com/maps/api/place/details/json",
            params={
                "place_id": place_id,
                "fields": "website,formatted_phone_number,rating,user_ratings_total",
                "key": settings.google_places_api_key,
            },
            timeout=8.0,
        )
        d.raise_for_status()
        details = d.json().get("result", {})
        return {
            "website": details.get("website"),
            "phone": details.get("formatted_phone_number"),
            "google_rating": details.get("rating"),
            "google_reviews_count": details.get("user_ratings_total"),
        }
    except (httpx.HTTPError, KeyError) as exc:
        logger.warning("Google Places enrichment failed for %r: %s", company_name, exc)
        return {}


def enrich_via_hunter(domain: str) -> dict[str, Any]:
    """
    Use Hunter.io domain-search to find a primary business email.
    """
    if not settings.hunter_api_key or not domain:
        return {}
    try:
        r = httpx.get(
            "https://api.hunter.io/v2/domain-search",
            params={"domain": domain, "api_key": settings.hunter_api_key, "limit": 1},
            timeout=8.0,
        )
        r.raise_for_status()
        data = r.json().get("data", {})
        emails = data.get("emails") or []
        if not emails:
            return {}
        return {"primary_email": emails[0].get("value")}
    except (httpx.HTTPError, KeyError) as exc:
        logger.warning("Hunter enrichment failed for %r: %s", domain, exc)
        return {}


def derive_domain(website: Optional[str]) -> Optional[str]:
    """Pull the bare domain out of a website URL string."""
    if not website:
        return None
    s = website.strip().lower()
    for prefix in ("https://", "http://", "www."):
        if s.startswith(prefix):
            s = s[len(prefix) :]
    return s.split("/", 1)[0] or None
