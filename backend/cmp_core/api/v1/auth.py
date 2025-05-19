# app/api/v1/auth.py

from cmp_core.core.db import get_db
from cmp_core.core.security import create_access_token, create_refresh_token
from cmp_core.schemas.auth import Token, UserCreate
from cmp_core.services.auth import (
    authenticate_user,
    create_user,
    get_user_by_email,
    save_refresh_token,
)
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["auth"], prefix="/auth")


@router.post("/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
async def signup(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await get_user_by_email(db, user_in.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User already registered"
        )
    user = await create_user(db, user_in)
    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)
    await save_refresh_token(db, user.id, refresh)
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}


@router.post("/token", response_model=Token)
async def login_for_access(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)
    await save_refresh_token(db, user.id, refresh)
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}
