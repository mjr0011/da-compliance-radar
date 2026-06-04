"""Alerts API — list dispatched alerts."""
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from sqlalchemy.orm import Session
from app.core.deps import CurrentUser
from app.database import get_db
from app.models.alert import Alert
from app.schemas.entities import AlertOut

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
def list_alerts(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    channel: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=500),
):
    stmt = select(Alert).order_by(Alert.created_at.desc()).limit(limit)
    if channel:
        stmt = stmt.where(Alert.alert_channel == channel)
    if status_filter:
        stmt = stmt.where(Alert.sent_status == status_filter)
    return db.execute(stmt).scalars().all()
