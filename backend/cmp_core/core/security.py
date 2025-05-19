# app/core/security.py
from datetime import datetime, timedelta
from typing import Any, Union

from cmp_core.core.config import settings
from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

# 1. Алгоритм хешування пароля
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 2. Назва ключа в токені
TOKEN_SUBJECT = "access"


# 3. Хешування та перевірка пароля
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# 4. Створення токенів
def create_access_token(subject: Union[str, Any]) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode = {"sub": str(subject), "exp": expire, "type": "access"}
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(subject: Union[str, Any]) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    to_encode = {"sub": str(subject), "exp": expire, "type": "refresh"}
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


# 5. Валідація токена
def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
