"""Admin-only routes: audit log review, suppression list management."""
import json
from datetime import datetime
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, require_role
from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.suppression import SuppressionEntry, SuppressionSource
from app.models.user import UserRole
from app.services import audit

router = APIRouter(prefix="/api/admin", tags=["admin"])


# --- Schemas ---


class AuditLogOut(BaseModel):
    """Frontend-facing audit log row. `actor_id` aliases `actor_user_id`."""
    id: int
    event_type: str
    actor_id: Optional[int] = Field(None, validation_alias="actor_user_id")
    actor_email: Optional[str]
    actor_ip: Optional[str]
    actor_user_agent: Optional[str]
    target_type: Optional[str]
    target_id: Optional[str]
    detail: Optional[dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("detail", mode="before")
    @classmethod
    def _parse_detail(cls, v: Any) -> Any:
        # detail is stored as Text JSON; lift it back to a dict for the API
        if v is None or isinstance(v, dict):
            return v
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, dict) else {"value": parsed}
            except (json.JSONDecodeError, ValueError):
                return {"raw": v}
        return None


class AuditLogPage(BaseModel):
    items: list[AuditLogOut]
    total: int
    limit: int
    offset: int


class SuppressionCreate(BaseModel):
    company_number: Optional[str] = None
    email: Optional[EmailStr] = None
    domain: Optional[str] = None
    source: SuppressionSource = SuppressionSource.MANUAL
    lawful_basis: Optional[str] = None
    reason: Optional[str] = None
    request_received_at: Optional[datetime] = None


class SuppressionOut(BaseModel):
    id: int
    company_number: Optional[str]
    email: Optional[str]
    domain: Optional[str]
    source: str
    lawful_basis: Optional[str]
    reason: Optional[str]
    added_by: Optional[str]
    request_received_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SuppressionPage(BaseModel):
    items: list[SuppressionOut]
    total: int
    limit: int
    offset: int


# --- Audit log ---


@router.get(
    "/audit-log",
    response_model=AuditLogPage,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def list_audit_log(
    db: Annotated[Session, Depends(get_db)],
    event_type: Optional[str] = None,
    actor_email: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    base = select(AuditLog)
    if event_type:
        # Partial-match on event_type is more useful than exact-match for an audit UI.
        base = base.where(AuditLog.event_type.ilike(f"%{event_type}%"))
    if actor_email:
        base = base.where(AuditLog.actor_email == actor_email.lower())

    total = db.execute(
        select(func.count()).select_from(base.subquery())
    ).scalar_one()

    items = db.execute(
        base.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    ).scalars().all()

    return AuditLogPage(
        items=[AuditLogOut.model_validate(r) for r in items],
        total=total,
        limit=limit,
        offset=offset,
    )


# --- Suppression list ---


@router.get(
    "/suppression",
    response_model=SuppressionPage,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.MANAGER))],
)
def list_suppression(
    db: Annotated[Session, Depends(get_db)],
    source: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    base = select(SuppressionEntry)
    if source:
        base = base.where(SuppressionEntry.source == source)

    total = db.execute(
        select(func.count()).select_from(base.subquery())
    ).scalar_one()

    items = db.execute(
        base.order_by(SuppressionEntry.created_at.desc()).limit(limit).offset(offset)
    ).scalars().all()

    return SuppressionPage(
        items=[SuppressionOut.model_validate(r) for r in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/suppression",
    response_model=SuppressionOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.MANAGER))],
)
def add_suppression(
    payload: SuppressionCreate,
    user: CurrentUser,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    if not any([payload.company_number, payload.email, payload.domain]):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Must provide at least one of: company_number, email, domain",
        )
    entry = SuppressionEntry(
        company_number=payload.company_number,
        email=str(payload.email) if payload.email else None,
        domain=payload.domain,
        source=payload.source.value,
        lawful_basis=payload.lawful_basis,
        reason=payload.reason,
        request_received_at=payload.request_received_at,
        added_by=user.email,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    audit.record(
        db,
        "suppression.added",
        actor=user,
        target_type="suppression",
        target_id=entry.id,
        detail=payload.model_dump(mode="json"),
    )
    return entry


@router.delete(
    "/suppression/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
def remove_suppression(
    entry_id: int,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    entry = db.get(SuppressionEntry, entry_id)
    if not entry:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Entry not found")
    snapshot = {
        "company_number": entry.company_number,
        "email": entry.email,
        "domain": entry.domain,
        "source": entry.source,
    }
    db.delete(entry)
    db.commit()
    audit.record(
        db,
        "suppression.removed",
        actor=user,
        target_type="suppression",
        target_id=entry_id,
        detail=snapshot,
    )
    return None


# --- Analytics ---


class AnalyticsResponse(BaseModel):
    """Aggregated counts for the admin analytics page."""
    leads_by_status: dict[str, int]
    leads_by_urgency: dict[str, int]
    alerts_by_channel: dict[str, dict[str, int]]
    """Channel → {sent, failed, pending} counts."""
    audit_events_30d: list[dict[str, Any]]
    """[{ event_type, count }] for the last 30 days."""
    risk_distribution: dict[str, int]
    """risk_level → count of companies."""
    pipeline_value_gbp: float
    """Sum of estimated_value_gbp for leads in active (non-terminal) statuses."""


@router.get(
    "/analytics",
    response_model=AnalyticsResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.MANAGER))],
)
def analytics(db: Annotated[Session, Depends(get_db)]):
    """
    Snapshot stats for the admin analytics dashboard. Cheap to compute —
    no joins beyond the trivial. If volumes grow past ~100k rows, swap
    these to a materialised view refreshed every few minutes.
    """
    from datetime import timedelta
    from app.models.alert import Alert
    from app.models.compliance import Compliance
    from app.models.lead import Lead

    # Leads by status
    rows = db.execute(
        select(Lead.status, func.count(Lead.id)).group_by(Lead.status)
    ).all()
    leads_by_status = {s: c for s, c in rows}

    # Leads by urgency
    rows = db.execute(
        select(Lead.urgency, func.count(Lead.id)).group_by(Lead.urgency)
    ).all()
    leads_by_urgency = {u: c for u, c in rows}

    # Alerts by channel + status
    rows = db.execute(
        select(
            Alert.alert_channel,
            Alert.sent_status,
            func.count(Alert.id),
        ).group_by(Alert.alert_channel, Alert.sent_status)
    ).all()
    alerts_by_channel: dict[str, dict[str, int]] = {}
    for channel, sent_status, count in rows:
        alerts_by_channel.setdefault(channel, {})[sent_status] = count

    # Audit events (30-day, top 20 by frequency)
    cutoff = datetime.utcnow() - timedelta(days=30)
    rows = db.execute(
        select(AuditLog.event_type, func.count(AuditLog.id))
        .where(AuditLog.created_at >= cutoff)
        .group_by(AuditLog.event_type)
        .order_by(func.count(AuditLog.id).desc())
        .limit(20)
    ).all()
    audit_events_30d = [{"event_type": e, "count": c} for e, c in rows]

    # Risk distribution
    rows = db.execute(
        select(Compliance.risk_level, func.count(Compliance.id))
        .group_by(Compliance.risk_level)
    ).all()
    risk_distribution = {(r or "unknown"): c for r, c in rows}

    # Pipeline value (active statuses only)
    active = ("new", "qualified", "contacted", "in_progress")
    pipeline_value = db.execute(
        select(func.coalesce(func.sum(Lead.estimated_value_gbp), 0.0))
        .where(Lead.status.in_(active))
    ).scalar_one()

    return AnalyticsResponse(
        leads_by_status=leads_by_status,
        leads_by_urgency=leads_by_urgency,
        alerts_by_channel=alerts_by_channel,
        audit_events_30d=audit_events_30d,
        risk_distribution=risk_distribution,
        pipeline_value_gbp=float(pipeline_value or 0.0),
    )
