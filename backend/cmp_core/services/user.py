from typing import List
from uuid import UUID

from cmp_core.models.role import RoleName
from cmp_core.models.user import User
from cmp_core.schemas.user import UserUpdateRole
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def list_users(db: AsyncSession) -> List[User]:
    result = await db.execute(select(User))
    return result.scalars().all()


async def get_user(db: AsyncSession, user_id: UUID) -> User:
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


async def update_user_role(
    db: AsyncSession, user_id: UUID, data: UserUpdateRole
) -> User:
    user = await get_user(db, user_id)
    try:
        RoleName(data.role_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role_id",
        )
    user.role_id = data.role_id
    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(db: AsyncSession, user_id: UUID) -> None:
    user = await get_user(db, user_id)
    await db.delete(user)
    await db.commit()
