# cmp_core/api/v1/azure.py

from typing import List

from cmp_core.core.db import get_db
from cmp_core.core.deps import require_project_member
from cmp_core.models.role import RoleName
from cmp_core.schemas.azure import AzureCreate, AzureOut, AzureUpdate
from cmp_core.services.azure_vm import (
    create_azure_nonblocking,
    delete_azure_nonblocking,
    get_azure,
    list_azure,
    start_azure_nonblocking,
    stop_azure_nonblocking,
    update_azure_nonblocking,
)
from fastapi import APIRouter, Body, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/resources/azure/vm",
    tags=["azure"],
)


@router.post(
    "/{project_id}",
    response_model=AzureOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def api_create_azure(
    project_id: str = Path(..., description="ID of the project"),
    dto: AzureCreate = Body(..., description="Azure VM parameters"),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_project_member(RoleName.devops)),
):
    return await create_azure_nonblocking(db, project_id, dto, str(user.id))


@router.get(
    "/{project_id}",
    response_model=List[AzureOut],
)
async def api_list_azure(
    project_id: str = Path(..., description="ID of the project"),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_project_member()),
):
    return await list_azure(db, project_id)


@router.get(
    "/{project_id}/{name}",
    response_model=AzureOut,
)
async def api_get_azure(
    project_id: str = Path(..., description="ID of the project"),
    name: str = Path(..., description="Name of the VM"),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_project_member()),
):
    return await get_azure(db, project_id, name)


@router.patch(
    "/{project_id}/{name}",
    response_model=AzureOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def api_update_azure(
    project_id: str = Path(...),
    name: str = Path(...),
    dto: AzureUpdate = Body(...),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_project_member(RoleName.devops)),
):
    return await update_azure_nonblocking(db, project_id, name, dto, str(user.id))


@router.delete(
    "/{project_id}/{name}",
    status_code=status.HTTP_202_ACCEPTED,
)
async def api_delete_azure(
    project_id: str = Path(...),
    name: str = Path(...),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_project_member(RoleName.devops)),
):
    await delete_azure_nonblocking(db, project_id, name, str(user.id))
    return None


@router.post(
    "/{project_id}/{name}/start",
    response_model=AzureOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def api_start_azure(
    project_id: str = Path(..., description="ID of the project"),
    name: str = Path(..., description="Name of the VM"),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_project_member(RoleName.devops)),
):
    """
    Start an Azure VM (non-blocking).
    """
    return await start_azure_nonblocking(db, project_id, name, str(user.id))


@router.post(
    "/{project_id}/{name}/stop",
    response_model=AzureOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def api_stop_azure(
    project_id: str = Path(..., description="ID of the project"),
    name: str = Path(..., description="Name of the VM"),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_project_member(RoleName.devops)),
):
    """
    Stop an Azure VM (non-blocking).
    """
    return await stop_azure_nonblocking(db, project_id, name, str(user.id))
