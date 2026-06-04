"""Company, compliance, lead, alert response schemas."""
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


# --- Compliance ---

class ComplianceOut(BaseModel):
    accounts_due_date: Optional[date]
    accounts_overdue: bool
    confirmation_due_date: Optional[date]
    confirmation_overdue: bool
    strike_off_warning: bool
    in_insolvency: bool
    next_deadline: Optional[date]
    days_until_next_deadline: Optional[int]
    risk_level: str

    model_config = ConfigDict(from_attributes=True)


# --- Company ---

class CompanyBase(BaseModel):
    company_number: str
    company_name: str
    status: Optional[str] = None
    sic_code: Optional[str] = None
    sic_description: Optional[str] = None
    incorporation_date: Optional[date] = None
    locality: Optional[str] = None
    postal_code: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    primary_email: Optional[str] = None
    lead_score: int
    risk_score: int


class CompanyOut(CompanyBase):
    id: int
    created_at: datetime
    updated_at: datetime
    compliance: Optional[ComplianceOut] = None

    model_config = ConfigDict(from_attributes=True)


class CompanyListResponse(BaseModel):
    items: List[CompanyOut]
    total: int
    limit: int
    offset: int


# --- Lead ---

class LeadOut(BaseModel):
    id: int
    company_id: int
    source: str
    lead_type: str
    summary: Optional[str]
    ai_category: Optional[str]
    urgency: str
    estimated_value_gbp: Optional[float]
    lead_score: int
    status: str
    assigned_to_id: Optional[int]
    crm_provider: Optional[str]
    crm_external_id: Optional[str]
    crm_synced_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    company: Optional[CompanyBase] = None

    model_config = ConfigDict(from_attributes=True)


class LeadListResponse(BaseModel):
    items: List[LeadOut]
    total: int
    limit: int
    offset: int


class LeadUpdate(BaseModel):
    status: Optional[str] = None
    assigned_to_id: Optional[int] = None
    notes: Optional[str] = None


# --- Alert ---

class AlertOut(BaseModel):
    id: int
    lead_id: Optional[int]
    alert_channel: str
    alert_type: str
    sent_status: str
    sent_at: Optional[datetime]
    error_message: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Dashboard ---

class DashboardStats(BaseModel):
    total_companies_tracked: int
    overdue_accounts_count: int
    overdue_confirmation_count: int
    strike_off_warnings: int
    high_risk_companies: int
    new_leads_7d: int
    high_value_leads: int
    alerts_sent_24h: int


class SectorBreakdown(BaseModel):
    sic_description: str
    count: int
    avg_lead_score: float


class DashboardResponse(BaseModel):
    stats: DashboardStats
    top_sectors: List[SectorBreakdown]
