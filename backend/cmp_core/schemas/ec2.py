# cmp_core/schemas/ec2.py
from pydantic import BaseModel


class Ec2Create(BaseModel):
    name: str
    region: str
    instance_type: str
    ami: str


class Ec2Update(BaseModel):
    instance_type: str


class Ec2Out(BaseModel):
    aws_id: str
    name: str
    region: str
    instance_type: str
    public_ip: str
    ami: str
    launch_time: str
    status: str

    class Config:
        from_attributes = True
