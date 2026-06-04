"""
Suppression list — GDPR / PECR opt-outs and lawful-basis records.

Each row blocks all outreach to the matching identifier. The added
GDPR fields support the firm's accountability obligations under UK
GDPR Article 5(2).
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SuppressionSource(str, Enum):
    """How the suppression was created — feeds compliance reports."""
    USER_OPT_OUT = "user_opt_out"           # individual asked to be removed
    CTPS_MATCH = "ctps_match"               # Corporate TPS suppression
    CLIENT_REQUEST = "client_request"        # existing client doesn't want outreach
    DSR_ERASURE = "dsr_erasure"             # GDPR Article 17 request
    MANUAL = "manual"                       # added by staff


class SuppressionEntry(Base):
    __tablename__ = "suppression"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Match by ANY of these — first non-null wins.
    company_number: Mapped[Optional[str]] = mapped_column(String(16), unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)
    domain: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)

    # Documentation
    reason: Mapped[Optional[str]] = mapped_column(Text)
    source: Mapped[str] = mapped_column(
        String(32), default=SuppressionSource.MANUAL.value, index=True
    )
    added_by: Mapped[Optional[str]] = mapped_column(String(120))

    # GDPR fields
    lawful_basis: Mapped[Optional[str]] = mapped_column(String(64))
    """ICO lawful-basis ref e.g. 'consent', 'legitimate_interest', 'erasure_request'."""

    request_received_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    """When the data subject contacted the firm (for DSR audit trail)."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        ident = self.company_number or self.email or self.domain
        return f"<SuppressionEntry {ident}>"
