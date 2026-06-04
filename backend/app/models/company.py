"""
Company model — mirrors the spec's Companies table.

One row per UK company tracked. Populated from Companies House profile
endpoint and enriched via Google Places, Hunter, etc.
"""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Companies House identity
    company_number: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    company_name: Mapped[str] = mapped_column(String(255), index=True)
    status: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    company_type: Mapped[Optional[str]] = mapped_column(String(64))

    # Classification
    sic_code: Mapped[Optional[str]] = mapped_column(String(16), index=True)
    sic_description: Mapped[Optional[str]] = mapped_column(String(255))

    # Dates
    incorporation_date: Mapped[Optional[date]] = mapped_column(Date)

    # Location
    address_line_1: Mapped[Optional[str]] = mapped_column(String(255))
    address_line_2: Mapped[Optional[str]] = mapped_column(String(255))
    locality: Mapped[Optional[str]] = mapped_column(String(120), index=True)
    region: Mapped[Optional[str]] = mapped_column(String(120))
    postal_code: Mapped[Optional[str]] = mapped_column(String(16), index=True)
    country: Mapped[Optional[str]] = mapped_column(String(64))

    # Enrichment
    website: Mapped[Optional[str]] = mapped_column(String(512))
    phone: Mapped[Optional[str]] = mapped_column(String(64))
    primary_email: Mapped[Optional[str]] = mapped_column(String(255))
    google_rating: Mapped[Optional[float]] = mapped_column(Float)
    google_reviews_count: Mapped[Optional[int]] = mapped_column(Integer)

    # Scoring
    lead_score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    risk_score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    score_breakdown: Mapped[Optional[str]] = mapped_column(Text)  # JSON string

    # Source tracking
    last_fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    compliance = relationship(
        "Compliance", back_populates="company", uselist=False, cascade="all, delete-orphan"
    )
    leads = relationship("Lead", back_populates="company", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Company {self.company_number} {self.company_name!r}>"
