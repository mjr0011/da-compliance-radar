"""
AI classification service — wraps OpenAI for lead analysis.

Produces the structured JSON shape from the spec:
    {
      "category":        "Overdue Accounts" | "VAT Help" | ...,
      "urgency":         "low" | "medium" | "high" | "urgent",
      "estimated_value": "£2,500/year",
      "summary":         "...short narrative..."
    }

If OPENAI_API_KEY is not configured, this service falls back to a
deterministic rule-based classifier so the platform still works
end-to-end out of the box.
"""
from __future__ import annotations

import json
import logging
from typing import Optional, TypedDict

from openai import OpenAI, OpenAIError

from app.config import settings

logger = logging.getLogger(__name__)


class Classification(TypedDict):
    category: str
    urgency: str
    estimated_value: str
    summary: str


SYSTEM_PROMPT = """You are an analyst at a UK accountancy firm (Dennis & Associates).
You triage incoming company-monitoring signals into actionable accounting leads.

You must output a single valid JSON object with EXACTLY these keys:
  - category: one of [
      "Overdue Accounts",
      "Overdue Confirmation Statement",
      "Newly Incorporated",
      "Strike-off Risk",
      "VAT Help",
      "Self-Assessment",
      "Bookkeeping",
      "Payroll",
      "CIS / Construction",
      "Landlord Tax",
      "eCommerce Accounting",
      "MTD Compliance",
      "General Compliance"
    ]
  - urgency: one of ["low", "medium", "high", "urgent"]
  - estimated_value: a short string like "£2,500/year"
  - summary: 1-2 plain-English sentences, under 280 chars, describing
    the opportunity and why the firm should pursue it.

No prose outside the JSON. No markdown fencing.
"""


def _classify_with_openai(payload: dict) -> Classification:
    client = OpenAI(api_key=settings.openai_api_key)
    resp = client.chat.completions.create(
        model=settings.openai_model,
        response_format={"type": "json_object"},
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, default=str)},
        ],
    )
    content = resp.choices[0].message.content or "{}"
    return json.loads(content)


def _classify_with_rules(payload: dict) -> Classification:
    """Deterministic fallback when OpenAI isn't configured."""
    sic = (payload.get("sic_code") or "")[:2]
    overdue_accounts = payload.get("accounts_overdue", False)
    overdue_confirm = payload.get("confirmation_overdue", False)
    new_co = payload.get("newly_incorporated", False)

    if overdue_accounts:
        category = "Overdue Accounts"
        urgency = "urgent"
    elif overdue_confirm:
        category = "Overdue Confirmation Statement"
        urgency = "high"
    elif new_co:
        category = "Newly Incorporated"
        urgency = "medium"
    elif sic in {"41", "42", "43"}:
        category = "CIS / Construction"
        urgency = "medium"
    elif sic == "68":
        category = "Landlord Tax"
        urgency = "medium"
    elif sic == "47":
        category = "eCommerce Accounting"
        urgency = "medium"
    else:
        category = "General Compliance"
        urgency = "low"

    est_value = payload.get("estimated_value_gbp") or 1200
    name = payload.get("company_name", "this company")
    summary = (
        f"{name} matches the {category.lower()} profile. "
        f"Likely fee opportunity around £{int(est_value):,}/year."
    )
    return Classification(
        category=category,
        urgency=urgency,
        estimated_value=f"£{int(est_value):,}/year",
        summary=summary,
    )


def classify_lead(payload: dict) -> Classification:
    """
    Classify a lead. Accepts a dict with company + compliance fields.

    Falls back to rules if OpenAI is misconfigured or fails. Never raises
    — the caller can always store the result.
    """
    if settings.openai_api_key:
        try:
            return _classify_with_openai(payload)
        except (OpenAIError, json.JSONDecodeError, KeyError) as exc:
            logger.warning("OpenAI classification failed, falling back: %s", exc)
    return _classify_with_rules(payload)
