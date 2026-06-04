"""
Audit log — append-only security and workflow events.

Captures everything an auditor would want to reconstruct:
- Logins (success / failure)
- Permission denials
- Lead status changes
- Suppression list mutations
- User creation / deactivation
- CRM sync attempts

Rows are never updated or deleted by application code.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # When + who
    actor_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    actor_email: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    """Captured at the moment of the event in case the user is later deleted."""

    actor_ip: Mapped[Optional[str]] = mapped_column(String(64))
    actor_user_agent: Mapped[Optional[str]] = mapped_column(String(512))

    # What
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    """
    Examples:
      auth.login.success, auth.login.failed, auth.logout,
      auth.token.refresh, auth.role.changed,
      lead.status.changed, lead.crm.synced,
      suppression.added, suppression.removed,
      user.created, user.deactivated
    """

    target_type: Mapped[Optional[str]] = mapped_column(String(64))
    """Resource being acted on (e.g. 'lead', 'user', 'company')."""

    target_id: Mapped[Optional[str]] = mapped_column(String(64))
    """ID as string to accommodate non-int identifiers."""

    # Detail (JSON-serialised; small)
    detail: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.event_type} actor={self.actor_email}>"
