from typing import Optional

from cmp_core.core.db import get_db
from cmp_core.core.deps import require_role
from cmp_core.models.role import RoleName
from cmp_core.schemas.audit import AuditEventPage
from cmp_core.services.audit import list_audit_events
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["audit"])


@router.get(
    "/audit",
    response_model=AuditEventPage,
    summary="Fetch audit events with pagination",
)
async def api_audit(
    project: Optional[str] = Query(None, alias="params[project_id]"),
    user: Optional[str] = Query(None, alias="params[user_id]"),
    action: Optional[str] = Query(None, alias="params[action]"),
    page: int = Query(1, ge=1, alias="params[page]"),
    page_size: int = Query(20, ge=1, le=100, alias="params[size]"),
    db: AsyncSession = Depends(get_db),
    _=require_role(RoleName.admin),
):
    print(
        f"API LOG: Received audit request - project: {project}, user: {user}, action: {action}, page: {page}, size: {page_size}"
    )

    items, total = await list_audit_events(
        db,
        project_id=project,
        user_id=user,
        action=action,
        page=page,
        page_size=page_size,
    )

    num_pages = (total + page_size - 1) // page_size if total > 0 else 0
    # Ensure page is not out of bounds if total is 0 or less than current page after filtering
    if page > num_pages and num_pages > 0:
        current_page_corrected = num_pages
    elif page > num_pages and num_pages == 0:
        current_page_corrected = 1  # Default to page 1 if no results
    else:
        current_page_corrected = page

    return AuditEventPage(
        items=items,
        total=total,
        page=current_page_corrected,  # Use the requested page number
        size=page_size,  # Use the requested page size
        pages=num_pages,
    )
