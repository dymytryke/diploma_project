# cmp_core/services/audit.py

from typing import List, Optional

from cmp_core.models.audit import AuditEvent
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def list_audit_events(
    db: AsyncSession,
    project_id: Optional[str] = None,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
) -> List[AuditEvent]:
    q = select(AuditEvent)
    if project_id is not None:
        q = q.where(AuditEvent.project_id == project_id)
    if user_id is not None:
        q = q.where(AuditEvent.user_id == user_id)
    if action is not None:
        q = q.where(AuditEvent.action == action)
    q = q.order_by(AuditEvent.timestamp.desc())
    result = await db.execute(q)
    return result.scalars().all()
