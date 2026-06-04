"""Companies API — list, filter, single fetch, manual refresh trigger."""
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import CurrentUser
from app.database import get_db
from app.models.company import Company
from app.models.compliance import Compliance
from app.schemas.entities import CompanyListResponse, CompanyOut

router = APIRouter(prefix="/api/companies", tags=["companies"])


def _apply_filters(stmt, q, sic_prefix, locality, min_lead_score, min_risk_score, overdue_only):
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                Company.company_name.ilike(like),
                Company.company_number.ilike(like),
            )
        )
    if sic_prefix:
        stmt = stmt.where(Company.sic_code.like(f"{sic_prefix}%"))
    if locality:
        stmt = stmt.where(Company.locality.ilike(f"%{locality}%"))
    if min_lead_score:
        stmt = stmt.where(Company.lead_score >= min_lead_score)
    if min_risk_score:
        stmt = stmt.where(Company.risk_score >= min_risk_score)
    if overdue_only:
        stmt = stmt.join(Compliance, Compliance.company_id == Company.id).where(
            or_(
                Compliance.accounts_overdue.is_(True),
                Compliance.confirmation_overdue.is_(True),
            )
        )
    return stmt


@router.get("", response_model=CompanyListResponse)
def list_companies(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    q: Optional[str] = Query(None, description="Search name or company number"),
    sic_prefix: Optional[str] = Query(None, description="SIC code prefix, e.g. '43'"),
    locality: Optional[str] = None,
    min_lead_score: int = Query(0, ge=0, le=100),
    min_risk_score: int = Query(0, ge=0, le=100),
    overdue_only: bool = False,
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    base_stmt = select(Company)
    base_stmt = _apply_filters(
        base_stmt, q, sic_prefix, locality, min_lead_score, min_risk_score, overdue_only
    )

    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = db.scalar(count_stmt) or 0

    rows = db.execute(
        base_stmt.options(joinedload(Company.compliance))
        .order_by(Company.lead_score.desc(), Company.updated_at.desc())
        .limit(limit)
        .offset(offset)
    ).unique().scalars().all()

    return CompanyListResponse(
        items=[CompanyOut.model_validate(c) for c in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{company_number}", response_model=CompanyOut)
def get_company(
    company_number: str,
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
):
    co = (
        db.query(Company)
        .options(joinedload(Company.compliance))
        .filter(Company.company_number == company_number.upper())
        .first()
    )
    if not co:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")
    return co


@router.post("/{company_number}/refresh", status_code=status.HTTP_202_ACCEPTED)
def refresh_company(
    company_number: str,
    user: CurrentUser,
):
    """Queue a background refresh of a single company from Companies House."""
    from app.workers.tasks import fetch_and_store_company

    fetch_and_store_company.delay(company_number.upper())
    return {"queued": True, "company_number": company_number.upper()}
