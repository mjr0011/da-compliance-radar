"""
Background tasks — the heart of the automation.

Run periodically (Celery Beat) or on demand from the API. Each task is
idempotent and safe to retry.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone

from celery import shared_task
from sqlalchemy import select

from app.database import SessionLocal
from app.models.company import Company
from app.models.compliance import Compliance
from app.models.lead import Lead, LeadStatus, LeadUrgency
from app.models.suppression import SuppressionEntry
from app.services.ai_classifier import classify_lead
from app.services.alerts import dispatch_lead_alert
from app.services.companies_house import (
    CompaniesHouseClient,
    CompaniesHouseError,
    extract_company_fields,
    extract_compliance_fields,
)
from app.services.crm import sync_lead_to_crm
from app.services.enrichment import (
    derive_domain,
    enrich_via_google_places,
    enrich_via_hunter,
)
from app.services.lead_scoring import (
    ScoringInputs,
    classify_risk_level,
    classify_urgency,
    estimate_annual_value_gbp,
    score_lead,
)
from app.services.risk_engine import RiskInputs, score_compliance_risk
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


# --- Suppression check ---

def _is_suppressed(db, company_number: str, email: str | None, domain: str | None) -> bool:
    """Return True if the company/email/domain is on the suppression list."""
    q = db.query(SuppressionEntry).filter(
        (SuppressionEntry.company_number == company_number)
        | (SuppressionEntry.email == (email or ""))
        | (SuppressionEntry.domain == (domain or ""))
    )
    return db.query(q.exists()).scalar()


# --- 1. Fetch & store a single company ---

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def fetch_and_store_company(self, company_number: str) -> dict:
    """Fetch a company from Companies House, upsert, score, classify."""
    db = SessionLocal()
    try:
        with CompaniesHouseClient() as ch:
            try:
                profile = ch.get_company_profile(company_number)
            except CompaniesHouseError as exc:
                logger.warning("CH error for %s: %s", company_number, exc)
                return {"status": "not_found"}

        co_fields = extract_company_fields(profile)
        comp_fields = extract_compliance_fields(profile)

        company = (
            db.query(Company)
            .filter(Company.company_number == co_fields["company_number"])
            .first()
        )
        if not company:
            company = Company(**co_fields)
            db.add(company)
            db.flush()
        else:
            for k, v in co_fields.items():
                setattr(company, k, v)

        compliance = (
            db.query(Compliance).filter(Compliance.company_id == company.id).first()
        )
        if not compliance:
            compliance = Compliance(company_id=company.id, **comp_fields)
            db.add(compliance)
        else:
            for k, v in comp_fields.items():
                setattr(compliance, k, v)

        # Score
        scoring = score_lead(
            ScoringInputs(
                accounts_overdue=compliance.accounts_overdue,
                confirmation_overdue=compliance.confirmation_overdue,
                strike_off_warning=compliance.strike_off_warning,
                in_insolvency=compliance.in_insolvency,
                incorporation_date=company.incorporation_date,
                sic_code=company.sic_code,
                postal_code=company.postal_code,
                locality=company.locality,
                website=company.website,
                google_reviews_count=company.google_reviews_count,
            )
        )
        company.lead_score = scoring.lead_score
        company.risk_score = scoring.risk_score
        company.score_breakdown = json.dumps(scoring.breakdown)

        # Dedicated compliance risk engine — more nuanced than the
        # lead_scoring risk_score. Drives Compliance.risk_level.
        risk = score_compliance_risk(
            RiskInputs(
                accounts_overdue_days=(
                    -compliance.days_until_next_deadline
                    if (
                        compliance.accounts_overdue
                        and compliance.days_until_next_deadline is not None
                        and compliance.days_until_next_deadline < 0
                    )
                    else (1 if compliance.accounts_overdue else 0)
                ),
                confirmation_overdue_days=(1 if compliance.confirmation_overdue else 0),
                strike_off_warning=compliance.strike_off_warning,
                in_insolvency_history=compliance.in_insolvency,
                status=company.status,
                last_filing_date=compliance.last_filing_date,
            )
        )
        compliance.risk_level = risk.risk_level
        company.last_fetched_at = datetime.now(timezone.utc)

        db.commit()

        # Maybe promote to a lead
        if scoring.lead_score >= 40 and not _is_suppressed(
            db, company.company_number, company.primary_email, derive_domain(company.website)
        ):
            _create_or_update_lead.delay(company.id)

        return {
            "status": "ok",
            "company_number": company.company_number,
            "lead_score": scoring.lead_score,
            "risk_score": scoring.risk_score,
        }
    except Exception as exc:
        db.rollback()
        logger.exception("fetch_and_store_company failed")
        raise self.retry(exc=exc)
    finally:
        db.close()


# --- 2. Create / refresh a Lead row for a company ---

@shared_task(bind=True)
def _create_or_update_lead(self, company_id: int) -> dict:
    db = SessionLocal()
    try:
        company = db.get(Company, company_id)
        if not company:
            return {"status": "missing_company"}
        compliance = company.compliance

        # AI classification
        payload = {
            "company_number": company.company_number,
            "company_name": company.company_name,
            "sic_code": company.sic_code,
            "sic_description": company.sic_description,
            "locality": company.locality,
            "incorporation_date": (
                str(company.incorporation_date) if company.incorporation_date else None
            ),
            "newly_incorporated": _is_newly_incorporated(company.incorporation_date),
            "accounts_overdue": bool(compliance and compliance.accounts_overdue),
            "confirmation_overdue": bool(compliance and compliance.confirmation_overdue),
            "estimated_value_gbp": estimate_annual_value_gbp(
                company.sic_code, company.lead_score
            ),
        }
        classification = classify_lead(payload)

        # Determine lead_type from category
        lead_type = _category_to_lead_type(classification["category"])
        urgency = classification.get("urgency", "medium")

        # Upsert lead — one active lead per (company, lead_type)
        lead = (
            db.query(Lead)
            .filter(Lead.company_id == company.id, Lead.lead_type == lead_type)
            .filter(Lead.status.notin_([LeadStatus.WON.value, LeadStatus.LOST.value]))
            .first()
        )

        days_until = compliance.days_until_next_deadline if compliance else None
        if not lead:
            lead = Lead(
                company_id=company.id,
                source="companies_house",
                lead_type=lead_type,
                ai_category=classification["category"],
                summary=classification["summary"],
                urgency=urgency,
                lead_score=company.lead_score,
                estimated_value_gbp=payload["estimated_value_gbp"],
                status=LeadStatus.NEW.value,
            )
            db.add(lead)
            db.flush()
            is_new = True
        else:
            lead.ai_category = classification["category"]
            lead.summary = classification["summary"]
            lead.urgency = urgency
            lead.lead_score = company.lead_score
            lead.estimated_value_gbp = payload["estimated_value_gbp"]
            is_new = False

        db.commit()

        # New, high-value lead → fire alert + CRM sync
        if is_new and company.lead_score >= 60:
            dispatch_alert_for_lead.delay(lead.id)
            push_lead_to_crm.delay(lead.id)

        return {"status": "ok", "lead_id": lead.id, "new": is_new}
    finally:
        db.close()


def _category_to_lead_type(category: str) -> str:
    mapping = {
        "Overdue Accounts": "overdue_accounts",
        "Overdue Confirmation Statement": "confirmation_statement",
        "Newly Incorporated": "new_incorporation",
        "Strike-off Risk": "strike_off",
        "VAT Help": "vat_help",
        "Self-Assessment": "self_assessment",
        "Bookkeeping": "bookkeeping",
        "Payroll": "payroll",
        "CIS / Construction": "cis",
        "Landlord Tax": "landlord_tax",
        "eCommerce Accounting": "ecommerce",
        "MTD Compliance": "mtd",
    }
    return mapping.get(category, "general_compliance")


def _is_newly_incorporated(d) -> bool:
    if not d:
        return False
    return (date.today() - d).days <= 180


# --- 3. Periodic scan of all tracked companies ---

@shared_task
def scan_tracked_companies() -> dict:
    """Re-fetch every tracked company that hasn't been refreshed recently."""
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        stale = (
            db.execute(
                select(Company.company_number).where(
                    (Company.last_fetched_at == None) | (Company.last_fetched_at < cutoff)
                ).limit(100)
            )
            .scalars()
            .all()
        )
        for num in stale:
            fetch_and_store_company.delay(num)
        return {"queued": len(stale)}
    finally:
        db.close()


# --- 4. Poll for newly incorporated target-sector companies ---

@shared_task
def poll_new_incorporations() -> dict:
    """
    Use Companies House search by SIC code to discover new companies in
    priority sectors. Real implementation would query the streaming API;
    here we use advanced search with a date filter as a simple approach.
    """
    from app.services.lead_scoring import PRIORITY_SIC_PREFIXES

    queued = 0
    try:
        with CompaniesHouseClient() as ch:
            for sic_prefix in list(PRIORITY_SIC_PREFIXES)[:6]:  # rate-limit friendly
                try:
                    results = ch.search_by_sic_code(sic_prefix, items_per_page=20)
                except CompaniesHouseError:
                    continue
                for item in results.get("items", []):
                    cn = item.get("company_number")
                    if cn:
                        fetch_and_store_company.delay(cn)
                        queued += 1
    except CompaniesHouseError as exc:
        logger.warning("poll_new_incorporations skipped: %s", exc)
    return {"queued": queued}


# --- 5. Process pending leads — sweep for ones missing classification ---

@shared_task
def process_pending_leads() -> dict:
    db = SessionLocal()
    try:
        # Companies with lead_score >= 40 but no active Lead row
        candidates = (
            db.execute(
                select(Company.id).where(Company.lead_score >= 40).limit(50)
            )
            .scalars()
            .all()
        )
        for cid in candidates:
            has_lead = (
                db.execute(
                    select(Lead.id)
                    .where(
                        Lead.company_id == cid,
                        Lead.status.notin_([LeadStatus.WON.value, LeadStatus.LOST.value]),
                    )
                    .limit(1)
                )
                .first()
            )
            if not has_lead:
                _create_or_update_lead.delay(cid)
        return {"checked": len(candidates)}
    finally:
        db.close()


# --- 6. Dispatch alert ---

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def dispatch_alert_for_lead(self, lead_id: int) -> dict:
    db = SessionLocal()
    try:
        lead = db.get(Lead, lead_id)
        if not lead:
            return {"status": "missing"}
        alerts = dispatch_lead_alert(db, lead)
        return {"sent": len(alerts)}
    finally:
        db.close()


# --- 7. CRM sync ---

@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def push_lead_to_crm(self, lead_id: int) -> dict:
    db = SessionLocal()
    try:
        lead = db.get(Lead, lead_id)
        if not lead:
            return {"status": "missing"}
        ext_id = sync_lead_to_crm(db, lead)
        return {"crm_external_id": ext_id}
    finally:
        db.close()


# --- 8. Enrichment ---

@shared_task
def enrich_company(company_id: int) -> dict:
    db = SessionLocal()
    try:
        co = db.get(Company, company_id)
        if not co:
            return {"status": "missing"}
        # Google Places
        gp = enrich_via_google_places(co.company_name, co.locality)
        for k, v in gp.items():
            if v:
                setattr(co, k, v)
        # Hunter (only if we have a domain now)
        dom = derive_domain(co.website)
        h = enrich_via_hunter(dom) if dom else {}
        for k, v in h.items():
            if v:
                setattr(co, k, v)
        db.commit()
        return {"status": "ok", "domain": dom}
    finally:
        db.close()
