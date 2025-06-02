from cmp_core.models.mixins import IdMixin, TimestampMixin
from sqlalchemy import Column, DateTime, ForeignKey, String

from .base import Base


class RefreshToken(IdMixin, TimestampMixin, Base):
    __tablename__ = "refresh_tokens"
    user_id = Column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    # created_at з TimestampMixin
