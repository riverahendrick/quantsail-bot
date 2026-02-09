"""add event seq cursor

Revision ID: c9e0b3f0f1a2
Revises: b581045cf266
Create Date: 2026-01-27 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9e0b3f0f1a2"
down_revision: Union[str, Sequence[str], None] = "b581045cf266"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add monotonic seq cursor to events."""
    op.execute("CREATE SEQUENCE IF NOT EXISTS events_seq_seq")
    op.add_column("events", sa.Column("seq", sa.BigInteger(), nullable=True))
    op.execute("ALTER TABLE events ALTER COLUMN seq SET DEFAULT nextval('events_seq_seq')")
    op.execute("ALTER SEQUENCE events_seq_seq OWNED BY events.seq")
    op.execute("UPDATE events SET seq = nextval('events_seq_seq') WHERE seq IS NULL")
    op.alter_column("events", "seq", nullable=False)
    op.create_index("uq_events_seq", "events", ["seq"], unique=True)


def downgrade() -> None:
    """Remove seq cursor from events."""
    op.drop_index("uq_events_seq", table_name="events")
    op.drop_column("events", "seq")
    op.execute("DROP SEQUENCE IF EXISTS events_seq_seq")
