from typing import List
from uuid import UUID

from cmp_core.models.project import Project
from cmp_core.models.project_member import ProjectMember
from cmp_core.models.resource import Resource
from cmp_core.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate
from cmp_core.tasks.pulumi import destroy_project_task
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def list_projects(db: AsyncSession, user_id: UUID) -> List[Project]:
    # projects you own or are a member of
    stmt = select(Project).where(
        (Project.owner_id == user_id)
        | (
            Project.id.in_(
                select(ProjectMember.project_id).where(ProjectMember.user_id == user_id)
            )
        )
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def list_projects_with_count(db: AsyncSession, user_id: UUID) -> list[ProjectOut]:
    projects = await list_projects(db, user_id)

    results: list[ProjectOut] = []
    for proj in projects:
        count = await db.execute(
            select(func.count())
            .select_from(Resource)
            .where(Resource.project_id == proj.id)
        )
        total = count.scalar_one()
        dto = ProjectOut.from_orm(proj)
        dto.resources_total = total
        results.append(dto)

    return results


async def create_project(
    db: AsyncSession, user_id: UUID, data: ProjectCreate
) -> Project:
    proj = Project(name=data.name, owner_id=user_id)
    db.add(proj)
    await db.commit()
    # add creator as member with devops role
    pm = ProjectMember(user_id=user_id, project_id=proj.id, role_id="devops")
    db.add(pm)
    await db.commit()
    await db.refresh(proj)
    return proj


async def get_project_or_404(
    db: AsyncSession, project_id: UUID, user_id: UUID
) -> Project:
    stmt = (
        select(Project)
        .join(ProjectMember)
        .where(Project.id == project_id)
        .where(ProjectMember.user_id == user_id)
    )
    result = await db.execute(stmt)
    proj = result.scalars().first()
    if not proj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return proj


async def update_project(
    db: AsyncSession, project_id: UUID, user_id: UUID, data: ProjectUpdate
) -> Project:
    proj = await get_project_or_404(db, project_id, user_id)
    proj.name = data.name
    await db.commit()
    await db.refresh(proj)
    return proj


async def delete_project(db: AsyncSession, project_id: UUID, user_id: UUID):
    proj = await get_project_or_404(db, project_id, user_id)
    await db.delete(proj)

    # asynchronously destroy all infra for that project
    destroy_project_task.delay(str(project_id))
    await db.commit()
