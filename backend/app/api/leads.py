"""Leads API — list, filter, update status, manual CRM sync."""
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import CurrentUser, require_role
from app.database import get_db
from app.models.lead import Lead
from app.models.user import UserRole
from app.schemas.entities import LeadListResponse, LeadOut, LeadUpdate

router = APIRouter(prefix="/api/leads", tags=["leads"])


@router.get("", response_model=LeadListResponse)
def list_leads(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    status_filter: Optional[str] = Query(None, alias="status"),
    urgency: Optional[str] = None,
    lead_type: Optional[str] = None,
    min_score: int = Query(0, ge=0, le=100),
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    stmt = select(Lead)
    if status_filter:
        stmt = stmt.where(Lead.status == status_filter)
    if urgency:
        stmt = stmt.where(Lead.urgency == urgency)
    if lead_type:
        stmt = stmt.where(Lead.lead_type == lead_type)
    if min_score:
        stmt = stmt.where(Lead.lead_score >= min_score)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    rows = db.execute(
        stmt.options(joinedload(Lead.company))
        .order_by(Lead.lead_score.desc(), Lead.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).unique().scalars().all()

    return LeadListResponse(
        items=[LeadOut.model_validate(l) for l in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(
    lead_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
):
    lead = (
        db.query(Lead).options(joinedload(Lead.company)).filter(Lead.id == lead_id).first()
    )
    if not lead:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lead not found")
    return lead


@router.patch("/{lead_id}", response_model=LeadOut)
def update_lead(
    lead_id: int,
    payload: LeadUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[object, Depends(require_role(UserRole.ADMIN, UserRole.MANAGER))],
):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lead not found")
    if payload.status is not None:
        lead.status = payload.status
    if payload.assigned_to_id is not None:
        lead.assigned_to_id = payload.assigned_to_id
    if payload.notes is not None:
        lead.notes = payload.notes
    db.commit()
    db.refresh(lead)
    return lead


@router.post("/{lead_id}/sync-crm", status_code=status.HTTP_202_ACCEPTED)
def sync_crm(
    lead_id: int,
    user: Annotated[object, Depends(require_role(UserRole.ADMIN, UserRole.MANAGER))],
):
    from app.workers.tasks import push_lead_to_crm

    push_lead_to_crm.delay(lead_id)
    return {"queued": True, "lead_id": lead_id}


@router.post("/{lead_id}/alert", status_code=status.HTTP_202_ACCEPTED)
def fire_alert(
    lead_id: int,
    user: CurrentUser,
):
    from app.workers.tasks import dispatch_alert_for_lead

    dispatch_alert_for_lead.delay(lead_id)
    return {"queued": True, "lead_id": lead_id}
