"""add exchange_keys is_active

Revision ID: 7f3b2a1c9c10
Revises: 5c1a9e2f1d3b
Create Date: 2026-01-28 11:40:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "7f3b2a1c9c10"
down_revision: Union[str, Sequence[str], None] = "5c1a9e2f1d3b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_active column and active-key uniqueness constraint."""
    op.add_column(
        "exchange_keys",
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )

    op.create_index(
        "uq_exchange_keys_active",
        "exchange_keys",
        ["exchange"],
        unique=True,
        postgresql_where=sa.text("is_active AND revoked_at IS NULL"),
    )


def downgrade() -> None:
    """Remove is_active column and constraint."""
    op.drop_index("uq_exchange_keys_active", table_name="exchange_keys")
    op.drop_column("exchange_keys", "is_active")
