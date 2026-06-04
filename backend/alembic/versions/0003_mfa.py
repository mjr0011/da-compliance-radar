"""mfa

Revision ID: 0003_mfa
Revises: 0002_hardening
Create Date: 2026-05-19 09:00:00

Adds TOTP MFA support to the users table.

- mfa_enabled: bool — false until the user completes enrollment
- mfa_secret:  string — base32 TOTP secret (RFC 4226)
- mfa_backup_codes: text — newline-separated bcrypt hashes of one-time
  recovery codes (10 by default; see app.core.mfa)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_mfa"
down_revision: Union[str, None] = "0002_hardening"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "mfa_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column("users", sa.Column("mfa_secret", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("mfa_backup_codes", sa.Text(), nullable=True))

    # Drop the server_default once existing rows are backfilled —
    # new rows are populated by ORM defaults, no need for a DB default.
    op.alter_column("users", "mfa_enabled", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "mfa_backup_codes")
    op.drop_column("users", "mfa_secret")
    op.drop_column("users", "mfa_enabled")
