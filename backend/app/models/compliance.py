"""Compliance record — one per company, tracking filing deadlines and risk."""
from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Compliance(Base):
    __tablename__ = "compliance"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), unique=True, index=True
    )

    # Accounts
    accounts_due_date: Mapped[Optional[date]] = mapped_column(Date, index=True)
    accounts_last_made_up_to: Mapped[Optional[date]] = mapped_column(Date)
    accounts_overdue: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Confirmation statement
    confirmation_due_date: Mapped[Optional[date]] = mapped_column(Date, index=True)
    confirmation_last_made_up_to: Mapped[Optional[date]] = mapped_column(Date)
    confirmation_overdue: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Risk indicators
    strike_off_warning: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    in_insolvency: Mapped[bool] = mapped_column(Boolean, default=False)
    has_charges: Mapped[bool] = mapped_column(Boolean, default=False)

    # Filing activity
    last_filing_date: Mapped[Optional[date]] = mapped_column(Date)
    filings_count_12mo: Mapped[int] = mapped_column(Integer, default=0)
    officer_changes_12mo: Mapped[int] = mapped_column(Integer, default=0)

    # Computed
    next_deadline: Mapped[Optional[date]] = mapped_column(Date, index=True)
    days_until_next_deadline: Mapped[Optional[int]] = mapped_column(Integer)
    risk_level: Mapped[str] = mapped_column(
        String(16), default=RiskLevel.LOW.value, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    company = relationship("Company", back_populates="compliance")

    def __repr__(self) -> str:
        return f"<Compliance company_id={self.company_id} risk={self.risk_level}>"
