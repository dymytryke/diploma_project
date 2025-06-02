"""fix default role to viewer

Revision ID: 883cf21d27ee
Revises: 6ef566463c8e
Create Date: 2025-05-19 16:20:23.976243

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "883cf21d27ee"
down_revision: Union[str, None] = "6ef566463c8e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "role_id",
        existing_type=sa.Enum("admin", "devops", "viewer", name="rolename"),
        server_default="viewer",
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "role_id",
        existing_type=sa.Enum("admin", "devops", "viewer", name="rolename"),
        server_default="devops",
        existing_nullable=False,
    )
