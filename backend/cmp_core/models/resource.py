import enum

from sqlalchemy import JSON, Column, Enum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.mutable import MutableDict

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
    # User/API initiated states (desired state set, pending worker pickup)
    PENDING_PROVISION = "pending_provision"
    PENDING_UPDATE = "pending_update"
    PENDING_DEPROVISION = "pending_deprovision"
    PENDING_START = "pending_start"
    PENDING_STOP = "pending_stop"

    # Worker in-progress states (worker has picked up the task)
    PROVISIONING = "provisioning"
    UPDATING = "updating"
    DEPROVISIONING = "deprovisioning"
    STARTING = "starting"
    STOPPING = "stopping"

    # Stable/Operational states
    RUNNING = "running"
    STOPPED = "stopped"
    TERMINATED = "terminated"

    # Error states
    ERROR = "error"
    ERROR_PROVISIONING = "error_provisioning"
    ERROR_UPDATING = "error_updating"
    ERROR_DEPROVISIONING = "error_deprovisioning"
    ERROR_STARTING = "error_starting"
    ERROR_STOPPING = "error_stopping"

    UNKNOWN = "unknown"

    # --- Legacy states from your original model ---
    # These are kept for now to help with data migration.
    # You'll need a strategy to map existing data from these states to the new ones.
    # Once migrated, these can be removed from the enum.
    CREATING = "creating"  # Suggest mapping to PENDING_PROVISION or PROVISIONING
    TERMINATING = (
        "terminating"  # Suggest mapping to PENDING_DEPROVISION or DEPROVISIONING
    )
    PENDING = "pending"  # Suggest mapping to a specific PENDING_XXX or UNKNOWN


class Resource(IdMixin, TimestampMixin, Base):
    __tablename__ = "resources"  # Explicitly defining tablename, good practice

    project_id = Column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider = Column(
        Enum(Provider, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )  # Using your Provider enum
    resource_type = Column(
        Enum(ResourceType, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    name = Column(String(63), nullable=False)
    region = Column(String(32), nullable=False)  # Assuming region is always required

    # Updated state column to use the new ResourceState enum
    # and changed default to PENDING_PROVISION
    state = Column(
        Enum(
            ResourceState, values_callable=lambda obj: [e.value for e in obj]
        ),  # Tell SQLAlchemy to use the enum values
        nullable=False,
        default=ResourceState.PENDING_PROVISION,  # Default still uses the enum member
    )

    cost_daily = Column(Numeric(12, 4), nullable=False, server_default="0")
    meta = Column(
        MutableDict.as_mutable(JSON),
        default=dict,
        nullable=False,
    )
    created_by = Column(
        UUID(as_uuid=True),  # Assuming UUID is from sqlalchemy.dialects.postgresql
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_resources_project_name"),
    )

    def __repr__(self) -> str:
        return (
            f"<Resource(id={self.id}, name='{self.name}', project_id='{self.project_id}', "
            f"provider='{self.provider.value if self.provider else None}', "
            f"resource_type='{self.resource_type.value if self.resource_type else None}', "
            f"state='{self.state.value if self.state else None}')>"
        )
