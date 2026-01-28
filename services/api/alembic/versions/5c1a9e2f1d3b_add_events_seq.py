"""add events seq column

Revision ID: 5c1a9e2f1d3b
Revises: b581045cf266
Create Date: 2026-01-28 11:25:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op, context


def _column_exists(inspector: sa.Inspector, table: str, column: str) -> bool:
    return any(col["name"] == column for col in inspector.get_columns(table))


def _index_exists(inspector: sa.Inspector, table: str, index: str) -> bool:
    return any(idx["name"] == index for idx in inspector.get_indexes(table))


def _sequence_exists(bind: sa.Connection, sequence: str) -> bool:
    result = bind.execute(sa.text("SELECT to_regclass(:sequence)"), {"sequence": sequence})
    return result.scalar() is not None

revision: str = "5c1a9e2f1d3b"
down_revision: Union[str, Sequence[str], None] = "b581045cf266"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add seq cursor column + unique index for events."""
    # In offline mode, we just emit the DDL without inspection
    if context.is_offline_mode():
        op.add_column("events", sa.Column("seq", sa.BigInteger(), nullable=True))
        op.execute("CREATE SEQUENCE events_seq_seq OWNED BY events.seq")
        op.execute(
            "SELECT setval("
            "  'events_seq_seq',"
            "  COALESCE((SELECT max(seq) FROM events), 1),"
            "  (SELECT max(seq) FROM events) IS NOT NULL"
            ")"
        )
        op.execute("UPDATE events SET seq = nextval('events_seq_seq') WHERE seq IS NULL")
        op.alter_column(
            "events",
            "seq",
            server_default=sa.text("nextval('events_seq_seq')"),
            nullable=False,
        )
        op.create_index("uq_events_seq", "events", ["seq"], unique=True)
        return

    bind = op.get_bind()
    inspector = sa.inspect(bind)

    has_seq_column = _column_exists(inspector, "events", "seq")
    if not has_seq_column:
        op.add_column("events", sa.Column("seq", sa.BigInteger(), nullable=True))
        has_seq_column = True

    if not _sequence_exists(bind, "events_seq_seq"):
        op.execute("CREATE SEQUENCE events_seq_seq OWNED BY events.seq")

    if has_seq_column:
        # Create sequence for monotonic cursor and backfill existing rows.
        op.execute(
            "SELECT setval("
            "  'events_seq_seq',"
            "  COALESCE((SELECT max(seq) FROM events), 1),"
            "  (SELECT max(seq) FROM events) IS NOT NULL"
            ")"
        )
        op.execute("UPDATE events SET seq = nextval('events_seq_seq') WHERE seq IS NULL")

        op.alter_column(
            "events",
            "seq",
            server_default=sa.text("nextval('events_seq_seq')"),
            nullable=False,
        )

        if not _index_exists(inspector, "events", "uq_events_seq"):
            op.create_index("uq_events_seq", "events", ["seq"], unique=True)


def downgrade() -> None:
    """Remove seq column and index."""
    if context.is_offline_mode():
        op.drop_index("uq_events_seq", table_name="events")
        op.drop_column("events", "seq")
        op.execute("DROP SEQUENCE events_seq_seq")
        return

    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _index_exists(inspector, "events", "uq_events_seq"):
        op.drop_index("uq_events_seq", table_name="events")

    if _column_exists(inspector, "events", "seq"):
        op.drop_column("events", "seq")

    if _sequence_exists(bind, "events_seq_seq"):
        op.execute("DROP SEQUENCE events_seq_seq")
