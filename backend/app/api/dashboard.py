"""Dashboard aggregations — counts, sector breakdowns."""
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser
from app.database import get_db
from app.models.alert import Alert, AlertStatus
from app.models.company import Company
from app.models.compliance import Compliance, RiskLevel
from app.models.lead import Lead
from app.schemas.entities import DashboardResponse, DashboardStats, SectorBreakdown

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
def dashboard(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
):
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)
    one_day_ago = now - timedelta(days=1)

    total_companies = db.scalar(select(func.count(Company.id))) or 0
    overdue_accounts = (
        db.scalar(
            select(func.count(Compliance.id)).where(Compliance.accounts_overdue.is_(True))
        )
        or 0
    )
    overdue_confirm = (
        db.scalar(
            select(func.count(Compliance.id)).where(
                Compliance.confirmation_overdue.is_(True)
            )
        )
        or 0
    )
    strike_off = (
        db.scalar(
            select(func.count(Compliance.id)).where(Compliance.strike_off_warning.is_(True))
        )
        or 0
    )
    high_risk = (
        db.scalar(
            select(func.count(Compliance.id)).where(
                Compliance.risk_level.in_([RiskLevel.HIGH.value, RiskLevel.CRITICAL.value])
            )
        )
        or 0
    )
    new_leads = (
        db.scalar(select(func.count(Lead.id)).where(Lead.created_at >= seven_days_ago)) or 0
    )
    high_value = db.scalar(select(func.count(Lead.id)).where(Lead.lead_score >= 70)) or 0
    alerts_24h = (
        db.scalar(
            select(func.count(Alert.id)).where(
                Alert.created_at >= one_day_ago,
                Alert.sent_status == AlertStatus.SENT.value,
            )
        )
        or 0
    )

    sector_rows = db.execute(
        select(
            func.coalesce(Company.sic_description, Company.sic_code, "Unclassified"),
            func.count(Company.id),
            func.avg(Company.lead_score),
        )
        .group_by(Company.sic_description, Company.sic_code)
        .order_by(desc(func.count(Company.id)))
        .limit(6)
    ).all()

    top_sectors = [
        SectorBreakdown(
            sic_description=row[0] or "Unclassified",
            count=row[1],
            avg_lead_score=round(float(row[2] or 0), 1),
        )
        for row in sector_rows
    ]

    return DashboardResponse(
        stats=DashboardStats(
            total_companies_tracked=total_companies,
            overdue_accounts_count=overdue_accounts,
            overdue_confirmation_count=overdue_confirm,
            strike_off_warnings=strike_off,
            high_risk_companies=high_risk,
            new_leads_7d=new_leads,
            high_value_leads=high_value,
            alerts_sent_24h=alerts_24h,
        ),
        top_sectors=top_sectors,
    )
