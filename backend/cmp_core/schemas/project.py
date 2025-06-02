from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProjectBase(BaseModel):
    name: str


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str


class ProjectOut(ProjectBase):
    id: UUID
    owner_id: UUID
    created_at: datetime
    resources_total: int = 0

    model_config = ConfigDict(from_attributes=True)
