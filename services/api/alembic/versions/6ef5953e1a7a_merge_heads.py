"""merge heads

Revision ID: 6ef5953e1a7a
Revises: 7f3b2a1c9c10, c9e0b3f0f1a2
Create Date: 2026-01-28 14:13:20.192541

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "6ef5953e1a7a"
down_revision: Union[str, Sequence[str], None] = ("7f3b2a1c9c10", "c9e0b3f0f1a2")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
