"""
Compliance risk engine — distinct from lead scoring.

Where `lead_scoring` answers *"is this company worth pursuing as a client?"*,
this module answers *"is this company in real trouble?"*.

The two questions correlate but aren't identical:
  - A profitable, well-run business in a priority sector is a high-value
    LEAD but low-RISK.
  - A failing micro-business in a dormant SIC code is high-RISK but
    low-value as a LEAD.

The compliance risk score (0-100) feeds:
  - The dashboard's "high-risk companies" KPI
  - Alert prioritisation (critical risk skips the lead-score threshold)
  - The compliance dashboard's strike-off-warning panel

Like `lead_scoring`, this is pure functions — testable, deterministic,
no I/O.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


# --- Risk factor weights ---
# Tuned so a clean company scores 0; a struck-off-imminent company nears 100.

RISK_WEIGHTS = {
    # Accounts filing
    "accounts_overdue_30d": 25,
    "accounts_overdue_90d": 15,      # +15 on top of the 30d band = 40 total
    "accounts_overdue_180d": 15,     # cumulative 55
    # Confirmation statement
    "confirmation_overdue_30d": 15,
    "confirmation_overdue_90d": 10,
    # Strike-off / insolvency signals
    "strike_off_warning": 30,
    "in_insolvency_history": 20,
    # Status indicators
    "status_dissolved": 50,           # already dissolved → max-tier risk artifact
    "status_liquidation": 35,
    "status_administration": 30,
    # Behavioural
    "no_filings_24mo": 15,
    "officer_churn_high": 10,        # 3+ officer changes in 12mo
    "dormant_to_active_recent": 10,  # reactivation often precedes problems
}

# Risk-level thresholds (0..100)
LEVEL_LOW_MAX = 24
LEVEL_MEDIUM_MAX = 49
LEVEL_HIGH_MAX = 74
# 75+ = critical


@dataclass
class RiskInputs:
    """Inputs for the compliance risk scorer — what we know about a company."""

    accounts_overdue_days: int = 0        # 0 = not overdue, positive = days past due
    confirmation_overdue_days: int = 0
    strike_off_warning: bool = False
    in_insolvency_history: bool = False
    status: Optional[str] = None
    last_filing_date: Optional[date] = None
    officer_changes_12mo: int = 0
    became_active_within_180d: bool = False


@dataclass
class RiskResult:
    risk_score: int
    risk_level: str
    breakdown: dict[str, int] = field(default_factory=dict)
    rationale: list[str] = field(default_factory=list)
    """Human-readable explanations, in priority order."""


# --- Helpers ---

def _days_since(d: Optional[date]) -> Optional[int]:
    if not d:
        return None
    return (date.today() - d).days


def _classify_level(score: int) -> str:
    if score <= LEVEL_LOW_MAX:
        return "low"
    if score <= LEVEL_MEDIUM_MAX:
        return "medium"
    if score <= LEVEL_HIGH_MAX:
        return "high"
    return "critical"


# --- Main scorer ---

def score_compliance_risk(inputs: RiskInputs) -> RiskResult:
    """Compute a 0-100 compliance-risk score with breakdown and rationale."""
    breakdown: dict[str, int] = {}
    rationale: list[str] = []

    def _add(factor: str, condition: bool, reason: str) -> None:
        if condition:
            breakdown[factor] = RISK_WEIGHTS[factor]
            rationale.append(reason)

    # Accounts overdue — tiered (each tier is additive)
    if inputs.accounts_overdue_days > 0:
        _add("accounts_overdue_30d", True, "Accounts overdue")
        _add(
            "accounts_overdue_90d",
            inputs.accounts_overdue_days >= 90,
            "Accounts overdue 90+ days",
        )
        _add(
            "accounts_overdue_180d",
            inputs.accounts_overdue_days >= 180,
            "Accounts overdue 180+ days — strike-off threshold approaching",
        )

    # Confirmation statement overdue — tiered
    if inputs.confirmation_overdue_days > 0:
        _add("confirmation_overdue_30d", True, "Confirmation statement overdue")
        _add(
            "confirmation_overdue_90d",
            inputs.confirmation_overdue_days >= 90,
            "Confirmation statement overdue 90+ days",
        )

    # Strike-off warning (explicit flag from CH)
    _add(
        "strike_off_warning",
        inputs.strike_off_warning,
        "Strike-off warning issued by Companies House",
    )

    # Insolvency history
    _add(
        "in_insolvency_history",
        inputs.in_insolvency_history,
        "Company has insolvency history",
    )

    # Status — these can pile on top of overdue factors
    status_norm = (inputs.status or "").lower()
    _add(
        "status_dissolved",
        "dissolved" in status_norm,
        "Company is dissolved",
    )
    _add(
        "status_liquidation",
        "liquidation" in status_norm,
        "Company is in liquidation",
    )
    _add(
        "status_administration",
        "administration" in status_norm,
        "Company is in administration",
    )

    # Behavioural signals
    last_filing_days = _days_since(inputs.last_filing_date)
    _add(
        "no_filings_24mo",
        last_filing_days is not None and last_filing_days >= 730,
        "No filings in 24+ months",
    )
    _add(
        "officer_churn_high",
        inputs.officer_changes_12mo >= 3,
        f"{inputs.officer_changes_12mo} officer changes in last 12 months",
    )
    _add(
        "dormant_to_active_recent",
        inputs.became_active_within_180d,
        "Recently reactivated from dormant",
    )

    risk_score = min(100, sum(breakdown.values()))
    return RiskResult(
        risk_score=risk_score,
        risk_level=_classify_level(risk_score),
        breakdown=breakdown,
        rationale=rationale,
    )


def predict_strike_off_window_days(inputs: RiskInputs) -> Optional[int]:
    """
    Heuristic: estimate how many days until Companies House would start
    strike-off proceedings, based on overdue thresholds.

    Returns None if no strike-off path is active.

    Background: Companies House typically starts strike-off action when
    accounts are around 6 months overdue or confirmation statement is 14+
    days overdue. These are heuristics, not guarantees.
    """
    if inputs.strike_off_warning:
        return 0
    candidates: list[int] = []
    if inputs.accounts_overdue_days > 0:
        candidates.append(max(0, 180 - inputs.accounts_overdue_days))
    if inputs.confirmation_overdue_days > 0:
        candidates.append(max(0, 14 - inputs.confirmation_overdue_days))
    if not candidates:
        return None
    return min(candidates)


def should_alert_on_risk(result: RiskResult) -> bool:
    """
    Risk-driven alert trigger.

    Critical-risk companies bypass the usual lead-score threshold because
    they need immediate human attention regardless of whether they're a
    good fit as a client.
    """
    return result.risk_level == "critical" or result.risk_score >= 60
