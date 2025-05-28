# cmp_core/services/azure_vm.py

import uuid

from cmp_core.lib.grafana import make_dashboard_url
from cmp_core.models.resource import Provider, Resource, ResourceState, ResourceType
from cmp_core.schemas.azure import AzureCreate, AzureOut, AzureUpdate
from cmp_core.tasks.azure import start_azure_task, stop_azure_task
from cmp_core.tasks.pulumi import reconcile_project
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def _to_azure_vm_out(res: Resource) -> AzureOut:
    # Extract Azure-specific details from res.meta
    # Adjust these .get() calls if your meta keys are different
    subscription_id = res.meta.get("subscription_id", "")
    resource_group = res.meta.get("resource_group_name", "")  # Or "resource_group"
    public_ip = res.meta.get("public_ip", "")

    return AzureOut(
        azure_vm_id=res.meta.get("azure_vm_id", ""),
        name=res.name,
        public_ip=public_ip,
        power_state=res.meta.get("power_state", ""),
        location=res.meta.get("location", ""),
        meta=res.meta,
        dashboard_url=make_dashboard_url(
            provider=res.provider.value,  # "azure"
            resource_type=res.resource_type.value,  # "vm"
            region=res.region,
            subscription_id=subscription_id,
            resource_group=resource_group,
            vm_name=res.name,  # res.name is the Azure VM name
        ),
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
    for r in items:
        out.append(_to_azure_vm_out(r))
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
    r = q.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    return _to_azure_vm_out(r)


async def create_azure_nonblocking(
    db: AsyncSession,
    project_id: str,
    dto: AzureCreate,
    user_id: str,
) -> AzureOut:
    # уникаємо дублювання імені
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

    # створюємо placeholder із станом pending
    res_id = uuid.uuid4()
    initial_meta = {
        "location": dto.location or "",
        "vnet_address_prefix": dto.vnet_address_prefix,
        "subnet_prefix": dto.subnet_prefix,
        "public_ip_allocation_method": dto.public_ip_allocation_method,
        "vm_size": dto.vm_size,
        "image_reference": (
            dto.image_reference if dto.image_reference else {}
        ),  # Use the dict directly
        "admin_username": dto.admin_username,
        "admin_password": dto.admin_password,
        "power_state": ResourceState.pending.value,  # Explicitly set initial power_state in meta
        # azure_vm_id will be populated by reconcile_single later
        # public_ip will be populated by reconcile_single later
    }
    placeholder = Resource(
        id=res_id,
        project_id=project_id,
        provider=Provider.azure,
        resource_type=ResourceType.vm,
        name=dto.name,
        region=dto.location
        or "",  # Azure uses 'location', but your Resource model has 'region'
        state=ResourceState.pending,
        meta=initial_meta,
        created_by=user_id,
    )
    db.add(placeholder)
    await db.commit()
    await db.refresh(
        placeholder
    )  # Ensure the placeholder object has the committed data, especially meta

    # штовхаємо фоновий Pulumi-таск
    reconcile_project.delay(project_id)

    # повертаємо початковий обʼєкт
    return AzureOut(
        azure_vm_id="",  # Not known yet
        name=placeholder.name,
        public_ip="",  # Not known yet
        power_state=placeholder.meta.get(
            "power_state", ResourceState.pending.value
        ),  # Read from meta
        location=placeholder.meta.get("location", ""),
        meta=placeholder.meta,
    )


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
    r = q.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    updates = dto.model_dump(exclude_unset=True)
    if "vm_size" in updates:
        r.meta["vm_size"] = updates["vm_size"]
    if "admin_password" in updates:
        r.meta["admin_password"] = updates["admin_password"]

    r.state = ResourceState.pending
    db.add(r)
    await db.commit()
    reconcile_project.delay(project_id)

    return AzureOut(
        azure_vm_id=r.meta.get("azure_vm_id", ""),
        name=r.name,
        public_ip=r.meta.get("public_ip", ""),
        power_state=r.meta.get("power_state", ""),
        location=r.meta.get("location", ""),
        meta=r.meta,
    )


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
    r = q.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    r.state = ResourceState.terminating
    db.add(r)
    await db.commit()
    reconcile_project.delay(project_id)


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
    r = q.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    r.state = (
        ResourceState.pending
    )  # Or ResourceState.running if you want to be optimistic
    if r.meta is None:  # Ensure meta dictionary exists
        r.meta = {}
    r.meta["power_state"] = "starting"  # Set intermediate state in meta
    db.add(r)
    await db.commit()
    await db.refresh(
        r
    )  # Refresh to get the updated meta if it's a JSONB type managed by SQLAlchemy
    start_azure_task.delay(str(r.id), user_id)

    return AzureOut(
        azure_vm_id=r.meta.get("azure_vm_id", ""),
        name=r.name,
        public_ip=r.meta.get("public_ip", ""),
        power_state=r.meta.get("power_state", ""),  # This will now be "starting"
        location=r.meta.get("location", ""),
        meta=r.meta,
    )


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
    r = q.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    r.state = ResourceState.pending  # Or ResourceState.stopped
    if r.meta is None:  # Ensure meta dictionary exists
        r.meta = {}
    r.meta["power_state"] = "stopping"  # Set intermediate state in meta
    db.add(r)
    await db.commit()
    await db.refresh(r)  # Refresh to get the updated meta
    stop_azure_task.delay(str(r.id), user_id)

    return AzureOut(
        azure_vm_id=r.meta.get("azure_vm_id", ""),
        name=r.name,
        public_ip=r.meta.get("public_ip", ""),
        power_state=r.meta.get("power_state", ""),  # This will now be "stopping"
        location=r.meta.get("location", ""),
        meta=r.meta,
    )
