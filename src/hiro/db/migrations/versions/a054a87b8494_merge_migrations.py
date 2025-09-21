"""merge migrations

Revision ID: a054a87b8494
Revises: 00837ac53bc2, 52ab4279ea02
Create Date: 2025-09-20 18:03:30.878042

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "a054a87b8494"
down_revision: str | Sequence[str] | None = ("00837ac53bc2", "52ab4279ea02")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
