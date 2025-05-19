from typing import List
from uuid import UUID

from cmp_core.core.db import get_db
from cmp_core.core.deps import get_current_user, require_role
from cmp_core.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate
from cmp_core.services.project import (
    create_project,
    delete_project,
    list_projects_with_count,
    update_project,
)
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=List[ProjectOut])
async def read_projects(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_projects_with_count(db, user.id)


@router.post(
    "",
    response_model=ProjectOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_role("devops")],
)
async def create_new_project(
    data: ProjectCreate,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_project(db, user.id, data)


@router.patch(
    "/{project_id}",
    response_model=ProjectOut,
    dependencies=[require_role("devops")],
)
async def rename_project(
    project_id: UUID,
    data: ProjectUpdate,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await update_project(db, project_id, user.id, data)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[require_role("devops")],
)
async def remove_project(
    project_id: UUID,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await delete_project(db, project_id, user.id)
