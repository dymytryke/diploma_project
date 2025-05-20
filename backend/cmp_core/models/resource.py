import enum

from sqlalchemy import JSON, Column, Enum, ForeignKey, Numeric, String, UniqueConstraint

from .base import Base
from .mixins import IdMixin, TimestampMixin


class Provider(str, enum.Enum):
    aws = "aws"
    azure = "azure"
    gcp = "gcp"


class ResourceType(str, enum.Enum):
    vm = "vm"
    volume = "volume"
    bucket = "bucket"
    db = "db"
    lb = "lb"


class ResourceState(str, enum.Enum):
    creating = "creating"
    running = "running"
    stopped = "stopped"
    terminating = "terminating"
    terminated = "terminated"
    error = "error"
    pending = "pending"


class Resource(IdMixin, TimestampMixin, Base):
    project_id = Column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider = Column(Enum(Provider), nullable=False)
    resource_type = Column(Enum(ResourceType), nullable=False)
    name = Column(String(63), nullable=False)
    region = Column(String(32), nullable=False)
    state = Column(Enum(ResourceState), nullable=False, default=ResourceState.creating)
    cost_daily = Column(Numeric(12, 4), nullable=False, server_default="0")
    meta = Column(JSON, default=dict)
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_resources_project_name"),
    )
