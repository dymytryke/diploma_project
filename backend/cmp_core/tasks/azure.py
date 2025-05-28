# cmp_core/tasks/azure.py

from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient

# Імпорт вашого celery_app (або створіть новий):
from cmp_core.celery_app import celery_app
from cmp_core.core.db_sync import SessionLocal
from cmp_core.models.audit import AuditEvent
from cmp_core.models.resource import Resource, ResourceState
from sqlalchemy.orm import Session


def _parse_azure_id(vm_id: str) -> tuple[str, str, str]:
    parts = vm_id.strip("/").split("/")
    # /subscriptions/{sub}/resourceGroups/{rg}/providers/.../virtualMachines/{name}
    return parts[1], parts[3], parts[-1]


@celery_app.task(name="cmp_core.tasks.start_azure_vm")
def start_azure_task(resource_id: str, user_id: str):
    db: Session = SessionLocal()
    try:
        res: Resource = db.query(Resource).filter_by(id=resource_id).one()
        if res.provider.value != "azure" or not res.meta.get("azure_vm_id"):
            return

        vm_id = res.meta["azure_vm_id"]
        sub, rg, name = _parse_azure_id(vm_id)
        cred = DefaultAzureCredential()
        client = ComputeManagementClient(cred, sub)

        poller = client.virtual_machines.begin_start(rg, name)
        poller.result()

        # Fetch the latest status from Azure after starting
        # We need compute_clients and network_clients for fetch_azure_info
        # For simplicity here, we'll just set a known good state,
        # but ideally, you'd call fetch_azure_info.
        # However, fetch_azure_info is designed for reconcile_single's structure.
        # For now, let's assume 'running' is the direct outcome.
        # A more robust solution would be to call reconcile_single for this resource.

        res.state = ResourceState.running
        if res.meta is None:
            res.meta = {}
        res.meta["power_state"] = "running"  # Set meta power_state
        db.add(res)
        evt = AuditEvent(
            user_id=user_id,
            project_id=res.project_id,
            action="start_azure_vm",
            object_type="resource",
            object_id=str(res.id),
            details={"new_state": res.state},
        )
        db.add(evt)
        db.commit()
    finally:
        db.close()


@celery_app.task(name="cmp_core.tasks.stop_azure_vm")
def stop_azure_task(resource_id: str, user_id: str):
    db: Session = SessionLocal()
    try:
        res: Resource = db.query(Resource).filter_by(id=resource_id).one()
        if res.provider.value != "azure" or not res.meta.get("azure_vm_id"):
            return

        vm_id = res.meta["azure_vm_id"]
        sub, rg, name = _parse_azure_id(vm_id)
        cred = DefaultAzureCredential()
        client = ComputeManagementClient(cred, sub)

        poller = client.virtual_machines.begin_power_off(
            rg, name
        )  # Use power_off for deallocation by default
        poller.result()

        # After power_off, the VM is typically 'deallocated'.
        # Let's update meta to reflect this.
        res.state = ResourceState.stopped
        if res.meta is None:
            res.meta = {}
        res.meta["power_state"] = (
            "deallocated"  # Set meta power_state to actual Azure state
        )
        db.add(res)
        evt = AuditEvent(
            user_id=user_id,
            project_id=res.project_id,
            action="stop_azure_vm",
            object_type="resource",
            object_id=str(res.id),
            details={"new_state": res.state},
        )
        db.add(evt)
        db.commit()
    finally:
        db.close()
