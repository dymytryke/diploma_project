from sqlalchemy import Column, String

from .base import Base
from .mixins import IdMixin, TimestampMixin


class User(IdMixin, TimestampMixin, Base):
    email = Column(String(320), unique=True, index=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
