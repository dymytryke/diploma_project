# cmp_core/schemas/audit.py

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class AuditEventOut(BaseModel):
    id: UUID
    user_id: UUID
    project_id: Optional[UUID]
    action: str
    object_type: str
    object_id: str
    timestamp: datetime
    details: dict

    class Config:
        from_attributes = True


class AuditEventPage(BaseModel):
    items: List[AuditEventOut]
    total: int
    page: int
    size: int
    pages: int

    class Config:
        from_attributes = True
