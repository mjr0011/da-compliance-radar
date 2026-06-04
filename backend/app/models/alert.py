"""Alert record — one per dispatched notification."""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AlertChannel(str, Enum):
    SLACK = "slack"
    TELEGRAM = "telegram"
    EMAIL = "email"


class AlertStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    lead_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), index=True
    )

    alert_channel: Mapped[str] = mapped_column(String(16), index=True)
    alert_type: Mapped[str] = mapped_column(String(64))
    # e.g. "high_value_lead", "overdue_accounts", "strike_off", "new_incorp"

    payload: Mapped[Optional[str]] = mapped_column(Text)  # JSON snapshot of message
    sent_status: Mapped[str] = mapped_column(
        String(16), default=AlertStatus.PENDING.value, index=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    lead = relationship("Lead", back_populates="alerts")

    def __repr__(self) -> str:
        return f"<Alert id={self.id} channel={self.alert_channel} status={self.sent_status}>"
