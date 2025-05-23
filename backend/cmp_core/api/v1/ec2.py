# cmp_core/api/v1/ec2.py

from typing import List

from cmp_core.core.db import get_db
from cmp_core.core.deps import require_project_member
from cmp_core.models.role import RoleName
from cmp_core.schemas.ec2 import Ec2Create, Ec2Out, Ec2Update
from cmp_core.services.ec2 import (
    create_ec2_nonblocking,
    delete_ec2_nonblocking,
    get_ec2,
    list_ec2,
    start_ec2_nonblocking,
    stop_ec2_nonblocking,
    update_ec2_nonblocking,
)
from fastapi import APIRouter, Body, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/resources/aws/ec2",
    tags=["ec2"],
)


@router.post(
    "/{project_id}",
    response_model=Ec2Out,
    status_code=status.HTTP_202_ACCEPTED,  # 202 is more semantically correct
)
async def api_create_ec2(
    project_id: str = Path(..., description="ID of the project"),
    dto: Ec2Create = Body(..., description="EC2 parameters"),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_project_member(RoleName.devops)),
):
    return await create_ec2_nonblocking(db, project_id, dto, str(user.id))


@router.get(
    "/{project_id}",
    response_model=List[Ec2Out],
)
async def api_list_ec2(
    project_id: str = Path(..., description="ID проєкту"),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_project_member()),
):
    """
    Повертає всі EC2 для цього проєкту. Достатньо бути членом проєкту.
    """
    return await list_ec2(db, project_id)


@router.get(
    "/{project_id}/{name}",
    response_model=Ec2Out,
)
async def api_get_ec2(
    project_id: str = Path(..., description="ID проєкту"),
    name: str = Path(..., description="Name EC2 інстансу"),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_project_member()),
):
    """
    Детальна інформація по EC2 інстансу. Достатньо бути членом проєкту.
    """
    return await get_ec2(db, project_id, name)


@router.patch(
    "/{project_id}/{name}",
    response_model=Ec2Out,
    status_code=status.HTTP_202_ACCEPTED,
)
async def api_update_ec2_nonblocking(
    project_id: str = Path(..., description="Проєкт ID"),
    name: str = Path(..., description="EC2 name"),
    dto: Ec2Update = Body(..., description="New instance_type"),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_project_member(RoleName.devops)),
):
    return await update_ec2_nonblocking(db, project_id, dto, name, str(user.id))


@router.delete(
    "/{project_id}/{name}",
    status_code=status.HTTP_202_ACCEPTED,
)
async def api_delete_ec2(
    project_id: str = Path(...),
    name: str = Path(...),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_project_member(RoleName.devops)),
):
    """
    Mark EC2 for deletion and dispatch background task.
    """
    await delete_ec2_nonblocking(db, project_id, name, str(user.id))
    # 202 Accepted → client can poll for final 'terminated' state
    return None


@router.post(
    "/{project_id}/{name}/start",
    response_model=Ec2Out,
    status_code=status.HTTP_202_ACCEPTED,
)
async def api_start_ec2(
    project_id: str = Path(..., description="Project ID"),
    name: str = Path(..., description="EC2 name"),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_project_member(RoleName.devops)),
):
    return await start_ec2_nonblocking(db, project_id, name, str(user.id))


@router.post(
    "/{project_id}/{name}/stop",
    response_model=Ec2Out,
    status_code=status.HTTP_202_ACCEPTED,
)
async def api_stop_ec2(
    project_id: str = Path(..., description="Project ID"),
    name: str = Path(..., description="EC2 name"),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_project_member(RoleName.devops)),
):
    return await stop_ec2_nonblocking(db, project_id, name, str(user.id))
