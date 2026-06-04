"""
Audit log helpers.

The pattern is: pass in a session + an actor + an event description,
get a persisted row with no fuss. Never let an audit failure break the
underlying operation — log and continue.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User

logger = logging.getLogger(__name__)


def record(
    db: Session,
    event_type: str,
    *,
    actor: Optional[User] = None,
    actor_email: Optional[str] = None,
    actor_ip: Optional[str] = None,
    actor_user_agent: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str | int] = None,
    detail: Optional[dict[str, Any]] = None,
    commit: bool = True,
) -> Optional[AuditLog]:
    """
    Persist an audit log row.

    `commit=False` lets you bundle the audit row with the calling
    transaction so they roll back together. Default is True because
    most call sites want fire-and-forget logging.
    """
    try:
        row = AuditLog(
            actor_user_id=actor.id if actor else None,
            actor_email=actor.email if actor else actor_email,
            actor_ip=actor_ip,
            actor_user_agent=(actor_user_agent or "")[:512] or None,
            event_type=event_type,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            detail=json.dumps(detail, default=str) if detail else None,
        )
        db.add(row)
        if commit:
            db.commit()
            db.refresh(row)
        return row
    except Exception:
        logger.exception("Audit logging failed for %s", event_type)
        if commit:
            db.rollback()
        return None
