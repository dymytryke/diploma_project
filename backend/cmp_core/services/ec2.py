# cmp_core/services/ec2.py

import uuid

from cmp_core.lib.pulumi_ec2 import destroy_instance, up_instance
from cmp_core.models.audit import AuditEvent
from cmp_core.models.resource import Provider, Resource, ResourceState, ResourceType
from cmp_core.schemas.ec2 import Ec2Create, Ec2Out, Ec2Update
from cmp_core.tasks.ec2 import create_ec2_task, delete_ec2_task
from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


async def create_ec2_nonblocking(
    db: AsyncSession,
    project_id: str,
    dto: Ec2Create,
    user_id: str,
) -> Ec2Out:
    """
    1) insert a placeholder Resource (state=pending)
    2) schedule the Celery task to actually provision it
    3) return an Ec2Out with status="pending"
    """
    resource_id = uuid.uuid4()
    placeholder = Resource(
        id=resource_id,
        project_id=project_id,
        provider=Provider.aws,
        resource_type=ResourceType.vm,
        name=dto.name,
        region=dto.region,
        state="pending",
        meta={},
    )
    db.add(placeholder)
    await db.commit()

    # fire‐and‐forget
    create_ec2_task.delay(
        str(resource_id),
        project_id,
        dto.dict(),
        user_id,
    )

    # return a shape matching your Ec2Out schema
    return Ec2Out(
        aws_id="",  # still unknown
        name=placeholder.name,
        region=placeholder.region,
        instance_type=dto.instance_type,
        public_ip="",
        ami="",
        launch_time="",
        status="pending",
    )


async def create_ec2(
    db: AsyncSession,
    project_id: str,
    dto: Ec2Create,
    user_id: str,
) -> Ec2Out:
    # 0) ensure no duplicate name in this project
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

    # 1) run Pulumi
    outputs = up_instance(project_id, dto.dict())

    # 2) persist to resources table
    res = Resource(
        project_id=project_id,
        provider=Provider.aws,
        resource_type=ResourceType.vm,
        name=dto.name,
        region=dto.region,
        state=outputs["status"],
        meta={
            "aws_id": outputs["aws_id"],
            "public_ip": outputs["public_ip"],
            "ami": outputs["ami"],
            "instance_type": outputs["instance_type"],
            # if you still export launch_time, include it here too:
            # "launch_time": outputs["launch_time"],
        },
    )
    db.add(res)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        # catch any race that sneaks past the pre-flight check
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An EC2 instance named '{dto.name}' already exists in project {project_id}",
        )
    await db.refresh(res)

    # 3) audit event
    evt = AuditEvent(
        user_id=user_id,
        action="create_ec2",
        object_type="ec2",
        object_id=res.id.hex,
        details=res.meta,
    )
    db.add(evt)
    await db.commit()

    # 4) return all required fields
    return Ec2Out(
        aws_id=res.meta["aws_id"],
        name=res.name,
        region=res.region,
        instance_type=res.meta["instance_type"],
        public_ip=res.meta["public_ip"],
        ami=res.meta["ami"],
        launch_time=res.meta.get("launch_time", ""),  # or drop if unused
        status=res.state,
    )


async def list_ec2(db: AsyncSession, project_id: str) -> list[Ec2Out]:
    q = await db.execute(
        select(Resource).where(
            Resource.project_id == project_id,
            Resource.provider == Provider.aws,
            Resource.resource_type == ResourceType.vm,
        )
    )
    items = q.scalars().all()
    return [
        Ec2Out(
            aws_id=i.meta["aws_id"],
            name=i.name,
            region=i.region,
            instance_type=i.meta["instance_type"],
            public_ip=i.meta["public_ip"],
            ami=i.meta["ami"],
            launch_time=i.meta.get("launch_time", ""),
            status=i.state,
        )
        for i in items
    ]


async def get_ec2(db: AsyncSession, project_id: str, name: str) -> Ec2Out:
    q = await db.execute(
        select(Resource).where(
            Resource.project_id == project_id,
            Resource.provider == Provider.aws,
            Resource.resource_type == ResourceType.vm,
            Resource.name == name,
        )
    )
    i = q.scalar_one_or_none()
    if not i:
        raise ValueError("Not found")
    return Ec2Out(
        aws_id=i.meta["aws_id"],
        name=i.name,
        region=i.region,
        instance_type=i.meta["instance_type"],
        public_ip=i.meta["public_ip"],
        ami=i.meta["ami"],
        launch_time=i.meta["launch_time"],
        status=i.state,
    )


async def update_ec2(
    db: AsyncSession, project_id: str, dto: Ec2Update, name: str, user_id: str
) -> Ec2Out:
    # load existing resource
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
        raise ValueError("Not found")

    # update its instance_type in metadata
    res.meta["instance_type"] = dto.instance_type
    db.add(res)
    await db.commit()
    await db.refresh(res)

    # audit the resize
    evt = AuditEvent(
        user_id=user_id,
        action="update_ec2",
        object_type="ec2",
        object_id=res.id.hex,
        details={"new_instance_type": dto.instance_type},
    )
    db.add(evt)
    await db.commit()

    return await get_ec2(db, project_id, name)


async def delete_ec2(db: AsyncSession, project_id: str, name: str, user_id: str):
    # fire Pulumi destroy
    destroy_instance(project_id)

    # remove from DB
    await db.execute(
        delete(Resource).where(
            Resource.project_id == project_id,
            Resource.name == name,
            Resource.provider == Provider.aws,
            Resource.resource_type == ResourceType.vm,
        )
    )
    # audit deletion
    evt = AuditEvent(
        user_id=user_id,
        action="delete_ec2",
        object_type="ec2",
        object_id=name,
        details={},
    )
    db.add(evt)
    await db.commit()


async def delete_ec2_nonblocking(
    db: AsyncSession, project_id: str, name: str, user_id: str
):
    # find the resource
    res = await db.scalar(
        select(Resource).where(
            Resource.project_id == project_id,
            Resource.name == name,
        )
    )
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    # mark deleting
    res.state = ResourceState.terminating
    db.add(res)
    await db.commit()

    # dispatch destroy
    delete_ec2_task.delay(str(res.id), user_id, project_id)
