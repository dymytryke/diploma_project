# cmp_core/core/deps.py

from cmp_core.core.db import get_db
from cmp_core.core.security import decode_token
from cmp_core.models.project_member import ProjectMember
from cmp_core.models.role import RoleName
from cmp_core.services.auth import get_user_by_id
from fastapi import Depends, HTTPException, Path, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def require_role(role: RoleName):
    def checker(user=Depends(get_current_user)):
        if user.role.id != role and user.role.id != RoleName.admin:
            raise HTTPException(status_code=403, detail="Forbidden")
        return user

    return Depends(checker)


def require_project_member(min_role: RoleName | None = None):
    async def checker(
        user=Depends(get_current_user),
        project_id: str = Path(..., description="ID проєкту"),
        db: AsyncSession = Depends(get_db),
    ):
        # перевіряємо, чи є юзер учасником проєкту
        q = await db.execute(
            select(ProjectMember).where(
                ProjectMember.user_id == user.id,
                ProjectMember.project_id == project_id,
            )
        )
        pm = q.scalar_one_or_none()
        if pm is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a project member",
            )

        # якщо потрібен мінімальний рівень ролі — перевіряємо його
        if (
            min_role is not None
            and pm.role_id != min_role
            and user.role.id != RoleName.admin
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient privileges",
            )

        return user

    return checker
