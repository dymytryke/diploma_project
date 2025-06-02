from typing import List
from uuid import UUID

from cmp_core.core.db import get_db
from cmp_core.core.deps import get_current_user, require_role
from cmp_core.models.role import RoleName
from cmp_core.schemas.user import UserOut, UserUpdateRole
from cmp_core.services.user import delete_user, get_user, list_users, update_user_role
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/users", tags=["users"])

admin_dep = [require_role(RoleName.admin)]


@router.get(
    "/me",
    response_model=UserOut,
)
async def api_read_users_me(user=Depends(get_current_user)):
    return user


@router.get("", response_model=List[UserOut], dependencies=admin_dep)
async def api_list_users(db: AsyncSession = Depends(get_db)):
    users = await list_users(db)
    return users


@router.get("/{user_id}", response_model=UserOut, dependencies=admin_dep)
async def api_get_user(user_id: UUID, db: AsyncSession = Depends(get_db)):
    return await get_user(db, user_id)


@router.patch(
    "/{user_id}/role",
    response_model=UserOut,
    dependencies=admin_dep,
)
async def api_update_role(
    user_id: UUID,
    data: UserUpdateRole,
    db: AsyncSession = Depends(get_db),
):
    return await update_user_role(db, user_id, data)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=admin_dep,
)
async def api_delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    await delete_user(db, user_id)
