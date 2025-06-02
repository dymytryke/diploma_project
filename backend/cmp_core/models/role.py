import enum

from sqlalchemy import Column, Enum

from .base import Base


class RoleName(str, enum.Enum):
    admin = "admin"
    devops = "devops"
    viewer = "viewer"


class Role(Base):
    id = Column(Enum(RoleName), primary_key=True)
