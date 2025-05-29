# cmp_core/schemas/ec2.py
from typing import Optional

from pydantic import BaseModel


class Ec2Create(BaseModel):
    name: str
    region: str
    instance_type: str
    ami: str


class Ec2Update(BaseModel):
    instance_type: str


class Ec2Out(BaseModel):
    aws_id: Optional[str] = None
    name: str
    region: str
    instance_type: str
    public_ip: Optional[str] = None
    ami: Optional[str] = None
    launch_time: str
    status: str
    dashboard_url: str | None = None

    class Config:
        from_attributes = True
