# cmp_core/schemas/azure.py

from typing import Any, Dict, Literal, Optional

from cmp_core.models.resource import ResourceState
from pydantic import BaseModel, ConfigDict, Field


class AzureCreate(BaseModel):
    name: str
    vm_size: str
    image_reference: Dict[str, str]  # {'publisher','offer','sku','version'}
    admin_username: str
    admin_password: str

    # Параметри для автоматичної мережі
    region: str | None = Field(None, description="Azure region (e.g. eastus)")
    vnet_address_prefix: str | None = Field(
        "10.0.0.0/16", description="VNet address space"
    )
    subnet_prefix: str | None = Field(
        "10.0.1.0/24", description="Subnet address prefix"
    )
    public_ip_allocation_method: Literal["Dynamic", "Static"] = Field(
        "Dynamic", description="Public IP allocation method"
    )

    model_config = ConfigDict(extra="ignore")


class AzureUpdate(BaseModel):
    vm_size: str | None = None
    admin_password: str | None = None


class AzureOut(BaseModel):
    id: str
    name: str
    region: str
    status: ResourceState  # Or str if you prefer to pass the value
    # Add other Azure VM specific fields you want to expose
    vm_size: Optional[str] = None
    public_ip: Optional[str] = None
    subscription_id: Optional[str] = None
    resource_group: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)
    dashboard_url: Optional[str] = None

    class Config:
        orm_mode = True  # or from_attributes = True for Pydantic v2
