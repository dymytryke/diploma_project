"""add project_id to audit_events

Revision ID: 74ae5cb9a0bf
Revises: 883cf21d27ee
Create Date: 2025-05-20 15:12:34.025431

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "74ae5cb9a0bf"
down_revision: Union[str, None] = "883cf21d27ee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        "audit_events",
        sa.Column("project_id", postgresql.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_audit_events_project_id",
        "audit_events",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint("fk_audit_events_project_id", "audit_events", type_="foreignkey")
    op.drop_column("audit_events", "project_id")
