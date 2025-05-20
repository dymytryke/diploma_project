from uuid import UUID

from cmp_core.core.db import get_db
from cmp_core.core.deps import require_role
from cmp_core.models.role import RoleName
from cmp_core.schemas.member import (
    ProjectMemberCreate,
    ProjectMemberOut,
    ProjectMemberUpdate,
)
from cmp_core.services.member import (
    add_member,
    list_members,
    remove_member,
    update_member,
)
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/projects/{project_id}/members", tags=["members"])
admin_only = [require_role(RoleName.admin)]


@router.get("", response_model=list[ProjectMemberOut], dependencies=admin_only)
async def api_list_members(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    return await list_members(db, project_id)


@router.post(
    "",
    response_model=ProjectMemberOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=admin_only,
)
async def api_add_member(
    project_id: UUID,
    data: ProjectMemberCreate,
    db: AsyncSession = Depends(get_db),
):
    return await add_member(db, project_id, data)


@router.patch(
    "/{user_id}",
    response_model=ProjectMemberOut,
    dependencies=admin_only,
)
async def api_update_member(
    project_id: UUID,
    user_id: UUID,
    data: ProjectMemberUpdate,
    db: AsyncSession = Depends(get_db),
):
    return await update_member(db, project_id, user_id, data)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=admin_only,
)
async def api_remove_member(
    project_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    await remove_member(db, project_id, user_id)
