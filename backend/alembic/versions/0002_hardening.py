"""auth hardening + gdpr + streaming

Revision ID: 0002_hardening
Revises: 0001_initial
Create Date: 2025-01-02 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_hardening"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # audit_log
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "actor_user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("actor_email", sa.String(255)),
        sa.Column("actor_ip", sa.String(64)),
        sa.Column("actor_user_agent", sa.String(512)),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("target_type", sa.String(64)),
        sa.Column("target_id", sa.String(64)),
        sa.Column("detail", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_log_actor_user_id", "audit_log", ["actor_user_id"])
    op.create_index("ix_audit_log_actor_email", "audit_log", ["actor_email"])
    op.create_index("ix_audit_log_event_type", "audit_log", ["event_type"])
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])

    # stream_state
    op.create_table(
        "stream_state",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("key", sa.String(64), nullable=False, unique=True),
        sa.Column("timepoint", sa.BigInteger, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_stream_state_key", "stream_state", ["key"], unique=True)

    # suppression — add GDPR-relevant columns
    op.add_column(
        "suppression",
        sa.Column("source", sa.String(32), server_default="manual", nullable=False),
    )
    op.add_column("suppression", sa.Column("lawful_basis", sa.String(64)))
    op.add_column(
        "suppression",
        sa.Column("request_received_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_suppression_source", "suppression", ["source"])


def downgrade() -> None:
    op.drop_index("ix_suppression_source", "suppression")
    op.drop_column("suppression", "request_received_at")
    op.drop_column("suppression", "lawful_basis")
    op.drop_column("suppression", "source")

    op.drop_index("ix_stream_state_key", "stream_state")
    op.drop_table("stream_state")

    op.drop_index("ix_audit_log_created_at", "audit_log")
    op.drop_index("ix_audit_log_event_type", "audit_log")
    op.drop_index("ix_audit_log_actor_email", "audit_log")
    op.drop_index("ix_audit_log_actor_user_id", "audit_log")
    op.drop_table("audit_log")
