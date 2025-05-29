# cmp_core/services/azure_vm.py

import uuid
from typing import Any, Dict  # Added typing for Dict and Any

from cmp_core.lib.grafana import make_dashboard_url
from cmp_core.models.resource import Provider, Resource, ResourceState, ResourceType
from cmp_core.schemas.azure import AzureCreate, AzureOut, AzureUpdate
from cmp_core.tasks.azure import start_azure_task, stop_azure_task
from cmp_core.tasks.pulumi import reconcile_project
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def _to_azure_vm_out(res: Resource) -> AzureOut:
    # Ensure meta is a dictionary
    meta: Dict[str, Any] = res.meta if res.meta is not None else {}

    # Extract Azure-specific details from res.meta for AzureOut fields
    azure_vm_size = meta.get("vm_size")
    azure_public_ip = meta.get("public_ip")
    azure_subscription_id = meta.get("subscription_id")
    azure_resource_group = meta.get("resource_group_name")

    # Get the actual VM name from meta, fallback to logical name if not present
    # This is the key change for the dashboard URL's vmName parameter
    actual_azure_vm_name_for_dashboard = meta.get("actual_vm_name", res.name)

    # Compute dashboard URL
    dashboard_url = make_dashboard_url(
        provider=res.provider.value,
        resource_type=res.resource_type.value,
        region=res.region,
        subscription_id=azure_subscription_id
        or "",  # Grafana lib handles empty strings if needed
        resource_group=azure_resource_group
        or "",  # Grafana lib handles empty strings if needed
        vm_name=actual_azure_vm_name_for_dashboard,  # Use the actual VM name from Azure
    )

    return AzureOut(
        id=str(res.id),
        name=res.name,  # Display name is still the logical name
        region=res.region,
        status=res.state,
        vm_size=azure_vm_size,
        public_ip=azure_public_ip,
        subscription_id=azure_subscription_id,  # For API output
        resource_group=azure_resource_group,  # For API output
        meta=meta,
        dashboard_url=dashboard_url,
    )


async def list_azure(
    db: AsyncSession,
    project_id: str,
) -> list[AzureOut]:
    q = await db.execute(
        select(Resource).where(
            Resource.project_id == project_id,
            Resource.provider == Provider.azure,
            Resource.resource_type == ResourceType.vm,
        )
    )
    items = q.scalars().all()

    out: list[AzureOut] = []
    for (
        r_item
    ) in items:  # Renamed r to r_item to avoid conflict if _to_azure_vm_out used 'r'
        out.append(_to_azure_vm_out(r_item))
    return out


async def get_azure(
    db: AsyncSession,
    project_id: str,
    name: str,
) -> AzureOut:
    q = await db.execute(
        select(Resource).where(
            Resource.project_id == project_id,
            Resource.provider == Provider.azure,
            Resource.resource_type == ResourceType.vm,
            Resource.name == name,
        )
    )
    r_item = q.scalar_one_or_none()  # Renamed r to r_item
    if not r_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    return _to_azure_vm_out(r_item)


async def create_azure_nonblocking(
    db: AsyncSession,
    project_id: str,
    dto: AzureCreate,
    user_id: str,
) -> AzureOut:
    q = await db.execute(
        select(Resource).where(
            Resource.project_id == project_id,
            Resource.name == dto.name,
        )
    )
    if q.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Azure VM '{dto.name}' already exists in project {project_id}",
        )

    res_id = uuid.uuid4()
    initial_meta: Dict[str, Any] = {  # Explicitly type initial_meta
        "location": dto.location
        or "",  # This will be used for AzureOut.region via Resource.region
        "vnet_address_prefix": dto.vnet_address_prefix,
        "subnet_prefix": dto.subnet_prefix,
        "public_ip_allocation_method": dto.public_ip_allocation_method,
        "vm_size": dto.vm_size,
        "image_reference": dto.image_reference if dto.image_reference else {},
        "admin_username": dto.admin_username,
        "admin_password": dto.admin_password,  # Consider security implications
        # azure_vm_id, public_ip, subscription_id, resource_group_name will be populated by reconcile_single
    }
    placeholder = Resource(
        id=res_id,
        project_id=project_id,
        provider=Provider.azure,
        resource_type=ResourceType.vm,
        name=dto.name,
        region=dto.location or "",
        state=ResourceState.PENDING_PROVISION,  # Use new state
        meta=initial_meta,
        created_by=user_id,
    )
    db.add(placeholder)
    await db.commit()
    await db.refresh(placeholder)

    reconcile_project.delay(project_id)

    return _to_azure_vm_out(placeholder)  # _to_azure_vm_out will use placeholder.state


async def update_azure_nonblocking(
    db: AsyncSession,
    project_id: str,
    name: str,
    dto: AzureUpdate,
    user_id: str,
) -> AzureOut:
    q = await db.execute(
        select(Resource).where(
            Resource.project_id == project_id,
            Resource.provider == Provider.azure,
            Resource.resource_type == ResourceType.vm,
            Resource.name == name,
        )
    )
    r_item = q.scalar_one_or_none()  # Renamed r to r_item
    if not r_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    # Add checks: e.g., cannot update if PENDING_DEPROVISION or TERMINATED
    if r_item.state in [
        ResourceState.PENDING_DEPROVISION,
        ResourceState.DEPROVISIONING,
        ResourceState.TERMINATED,
    ]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot update resource in state: {r_item.state.value}",
        )

    updates = dto.model_dump(exclude_unset=True)
    if r_item.meta is None:  # Ensure meta exists
        r_item.meta = {}

    if "vm_size" in updates and updates["vm_size"] is not None:
        r_item.meta["vm_size"] = updates["vm_size"]
    if "admin_password" in updates and updates["admin_password"] is not None:
        r_item.meta["admin_password"] = updates["admin_password"]  # Consider security

    r_item.state = ResourceState.PENDING_UPDATE  # Use new state
    db.add(r_item)
    await db.commit()
    await db.refresh(r_item)  # Refresh to get any DB-side changes before converting
    reconcile_project.delay(project_id)

    return _to_azure_vm_out(r_item)  # Use the corrected helper function


async def delete_azure_nonblocking(
    db: AsyncSession,
    project_id: str,
    name: str,
    user_id: str,
):
    q = await db.execute(
        select(Resource).where(
            Resource.project_id == project_id,
            Resource.provider == Provider.azure,
            Resource.resource_type == ResourceType.vm,
            Resource.name == name,
        )
    )
    r_item = q.scalar_one_or_none()  # Renamed r to r_item
    if not r_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    # Add checks similar to EC2 delete
    if r_item.state in [
        ResourceState.PENDING_DEPROVISION,
        ResourceState.DEPROVISIONING,
        ResourceState.TERMINATED,
    ]:
        if r_item.state == ResourceState.DEPROVISIONING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Resource is already being deprovisioned.",
            )
        if r_item.state == ResourceState.TERMINATED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Resource is already terminated.",
            )

    r_item.state = ResourceState.PENDING_DEPROVISION  # Use new state
    db.add(r_item)
    await db.commit()
    reconcile_project.delay(project_id)
    # No return value, so no AzureOut conversion needed here


async def start_azure_nonblocking(
    db: AsyncSession,
    project_id: str,
    name: str,
    user_id: str,
) -> AzureOut:
    q = await db.execute(
        select(Resource).where(
            Resource.project_id == project_id,
            Resource.provider == Provider.azure,
            Resource.resource_type == ResourceType.vm,
            Resource.name == name,
        )
    )
    r_item = q.scalar_one_or_none()  # Renamed r to r_item
    if not r_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    # Add checks: Can only start if STOPPED or perhaps ERROR_STARTING
    if r_item.state not in [
        ResourceState.STOPPED,
        ResourceState.ERROR_STARTING,
        ResourceState.ERROR,
    ]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot start resource in state: {r_item.state.value}. Must be STOPPED or an error state related to starting.",
        )

    # The current Azure start task updates meta['power_state'] but not the main Resource.state
    # We should set the main state here to PENDING_START
    r_item.state = ResourceState.PENDING_START  # Use new state
    if r_item.meta is None:
        r_item.meta = {}
    # The task itself will handle the 'STARTING' and then 'RUNNING' or 'ERROR_STARTING'
    # No need to set meta['power_state'] = "starting" here, let the task do it.
    db.add(r_item)
    await db.commit()
    await db.refresh(r_item)
    start_azure_task.delay(str(r_item.id), user_id)

    return _to_azure_vm_out(r_item)  # Use the corrected helper function


async def stop_azure_nonblocking(
    db: AsyncSession,
    project_id: str,
    name: str,
    user_id: str,
) -> AzureOut:
    q = await db.execute(
        select(Resource).where(
            Resource.project_id == project_id,
            Resource.provider == Provider.azure,
            Resource.resource_type == ResourceType.vm,
            Resource.name == name,
        )
    )
    r_item = q.scalar_one_or_none()  # Renamed r to r_item
    if not r_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    # Add checks: Can only stop if RUNNING or perhaps ERROR_STOPPING
    if r_item.state not in [
        ResourceState.RUNNING,
        ResourceState.ERROR_STOPPING,
        ResourceState.ERROR,
    ]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot stop resource in state: {r_item.state.value}. Must be RUNNING or an error state related to stopping.",
        )

    r_item.state = ResourceState.PENDING_STOP  # Use new state
    if r_item.meta is None:
        r_item.meta = {}
    # No need to set meta['power_state'] = "stopping" here, let the task do it.
    db.add(r_item)
    await db.commit()
    await db.refresh(r_item)
    stop_azure_task.delay(str(r_item.id), user_id)

    return _to_azure_vm_out(r_item)  # Use the corrected helper function
