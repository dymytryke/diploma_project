from uuid import UUID

from cmp_core.models.project_member import ProjectMember
from cmp_core.models.user import User
from cmp_core.schemas.member import ProjectMemberCreate, ProjectMemberUpdate
from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession


async def list_members(db: AsyncSession, project_id: UUID) -> list[ProjectMember]:
    res = await db.execute(
        select(ProjectMember).where(ProjectMember.project_id == project_id)
    )
    return res.scalars().all()


async def add_member(
    db: AsyncSession, project_id: UUID, data: ProjectMemberCreate
) -> ProjectMember:
    # перевірити, що користувач існує
    user = await db.get(User, data.user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    # перевірити дублікати
    existing = await db.get(ProjectMember, (data.user_id, project_id))
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Already a member")
    member = ProjectMember(
        user_id=data.user_id, project_id=project_id, role_id=data.role_id
    )
    db.add(member)
    await db.commit()
    return member


async def update_member(
    db: AsyncSession, project_id: UUID, user_id: UUID, data: ProjectMemberUpdate
) -> ProjectMember:
    member = await db.get(ProjectMember, (user_id, project_id))
    if not member:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    member.role_id = data.role_id
    await db.commit()
    await db.refresh(member)
    return member


async def remove_member(db: AsyncSession, project_id: UUID, user_id: UUID) -> None:
    stmt = delete(ProjectMember).where(
        ProjectMember.project_id == project_id, ProjectMember.user_id == user_id
    )
    await db.execute(stmt)
    await db.commit()
