"""
Lead & risk scoring engine.

Implements the rule-based scoring system from the platform spec
(section 8). Pure functions — no DB or network access — so they're
trivially unit-testable.

Final lead score is bounded 0..100. The breakdown is preserved so the
UI can show *why* something scored high.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

# --- Configurable weights (spec section 8) ---

WEIGHTS = {
    "accounts_overdue": 35,
    "confirmation_overdue": 20,
    "newly_incorporated": 15,
    "priority_sector": 15,
    "active_website": 10,
    "target_region": 10,
    "hiring_signal": 10,
    "high_online_activity": 10,
}

# SIC code prefixes that map to D&A's priority industries.
# Source: ONS SIC 2007. Edit per the firm's actual target list.
PRIORITY_SIC_PREFIXES = {
    "41",  # Construction of buildings
    "42",  # Civil engineering
    "43",  # Specialised construction (CIS bread & butter)
    "47",  # Retail trade (ecommerce overlap)
    "55",  # Hospitality
    "56",  # Food service
    "62",  # IT consultancy
    "68",  # Real estate (landlords)
    "70",  # Management consultancy
    "85",  # Education
    "86",  # Healthcare
    "87",  # Residential care
    "88",  # Social care
    "96",  # Other personal services (salons, etc.)
}

# Target geographic regions. Match either postcode prefix or locality
# (case-insensitive). Tune for the firm's catchment.
TARGET_POSTCODE_PREFIXES = {
    "E", "EC", "N", "NW", "SE", "SW", "W", "WC",   # London
    "IG", "RM", "EN", "HA", "UB", "TW", "KT", "CR", "BR", "DA",  # Greater London
}

NEWLY_INCORPORATED_DAYS = 180  # Within last ~6 months


@dataclass
class ScoringInputs:
    """Inputs for the scoring engine — pulled together by the worker."""

    accounts_overdue: bool = False
    confirmation_overdue: bool = False
    strike_off_warning: bool = False
    in_insolvency: bool = False
    incorporation_date: Optional[date] = None
    sic_code: Optional[str] = None
    postal_code: Optional[str] = None
    locality: Optional[str] = None
    website: Optional[str] = None
    google_reviews_count: Optional[int] = None
    has_hiring_signal: bool = False  # set by Reddit/X monitor or careers page check
    has_high_online_activity: bool = False  # social posts in last 30d, etc.


@dataclass
class ScoringResult:
    lead_score: int
    risk_score: int
    breakdown: dict = field(default_factory=dict)
    # breakdown is { factor_name: points_awarded }


def _is_priority_sector(sic_code: Optional[str]) -> bool:
    if not sic_code:
        return False
    return any(sic_code.startswith(p) for p in PRIORITY_SIC_PREFIXES)


def _is_target_region(postal_code: Optional[str], locality: Optional[str]) -> bool:
    if postal_code:
        # UK outward code = letters at the start before the first digit
        # e.g. "SW1A 1AA" -> "SW", "EC2N 4DL" -> "EC", "E14 5AB" -> "E"
        outward = postal_code.upper().split(" ", 1)[0]
        prefix_chars = []
        for ch in outward:
            if ch.isalpha():
                prefix_chars.append(ch)
            else:
                break
        prefix = "".join(prefix_chars)
        if prefix in TARGET_POSTCODE_PREFIXES:
            return True
    if locality and "london" in locality.lower():
        return True
    return False


def _is_newly_incorporated(d: Optional[date]) -> bool:
    if not d:
        return False
    return (date.today() - d).days <= NEWLY_INCORPORATED_DAYS


def _has_active_website(website: Optional[str]) -> bool:
    return bool(website and website.strip())


def score_lead(inputs: ScoringInputs) -> ScoringResult:
    """
    Compute lead score (0-100) and risk score (0-100) for a company.

    Lead score = sum of weighted positive factors (capped at 100).
    Risk score = compliance-driven sub-score, separate signal.
    """
    breakdown: dict[str, int] = {}

    def _add(factor: str, condition: bool) -> None:
        if condition:
            breakdown[factor] = WEIGHTS[factor]

    _add("accounts_overdue", inputs.accounts_overdue)
    _add("confirmation_overdue", inputs.confirmation_overdue)
    _add("newly_incorporated", _is_newly_incorporated(inputs.incorporation_date))
    _add("priority_sector", _is_priority_sector(inputs.sic_code))
    _add("active_website", _has_active_website(inputs.website))
    _add("target_region", _is_target_region(inputs.postal_code, inputs.locality))
    _add("hiring_signal", inputs.has_hiring_signal)
    _add("high_online_activity", inputs.has_high_online_activity)

    lead_score = min(100, sum(breakdown.values()))

    # Risk score — compliance only, weighted differently
    risk = 0
    if inputs.accounts_overdue:
        risk += 50
    if inputs.confirmation_overdue:
        risk += 25
    if inputs.strike_off_warning:
        risk += 40
    if inputs.in_insolvency:
        risk += 30
    risk_score = min(100, risk)

    return ScoringResult(
        lead_score=lead_score,
        risk_score=risk_score,
        breakdown=breakdown,
    )


def classify_risk_level(risk_score: int) -> str:
    """Map numeric risk score to enum string."""
    if risk_score >= 75:
        return "critical"
    if risk_score >= 50:
        return "high"
    if risk_score >= 25:
        return "medium"
    return "low"


def classify_urgency(lead_score: int, days_until_deadline: Optional[int]) -> str:
    """Combine lead score and deadline proximity into an urgency tier."""
    if days_until_deadline is not None and days_until_deadline < 0:
        # Already overdue
        return "urgent" if lead_score >= 50 else "high"
    if lead_score >= 70:
        return "high"
    if lead_score >= 40:
        return "medium"
    return "low"


def estimate_annual_value_gbp(
    sic_code: Optional[str],
    lead_score: int,
    services: list[str] | None = None,
) -> float:
    """
    Rough annual fee estimate so the UI / alerts can show £ value.

    These numbers are placeholders calibrated to typical D&A pricing
    bands — edit `BASE_VALUES` to match the firm's actual rate card.
    """
    base = 1200.0  # statutory accounts baseline for a small Ltd
    if _is_priority_sector(sic_code):
        base += 800.0  # CIS / hospitality / care = more compliance work
    if lead_score >= 70:
        base *= 1.4
    elif lead_score >= 40:
        base *= 1.15
    return round(base, 2)
