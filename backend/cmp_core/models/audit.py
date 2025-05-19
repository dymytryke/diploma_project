from sqlalchemy import JSON, Column, DateTime, ForeignKey, String, func

from .base import Base
from .mixins import IdMixin


class AuditEvent(IdMixin, Base):
    __tablename__ = "audit_events"
    user_id = Column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action = Column(String(32), nullable=False)
    object_type = Column(String(32), nullable=False)
    object_id = Column(String, nullable=False)
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    details = Column(JSON, default=dict)
