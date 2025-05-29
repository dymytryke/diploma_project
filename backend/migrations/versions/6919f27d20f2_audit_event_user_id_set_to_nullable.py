"""audit event user id set to nullable

Revision ID: 6919f27d20f2
Revises: fbaa9eb83266
Create Date: 2025-05-29 16:09:31.972972

"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "6919f27d20f2"
down_revision: Union[str, None] = "fbaa9eb83266"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "audit_events",
        "user_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "audit_events",
        "user_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
