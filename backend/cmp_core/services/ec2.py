# cmp_core/services/ec2.py

import uuid

from cmp_core.lib.grafana import make_dashboard_url
from cmp_core.models.resource import Provider, Resource, ResourceState, ResourceType
from cmp_core.schemas.ec2 import Ec2Create, Ec2Out, Ec2Update

# Ensure new task names if we rename them, for now assume they are generic enough
# or we create new ones like provision_task, deprovision_task etc.
# For start/stop, the existing task names (start_ec2_task, stop_ec2_task) are fine.
# For create/update/delete, these currently go via reconcile_project.
from cmp_core.tasks.ec2 import start_ec2_task, stop_ec2_task
from cmp_core.tasks.pulumi import (  # This handles create, update, delete via Pulumi
    reconcile_project,
)
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def list_ec2(db: AsyncSession, project_id: str) -> list[Ec2Out]:
    q = await db.execute(
        select(Resource).where(
            Resource.project_id == project_id,
            Resource.provider == Provider.aws,
            Resource.resource_type == ResourceType.vm,
        )
    )
    items = q.scalars().all()

    out: list[Ec2Out] = []
    for res in items:
        out.append(
            Ec2Out(
                aws_id=res.meta.get("aws_id", ""),
                name=res.name,
                region=res.region,
                instance_type=res.meta.get("instance_type", ""),
                public_ip=res.meta.get("public_ip", ""),
                ami=res.meta.get("ami", ""),
                launch_time=res.meta.get("launch_time", ""),
                status=res.state,
                dashboard_url=make_dashboard_url(
                    provider=res.provider.value,
                    resource_type=res.resource_type.value,
                    region=res.region,
                    instance_id=res.meta.get("aws_id", ""),
                ),
            )
        )
    return out


async def get_ec2(db: AsyncSession, project_id: str, name: str) -> Ec2Out:
    q = await db.execute(
        select(Resource).where(
            Resource.project_id == project_id,
            Resource.provider == Provider.aws,
            Resource.resource_type == ResourceType.vm,
            Resource.name == name,
        )
    )
    res = q.scalar_one_or_none()
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    return Ec2Out(
        aws_id=res.meta.get("aws_id", ""),
        name=res.name,
        region=res.region,
        instance_type=res.meta.get("instance_type", ""),
        public_ip=res.meta.get("public_ip", ""),
        ami=res.meta.get("ami", ""),
        launch_time=res.meta.get("launch_time", ""),
        status=res.state,
        dashboard_url=make_dashboard_url(
            provider=res.provider.value,
            resource_type=res.resource_type.value,
            region=res.region,
            instance_id=res.meta.get("aws_id", ""),
        ),
    )


def _to_ec2out(res: Resource) -> Ec2Out:
    return Ec2Out(
        aws_id=res.meta.get("aws_id", ""),
        name=res.name,
        region=res.region,
        instance_type=res.meta.get("instance_type", ""),
        public_ip=res.meta.get("public_ip", ""),
        ami=res.meta.get("ami", ""),
        launch_time=res.meta.get("launch_time", ""),
        status=res.state.value,
        dashboard_url=make_dashboard_url(
            provider=res.provider.value,
            resource_type=res.resource_type.value,
            region=res.region,
            instance_id=res.meta.get("aws_id", ""),
        ),
    )


async def _mark_and_reconcile(
    db: AsyncSession,
    res: Resource,
    project_id: str,
    new_meta: dict | None = None,
    # NEW: Parameter to specify the desired pending state for reconcile
    pending_state: ResourceState = ResourceState.PENDING_UPDATE,
) -> Ec2Out:
    if new_meta:
        res.meta.update(new_meta)
    # Use the specified pending_state
    res.state = pending_state
    db.add(res)
    await db.commit()
    # Reconcile project will pick up resources in PENDING_PROVISION, PENDING_UPDATE, PENDING_DEPROVISION
    reconcile_project.delay(project_id)
    return _to_ec2out(res)


async def create_ec2_nonblocking(
    db: AsyncSession,
    project_id: str,
    dto: Ec2Create,
    user_id: str,
) -> Ec2Out:
    # 0) pre-flight: no duplicate names in this project
    q = await db.execute(
        select(Resource).where(
            Resource.project_id == project_id,
            Resource.name == dto.name,
        )
    )
    if q.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An EC2 instance named '{dto.name}' already exists in project {project_id}",
        )

    # 1) insert placeholder Resource
    resource_id = uuid.uuid4()
    placeholder = Resource(
        id=resource_id,
        project_id=project_id,
        provider=Provider.aws,
        resource_type=ResourceType.vm,
        name=dto.name,
        region=dto.region,
        state=ResourceState.PENDING_PROVISION,  # Use new state
        meta={"ami": dto.ami, "instance_type": dto.instance_type},
        created_by=user_id,
    )
    db.add(placeholder)
    await db.commit()

    # 2) schedule the background reconcile (which will do a single pulumi up per-project)
    reconcile_project.delay(project_id)

    # 3) return the “pending” placeholder
    return Ec2Out(
        aws_id="",
        name=placeholder.name,
        region=placeholder.region,
        instance_type=dto.instance_type,
        public_ip="",
        ami="",  # Should be dto.ami
        launch_time="",
        status=ResourceState.PENDING_PROVISION,  # Reflect the new state
        dashboard_url=make_dashboard_url(
            provider=placeholder.provider.value,
            resource_type=placeholder.resource_type.value,
            region=placeholder.region,
            instance_id="",  # not known yet
        ),
    )


async def update_ec2_nonblocking(
    db: AsyncSession,
    project_id: str,
    dto: Ec2Update,
    name: str,
    user_id: str,
) -> Ec2Out:
    q = await db.execute(
        select(Resource).where(
            Resource.project_id == project_id,
            Resource.name == name,
            Resource.provider == Provider.aws,
            Resource.resource_type == ResourceType.vm,
        )
    )
    res = q.scalar_one_or_none()
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    # Add checks: e.g., cannot update if PENDING_DEPROVISION or TERMINATED
    if res.state in [
        ResourceState.PENDING_DEPROVISION,
        ResourceState.DEPROVISIONING,
        ResourceState.TERMINATED,
    ]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot update resource in state: {res.state.value}",
        )

    return await _mark_and_reconcile(
        db,
        res,
        project_id,
        new_meta={"instance_type": dto.instance_type},
        pending_state=ResourceState.PENDING_UPDATE,  # Specify pending state
    )


async def delete_ec2_nonblocking(
    db: AsyncSession,
    project_id: str,
    name: str,
    user_id: str,
):
    q = await db.execute(
        select(Resource).where(
            Resource.project_id == project_id,
            Resource.name == name,
        )
    )
    res = q.scalar_one_or_none()
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    # Add checks: e.g., cannot delete if already PENDING_DEPROVISION or TERMINATED
    if res.state in [
        ResourceState.PENDING_DEPROVISION,
        ResourceState.DEPROVISIONING,
        ResourceState.TERMINATED,
    ]:
        # Optionally, just return success if already terminated or pending deprovision
        # For now, let's raise a conflict if actively being deprovisioned.
        if res.state == ResourceState.DEPROVISIONING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Resource is already being deprovisioned.",
            )
        # If already PENDING_DEPROVISION or TERMINATED, could be idempotent, or raise error.
        # For now, let's allow re-triggering PENDING_DEPROVISION if it's in a stable state.
        if res.state == ResourceState.TERMINATED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Resource is already terminated.",
            )

    # _mark_and_reconcile was using ResourceState.terminating directly.
    # We should set it to PENDING_DEPROVISION and let reconcile_project handle it.
    # The `terminating` parameter in _mark_and_reconcile was a bit confusing.
    # Let's adjust _mark_and_reconcile or call directly.
    res.state = ResourceState.PENDING_DEPROVISION
    db.add(res)
    await db.commit()
    reconcile_project.delay(project_id)
    # For delete, typically no body is returned (204 No Content)
    # If you need to return the object, use _to_ec2out(res)


async def start_ec2_nonblocking(
    db: AsyncSession,
    project_id: str,
    name: str,
    user_id: str,
) -> Ec2Out:
    q = await db.execute(
        select(Resource).where(
            Resource.project_id == project_id,
            Resource.name == name,
            Resource.provider == Provider.aws,
            Resource.resource_type == ResourceType.vm,
        )
    )
    res = q.scalar_one_or_none()
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    # Add checks: Can only start if STOPPED or perhaps ERROR_STARTING
    if res.state not in [
        ResourceState.STOPPED,
        ResourceState.ERROR_STARTING,
        ResourceState.ERROR,
    ]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot start resource in state: {res.state.value}. Must be STOPPED or an error state related to starting.",
        )

    start_ec2_task.delay(str(res.id), user_id)
    res.state = ResourceState.PENDING_START  # Use new state
    db.add(res)
    await db.commit()
    return _to_ec2out(res)


async def stop_ec2_nonblocking(
    db: AsyncSession,
    project_id: str,
    name: str,
    user_id: str,
) -> Ec2Out:
    q = await db.execute(
        select(Resource).where(
            Resource.project_id == project_id,
            Resource.name == name,
            Resource.provider == Provider.aws,
            Resource.resource_type == ResourceType.vm,
        )
    )
    res = q.scalar_one_or_none()
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    # Add checks: Can only stop if RUNNING or perhaps ERROR_STOPPING
    if res.state not in [
        ResourceState.RUNNING,
        ResourceState.ERROR_STOPPING,
        ResourceState.ERROR,
    ]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot stop resource in state: {res.state.value}. Must be RUNNING or an error state related to stopping.",
        )

    stop_ec2_task.delay(str(res.id), user_id)
    res.state = ResourceState.PENDING_STOP  # Use new state
    db.add(res)
    await db.commit()
    return _to_ec2out(res)
