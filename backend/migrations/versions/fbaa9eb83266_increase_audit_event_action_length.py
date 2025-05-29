"""increase_audit_event_action_length

Revision ID: fbaa9eb83266
Revises: 7db9c2a697c1
Create Date: 2025-05-29 15:40:44.017098

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fbaa9eb83266"
down_revision: Union[str, None] = "7db9c2a697c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "audit_events",
        "action",
        existing_type=sa.VARCHAR(length=32),  # Current length in DB
        type_=sa.VARCHAR(length=64),  # New length from model
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "audit_events",
        "action",
        existing_type=sa.VARCHAR(length=64),  # New length
        type_=sa.VARCHAR(length=32),  # Old length
        existing_nullable=False,
    )
