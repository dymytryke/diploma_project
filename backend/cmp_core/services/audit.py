# cmp_core/services/audit.py

from typing import List, Optional, Tuple

from cmp_core.models.audit import AuditEvent
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def list_audit_events(
    db: AsyncSession,
    project_id: Optional[str] = None,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[AuditEvent], int]:
    q = select(AuditEvent)
    if project_id is not None:
        q = q.where(AuditEvent.project_id == project_id)
    if user_id is not None:
        q = q.where(AuditEvent.user_id == user_id)
    if action is not None:
        q = q.where(AuditEvent.action == action)

    # Get total count before applying pagination
    count_q = select(func.count()).select_from(q.subquery())
    total_count_result = await db.execute(count_q)
    total = total_count_result.scalar_one_or_none() or 0

    # Get paginated items
    items_q = (
        q.order_by(AuditEvent.timestamp.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(items_q)
    items = result.scalars().all()
    return items, total
