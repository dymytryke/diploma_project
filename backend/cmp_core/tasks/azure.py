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

        # запускаємо VM
        poller = client.virtual_machines.begin_start(rg, name)
        poller.result()  # чекаємо завершення

        # оновлюємо стан
        res.state = ResourceState.running
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

        # зупиняємо VM
        poller = client.virtual_machines.begin_power_off(rg, name)
        poller.result()  # чекаємо завершення

        # оновлюємо стан
        res.state = ResourceState.stopped
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
