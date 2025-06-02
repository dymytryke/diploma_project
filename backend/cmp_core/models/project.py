from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.orm import relationship

from .base import Base
from .mixins import IdMixin, TimestampMixin


class Project(IdMixin, TimestampMixin, Base):
    name = Column(String(64), nullable=False)
    owner_id = Column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    owner = relationship("User", backref="owned_projects")
