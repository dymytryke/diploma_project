# app/schemas/auth.py

from datetime import datetime

from pydantic import BaseModel, EmailStr


# 1. Запит на реєстрацію
class UserCreate(BaseModel):
    email: EmailStr
    password: str


# 2. Відповідь із токенами
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# 3. Дані з декодованого токена
class TokenPayload(BaseModel):
    sub: str
    exp: datetime
    type: str
