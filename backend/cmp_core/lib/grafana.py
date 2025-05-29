# cmp_core/lib/grafana.py

from urllib.parse import urlencode

from cmp_core.core.config import settings


def make_dashboard_url(
    provider: str,
    resource_type: str,
    region: str,
    instance_id: str | None = None,  # Used for AWS EC2
    subscription_id: str | None = None,  # Used for Azure VM
    resource_group: str | None = None,  # Used for Azure VM
    vm_name: str | None = None,  # Used for Azure VM
) -> str:
    key = f"{provider.lower()}_{resource_type.lower()}"  # Ensure lowercase for key consistency
    try:
        # Assuming settings.grafana_dashboard_uids contains entries like:
        # "aws_vm": "aws-ec2-instance-uid"
        # "azure_vm": "azure-vm-golden" (this is the UID of your dashboard)
        uid = settings.grafana_dashboard_uids[key]
    except KeyError:
        raise ValueError(
            f"No Grafana dashboard UID configured for {key!r} in settings.grafana_dashboard_uids"
        )

    # slug = uid by default; this matches your Azure VM dashboard URL structure
    # e.g., /d/azure-vm-golden/azure-vm-golden
    path = f"/d/{uid}/{uid}"

    qs = {
        "orgId": settings.grafana_org_id,
        "refresh": "30s",  # Default refresh rate, can be made a parameter if needed
    }

    if provider.lower() == "aws" and resource_type.lower() == "vm":
        if region:
            qs["var-region"] = region  # Grafana variable for AWS region
        if instance_id:
            qs["var-instanceId"] = instance_id  # Grafana variable for AWS instance ID
    elif provider.lower() == "azure" and resource_type.lower() == "vm":
        if subscription_id:
            qs["var-subscription"] = subscription_id
        if resource_group:
            qs["var-resourceGroup"] = resource_group
        if vm_name:
            qs["var-vmName"] = vm_name
        if region:  # Azure dashboard also uses region
            qs["var-region"] = region
    else:
        # Fallback or raise error for unsupported combinations if necessary
        # For now, we'll assume the key lookup handles unsupported types
        pass

    if settings.grafana_kiosk:
        qs["kiosk"] = "tv"

    return f"{settings.grafana_base_url.rstrip('/')}{path}?{urlencode(qs)}"
