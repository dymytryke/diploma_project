from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    role_id: str
    created_at: datetime  # або datetime

    model_config = ConfigDict(from_attributes=True)


class UserUpdateRole(BaseModel):
    role_id: str  # повинно бути одне з 'admin','devops','viewer'
