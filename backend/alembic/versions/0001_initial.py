"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2025-01-01 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("role", sa.String(32), nullable=False, server_default="viewer"),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # companies
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("company_number", sa.String(16), nullable=False, unique=True),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(64)),
        sa.Column("company_type", sa.String(64)),
        sa.Column("sic_code", sa.String(16)),
        sa.Column("sic_description", sa.String(255)),
        sa.Column("incorporation_date", sa.Date),
        sa.Column("address_line_1", sa.String(255)),
        sa.Column("address_line_2", sa.String(255)),
        sa.Column("locality", sa.String(120)),
        sa.Column("region", sa.String(120)),
        sa.Column("postal_code", sa.String(16)),
        sa.Column("country", sa.String(64)),
        sa.Column("website", sa.String(512)),
        sa.Column("phone", sa.String(64)),
        sa.Column("primary_email", sa.String(255)),
        sa.Column("google_rating", sa.Float),
        sa.Column("google_reviews_count", sa.Integer),
        sa.Column("lead_score", sa.Integer, nullable=False, server_default="0"),
        sa.Column("risk_score", sa.Integer, nullable=False, server_default="0"),
        sa.Column("score_breakdown", sa.Text),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_companies_company_number", "companies", ["company_number"], unique=True)
    op.create_index("ix_companies_company_name", "companies", ["company_name"])
    op.create_index("ix_companies_status", "companies", ["status"])
    op.create_index("ix_companies_sic_code", "companies", ["sic_code"])
    op.create_index("ix_companies_locality", "companies", ["locality"])
    op.create_index("ix_companies_postal_code", "companies", ["postal_code"])
    op.create_index("ix_companies_lead_score", "companies", ["lead_score"])
    op.create_index("ix_companies_risk_score", "companies", ["risk_score"])

    # compliance
    op.create_table(
        "compliance",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "company_id",
            sa.Integer,
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("accounts_due_date", sa.Date),
        sa.Column("accounts_last_made_up_to", sa.Date),
        sa.Column("accounts_overdue", sa.Boolean, server_default=sa.false()),
        sa.Column("confirmation_due_date", sa.Date),
        sa.Column("confirmation_last_made_up_to", sa.Date),
        sa.Column("confirmation_overdue", sa.Boolean, server_default=sa.false()),
        sa.Column("strike_off_warning", sa.Boolean, server_default=sa.false()),
        sa.Column("in_insolvency", sa.Boolean, server_default=sa.false()),
        sa.Column("has_charges", sa.Boolean, server_default=sa.false()),
        sa.Column("last_filing_date", sa.Date),
        sa.Column("filings_count_12mo", sa.Integer, server_default="0"),
        sa.Column("officer_changes_12mo", sa.Integer, server_default="0"),
        sa.Column("next_deadline", sa.Date),
        sa.Column("days_until_next_deadline", sa.Integer),
        sa.Column("risk_level", sa.String(16), server_default="low"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_compliance_company_id", "compliance", ["company_id"], unique=True)
    op.create_index("ix_compliance_accounts_due_date", "compliance", ["accounts_due_date"])
    op.create_index("ix_compliance_accounts_overdue", "compliance", ["accounts_overdue"])
    op.create_index("ix_compliance_confirmation_due_date", "compliance", ["confirmation_due_date"])
    op.create_index("ix_compliance_confirmation_overdue", "compliance", ["confirmation_overdue"])
    op.create_index("ix_compliance_strike_off_warning", "compliance", ["strike_off_warning"])
    op.create_index("ix_compliance_next_deadline", "compliance", ["next_deadline"])
    op.create_index("ix_compliance_risk_level", "compliance", ["risk_level"])

    # leads
    op.create_table(
        "leads",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "company_id",
            sa.Integer,
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("lead_type", sa.String(64), nullable=False),
        sa.Column("summary", sa.Text),
        sa.Column("ai_category", sa.String(64)),
        sa.Column("urgency", sa.String(16), server_default="medium"),
        sa.Column("estimated_value_gbp", sa.Float),
        sa.Column("lead_score", sa.Integer, server_default="0"),
        sa.Column(
            "assigned_to_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("status", sa.String(32), server_default="new"),
        sa.Column("notes", sa.Text),
        sa.Column("crm_provider", sa.String(32)),
        sa.Column("crm_external_id", sa.String(128)),
        sa.Column("crm_synced_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_leads_company_id", "leads", ["company_id"])
    op.create_index("ix_leads_source", "leads", ["source"])
    op.create_index("ix_leads_lead_type", "leads", ["lead_type"])
    op.create_index("ix_leads_urgency", "leads", ["urgency"])
    op.create_index("ix_leads_lead_score", "leads", ["lead_score"])
    op.create_index("ix_leads_status", "leads", ["status"])

    # alerts
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "lead_id",
            sa.Integer,
            sa.ForeignKey("leads.id", ondelete="CASCADE"),
        ),
        sa.Column("alert_channel", sa.String(16), nullable=False),
        sa.Column("alert_type", sa.String(64), nullable=False),
        sa.Column("payload", sa.Text),
        sa.Column("sent_status", sa.String(16), server_default="pending"),
        sa.Column("error_message", sa.Text),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_alerts_lead_id", "alerts", ["lead_id"])
    op.create_index("ix_alerts_alert_channel", "alerts", ["alert_channel"])
    op.create_index("ix_alerts_sent_status", "alerts", ["sent_status"])

    # suppression
    op.create_table(
        "suppression",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("company_number", sa.String(16), unique=True),
        sa.Column("email", sa.String(255), unique=True),
        sa.Column("domain", sa.String(255), unique=True),
        sa.Column("reason", sa.Text),
        sa.Column("added_by", sa.String(120)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_suppression_company_number", "suppression", ["company_number"], unique=True)
    op.create_index("ix_suppression_email", "suppression", ["email"], unique=True)
    op.create_index("ix_suppression_domain", "suppression", ["domain"], unique=True)


def downgrade() -> None:
    op.drop_table("suppression")
    op.drop_table("alerts")
    op.drop_table("leads")
    op.drop_table("compliance")
    op.drop_table("companies")
    op.drop_table("users")
