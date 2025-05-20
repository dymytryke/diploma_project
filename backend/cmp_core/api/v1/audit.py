from typing import List, Optional

from cmp_core.core.db import get_db
from cmp_core.core.deps import require_role
from cmp_core.models.audit import AuditEvent
from cmp_core.models.role import RoleName
from cmp_core.schemas.audit import AuditEventOut
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["audit"])


@router.get(
    "/audit", response_model=List[AuditEventOut], summary="Fetch audit events (JSON)"
)
async def api_audit(
    project: Optional[str] = Query(None),
    user: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _=require_role(RoleName.admin),  # only admins
):
    q = select(AuditEvent)
    if project:
        q = q.where(AuditEvent.project_id == project)
    if user:
        q = q.where(AuditEvent.user_id == user)
    if action:
        q = q.where(AuditEvent.action == action)
    q = q.order_by(AuditEvent.timestamp.desc())
    events = (await db.execute(q)).scalars().all()
    return events
