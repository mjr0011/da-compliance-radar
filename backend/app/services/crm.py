"""
CRM sync service with workflow automation.

Beyond just pushing a Deal, the platform now:
  - Routes deals to a pipeline stage based on urgency
  - Creates a follow-up task with a context-aware due date
  - Generates an AI-suggested next action for the assignee
  - Records sync attempts in the audit log

Two providers: HubSpot and Pipedrive. Each is opt-in via env keys.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models.lead import Lead

logger = logging.getLogger(__name__)


# --- Workflow rules: map urgency to pipeline stage + due date ---

PIPELINE_RULES = {
    "urgent": {
        "hubspot_stage": "qualifiedtobuy",
        "due_in_hours": 4,
        "task_priority": "HIGH",
    },
    "high": {
        "hubspot_stage": "appointmentscheduled",
        "due_in_hours": 24,
        "task_priority": "HIGH",
    },
    "medium": {
        "hubspot_stage": "appointmentscheduled",
        "due_in_hours": 72,
        "task_priority": "MEDIUM",
    },
    "low": {
        "hubspot_stage": "appointmentscheduled",
        "due_in_hours": 168,  # one week
        "task_priority": "LOW",
    },
}


def _suggested_next_action(lead: Lead) -> str:
    """Generate a context-aware follow-up suggestion for the rep."""
    cat = lead.ai_category or lead.lead_type
    co = lead.company
    name = co.company_name if co else "the company"

    if "Overdue" in cat:
        return (
            f"Call {name} re. overdue filings. Mention specific deadline "
            f"and Companies House strike-off risk. Open with: 'We noticed "
            f"your accounts are overdue — would 15 minutes today help?'"
        )
    if "Newly Incorporated" in cat:
        return (
            f"Send the new-incorporation welcome email to {name}. Offer a "
            f"free 30-min compliance review covering accounts year-end and "
            f"VAT registration timing."
        )
    if "CIS" in cat:
        return (
            f"Reach out to {name} about CIS verification and the £100 "
            f"monthly return penalty. Send the CIS checklist PDF."
        )
    if "Landlord" in cat:
        return (
            f"Send {name} the landlord tax brief covering Section 24 "
            f"interest relief and MTD for income tax timing."
        )
    if "eCommerce" in cat:
        return (
            f"Outline VAT-on-marketplace-sales support for {name}. "
            f"Mention OSS/IOSS scheme if they ship internationally."
        )
    return (
        f"Introductory call with {name}. Lead with our specialism in "
        f"{cat.lower()} and reference our typical fee band."
    )


# --- HubSpot ---

def push_to_hubspot(lead: Lead) -> Optional[str]:
    """
    Create a Contact + Deal + Task in HubSpot.

    Returns the Deal ID. Uses the rules table to set pipeline stage,
    task priority, and due date.
    """
    if not settings.hubspot_api_key:
        return None
    co = lead.company
    if not co:
        return None

    headers = {
        "Authorization": f"Bearer {settings.hubspot_api_key}",
        "Content-Type": "application/json",
    }
    rules = PIPELINE_RULES.get(lead.urgency, PIPELINE_RULES["medium"])

    contact_id: Optional[str] = None
    if co.primary_email:
        try:
            r = httpx.post(
                "https://api.hubapi.com/crm/v3/objects/contacts",
                headers=headers,
                json={
                    "properties": {
                        "email": co.primary_email,
                        "company": co.company_name,
                        "phone": co.phone or "",
                        "website": co.website or "",
                    }
                },
                timeout=10.0,
            )
            if r.is_success:
                contact_id = r.json().get("id")
        except httpx.HTTPError as exc:
            logger.warning("HubSpot contact create failed: %s", exc)

    # Deal
    deal_r = httpx.post(
        "https://api.hubapi.com/crm/v3/objects/deals",
        headers=headers,
        json={
            "properties": {
                "dealname": f"{co.company_name} – {lead.ai_category or lead.lead_type}",
                "amount": str(int(lead.estimated_value_gbp or 0)),
                "pipeline": "default",
                "dealstage": rules["hubspot_stage"],
                "description": (
                    f"{lead.summary or ''}\n\n"
                    f"Source: D&A Compliance Radar\n"
                    f"Lead score: {lead.lead_score}/100\n"
                    f"Suggested next action: {_suggested_next_action(lead)}"
                ),
            }
        },
        timeout=10.0,
    )
    deal_r.raise_for_status()
    deal_id = deal_r.json().get("id")

    # Task
    due_at = datetime.now(timezone.utc) + timedelta(hours=rules["due_in_hours"])
    try:
        httpx.post(
            "https://api.hubapi.com/crm/v3/objects/tasks",
            headers=headers,
            json={
                "properties": {
                    "hs_task_subject": _suggested_next_action(lead)[:200],
                    "hs_task_body": lead.summary or "",
                    "hs_task_priority": rules["task_priority"],
                    "hs_task_status": "NOT_STARTED",
                    "hs_timestamp": int(due_at.timestamp() * 1000),
                }
            },
            timeout=10.0,
        )
    except httpx.HTTPError as exc:
        logger.warning("HubSpot task create failed (non-fatal): %s", exc)

    return deal_id


# --- Pipedrive ---

def push_to_pipedrive(lead: Lead) -> Optional[str]:
    """Create an Organization + Deal + Activity in Pipedrive."""
    if not (settings.pipedrive_api_token and settings.pipedrive_company_domain):
        return None
    co = lead.company
    if not co:
        return None

    base = f"https://{settings.pipedrive_company_domain}.pipedrive.com/api/v1"
    params = {"api_token": settings.pipedrive_api_token}
    rules = PIPELINE_RULES.get(lead.urgency, PIPELINE_RULES["medium"])

    # Organization
    org_id: Optional[int] = None
    try:
        org_r = httpx.post(
            f"{base}/organizations",
            params=params,
            json={"name": co.company_name},
            timeout=10.0,
        )
        if org_r.is_success:
            org_id = (org_r.json().get("data") or {}).get("id")
    except httpx.HTTPError as exc:
        logger.warning("Pipedrive org create failed: %s", exc)

    # Deal
    deal_r = httpx.post(
        f"{base}/deals",
        params=params,
        json={
            "title": f"{co.company_name} – {lead.ai_category or lead.lead_type}",
            "value": int(lead.estimated_value_gbp or 0),
            "currency": "GBP",
            "org_id": org_id,
        },
        timeout=10.0,
    )
    deal_r.raise_for_status()
    deal_id = (deal_r.json().get("data") or {}).get("id")

    # Activity (follow-up task)
    due_at = datetime.now(timezone.utc) + timedelta(hours=rules["due_in_hours"])
    try:
        httpx.post(
            f"{base}/activities",
            params=params,
            json={
                "subject": _suggested_next_action(lead)[:255],
                "type": "call",
                "due_date": due_at.date().isoformat(),
                "deal_id": deal_id,
                "org_id": org_id,
                "note": lead.summary or "",
            },
            timeout=10.0,
        )
    except httpx.HTTPError as exc:
        logger.warning("Pipedrive activity create failed: %s", exc)

    return str(deal_id) if deal_id else None


# --- Dispatcher ---

def sync_lead_to_crm(db: Session, lead: Lead) -> Optional[str]:
    """Push to the first configured CRM and record the external ID."""
    providers: list[tuple[str, Any]] = [
        ("hubspot", push_to_hubspot),
        ("pipedrive", push_to_pipedrive),
    ]
    for name, fn in providers:
        try:
            external_id = fn(lead)
        except (httpx.HTTPError, RuntimeError) as exc:
            logger.warning("CRM %s sync failed: %s", name, exc)
            continue
        if external_id:
            lead.crm_provider = name
            lead.crm_external_id = external_id
            lead.crm_synced_at = datetime.now(timezone.utc)
            db.commit()
            return external_id
    return None
