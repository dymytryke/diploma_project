# app/services/auth.py

import uuid
from datetime import datetime
from typing import Optional

from cmp_core.core.security import decode_token, hash_password, verify_password
from cmp_core.models.refresh_token import RefreshToken
from cmp_core.models.user import User
from cmp_core.schemas.auth import UserCreate
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    q = select(User).where(User.email == email)
    result = await db.execute(q)
    return result.scalars().first()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
    q = select(User).where(User.id == user_id)
    result = await db.execute(q)
    return result.scalars().first()


async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
    user = User(email=user_in.email, password_hash=hash_password(user_in.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(
    db: AsyncSession, email: str, password: str
) -> Optional[User]:
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


async def save_refresh_token(
    db: AsyncSession, user_id: uuid.UUID, token: str
) -> RefreshToken:
    # Визначаємо експайр з payload
    payload = decode_token(token)
    expires_at = datetime.fromtimestamp(payload["exp"])
    rt = RefreshToken(user_id=user_id, token=token, expires_at=expires_at)
    db.add(rt)
    await db.commit()
    return rt


async def revoke_refresh_token(db: AsyncSession, token: str) -> None:
    stmt = delete(RefreshToken).where(RefreshToken.token == token)
    await db.execute(stmt)
    await db.commit()
