# cmp_core/services/ec2.py

import uuid

from cmp_core.lib.grafana import make_dashboard_url
from cmp_core.models.resource import Provider, Resource, ResourceState, ResourceType
from cmp_core.schemas.ec2 import Ec2Create, Ec2Out, Ec2Update
from cmp_core.tasks.ec2 import start_ec2_task, stop_ec2_task
from cmp_core.tasks.pulumi import reconcile_project
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
    terminating: bool = False,
) -> Ec2Out:
    if new_meta:
        res.meta.update(new_meta)
    res.state = ResourceState.terminating if terminating else ResourceState.pending
    db.add(res)
    await db.commit()
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

    # 1) insert placeholder Resource (state=pending), seed instance_type so front-end won't crash
    resource_id = uuid.uuid4()
    placeholder = Resource(
        id=resource_id,
        project_id=project_id,
        provider=Provider.aws,
        resource_type=ResourceType.vm,
        name=dto.name,
        region=dto.region,
        state=ResourceState.pending,
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
        ami="",
        launch_time="",
        status=ResourceState.pending,
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

    return await _mark_and_reconcile(
        db, res, project_id, new_meta={"instance_type": dto.instance_type}
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

    await _mark_and_reconcile(db, res, project_id, terminating=True)


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

    start_ec2_task.delay(str(res.id), user_id)
    res.state = ResourceState.pending  # or ResourceState.creating
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

    # enqueue the EC2‐stop task (so it just calls Boto3.stop_instances, updates state, etc.)
    stop_ec2_task.delay(str(res.id), user_id)
    # set in-DB state to "stopping" so client sees it immediately
    res.state = ResourceState.pending
    db.add(res)
    await db.commit()
    return _to_ec2out(res)
