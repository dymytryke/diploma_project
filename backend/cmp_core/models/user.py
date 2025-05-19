from sqlalchemy import Column, Enum, ForeignKey, String
from sqlalchemy.orm import relationship

from .base import Base
from .mixins import IdMixin, TimestampMixin
from .role import RoleName


class User(IdMixin, TimestampMixin, Base):
    email = Column(String(320), unique=True, index=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    role_id = Column(
        Enum(RoleName),
        ForeignKey("roles.id", ondelete="SET NULL"),
        nullable=False,
        server_default=RoleName.viewer.value,
    )
    role = relationship("Role", lazy="joined")
