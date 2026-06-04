"""Lead model — qualified opportunity derived from a company."""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LeadStatus(str, Enum):
    NEW = "new"
    QUALIFIED = "qualified"
    CONTACTED = "contacted"
    IN_PROGRESS = "in_progress"
    WON = "won"
    LOST = "lost"
    REJECTED = "rejected"


class LeadUrgency(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )

    # Source classification
    source: Mapped[str] = mapped_column(String(64), index=True)
    # e.g. "companies_house_overdue", "companies_house_new_incorp",
    # "reddit", "x_twitter", "dataforseo", "manual"

    lead_type: Mapped[str] = mapped_column(String(64), index=True)
    # e.g. "overdue_accounts", "confirmation_statement", "vat_help",
    # "bookkeeping", "payroll", "self_assessment", "cis", "mtd"

    # AI / human summary
    summary: Mapped[Optional[str]] = mapped_column(Text)
    ai_category: Mapped[Optional[str]] = mapped_column(String(64))

    # Sizing
    urgency: Mapped[str] = mapped_column(
        String(16), default=LeadUrgency.MEDIUM.value, index=True
    )
    estimated_value_gbp: Mapped[Optional[float]] = mapped_column(Float)
    lead_score: Mapped[int] = mapped_column(Integer, default=0, index=True)

    # Workflow
    assigned_to_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(
        String(32), default=LeadStatus.NEW.value, index=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # CRM sync
    crm_provider: Mapped[Optional[str]] = mapped_column(String(32))
    crm_external_id: Mapped[Optional[str]] = mapped_column(String(128))
    crm_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    company = relationship("Company", back_populates="leads")
    alerts = relationship("Alert", back_populates="lead", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Lead id={self.id} type={self.lead_type} score={self.lead_score}>"
