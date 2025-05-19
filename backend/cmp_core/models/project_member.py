from sqlalchemy import Column, ForeignKey, PrimaryKeyConstraint

from .base import Base


class ProjectMember(Base):
    __tablename__ = "project_members"
    user_id = Column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id = Column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_id = Column(ForeignKey("roles.id"), nullable=False)
    __table_args__ = (PrimaryKeyConstraint("user_id", "project_id"),)
