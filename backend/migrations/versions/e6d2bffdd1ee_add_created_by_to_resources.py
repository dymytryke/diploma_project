"""add created_by to resources

Revision ID: e6d2bffdd1ee
Revises: f1fbb32df71b
Create Date: 2025-05-23 09:11:55.331491

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e6d2bffdd1ee"
down_revision: Union[str, None] = "f1fbb32df71b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "resources",
        sa.Column(
            "created_by",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    pass


def downgrade() -> None:
    op.drop_column("resources", "created_by")
    pass
