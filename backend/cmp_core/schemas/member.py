from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProjectMemberCreate(BaseModel):
    user_id: UUID
    role_id: str  # enum: 'devops' або 'viewer'
    model_config = ConfigDict(from_attributes=True)


class ProjectMemberUpdate(BaseModel):
    role_id: str
    model_config = ConfigDict(from_attributes=True)


class ProjectMemberOut(BaseModel):
    user_id: UUID
    project_id: UUID
    role_id: str
    model_config = ConfigDict(from_attributes=True)
