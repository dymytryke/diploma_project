# cmp_core/tasks/pulumi.py

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import boto3
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from celery import shared_task
from cmp_core.core.db_sync import SessionLocal
from cmp_core.lib.pulumi_project import destroy_project, up_project
from cmp_core.models.audit import AuditEvent
from cmp_core.models.project import Project
from cmp_core.models.resource import Resource, ResourceState
from sqlalchemy import select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
MAX_THREADS = 10  # можна налаштувати через конфіг


def load_resources(session: Session, project_id: str) -> list[Resource]:
    return session.query(Resource).filter_by(project_id=project_id).all()


def fetch_aws_info(client, aws_id: str) -> dict:
    resp = client.describe_instances(InstanceIds=[aws_id])
    inst = resp["Reservations"][0]["Instances"][0]
    return {
        "public_ip": inst.get("PublicIpAddress", ""),
        "launch_time": inst["LaunchTime"].isoformat(),
        "state": inst["State"]["Name"],
    }


def parse_azure_id(vm_id: str) -> tuple[str, str, str]:
    parts = vm_id.strip("/").split("/")
    # /subscriptions/{sub}/resourceGroups/{rg}/providers/.../virtualMachines/{vm}
    return parts[1], parts[3], parts[-1]


def fetch_azure_info(
    vm_id: str,
    cred: DefaultAzureCredential,
    compute_clients: dict,
    network_clients: dict,
) -> dict:
    sub, rg, name = parse_azure_id(vm_id)
    compute = compute_clients.setdefault(sub, ComputeManagementClient(cred, sub))
    network = network_clients.setdefault(sub, NetworkManagementClient(cred, sub))

    vm = compute.virtual_machines.get(rg, name, expand="instanceView")
    # PowerState/status
    ps = next(
        (
            s.code.split("/")[-1]
            for s in vm.instance_view.statuses
            if s.code.startswith("PowerState/")
        ),
        None,
    )

    # public IP via NIC
    nic_ref = vm.network_profile.network_interfaces[0].id
    nic_name = nic_ref.split("/networkInterfaces/")[-1]
    nic = network.network_interfaces.get(rg, nic_name)
    ip_conf = nic.ip_configurations[0]
    public_ip = ""
    if ip_conf.public_ip_address:
        pip_id = ip_conf.public_ip_address.id
        pip_name = pip_id.split("/publicIPAddresses/")[-1]
        pip = network.public_ip_addresses.get(rg, pip_name)
        public_ip = pip.ip_address or ""

    return {"public_ip": public_ip, "power_state": ps}


def reconcile_single(
    resource: Resource,
    outputs: dict,
    ec2_clients: dict,
    azure_cred: DefaultAzureCredential,
    azure_compute: dict,
    azure_network: dict,
) -> tuple[Resource, AuditEvent] | None:
    meta = (resource.meta or {}).copy()
    changed = False

    # Azure VM
    if resource.provider.value == "azure":
        vm_id = outputs.get(f"{resource.name}-id") or meta.get("azure_vm_id")
        if not vm_id:
            return None

        # Ensure the definitive vm_id (Azure Resource ID) is stored in meta
        # and mark as changed if it's new or different.
        if meta.get("azure_vm_id") != vm_id:
            meta["azure_vm_id"] = vm_id
            changed = True

        info = fetch_azure_info(vm_id, azure_cred, azure_compute, azure_network)
        if info["public_ip"] and meta.get("public_ip") != info["public_ip"]:
            meta["public_ip"] = info["public_ip"]
            changed = True
        if meta.get("power_state") != info["power_state"]:
            meta["power_state"] = info["power_state"]
            changed = True

        if not changed:
            return None

        resource.meta = meta
        event = AuditEvent(
            user_id=getattr(resource, "created_by", None),
            project_id=resource.project_id,
            action="reconcile",
            object_type="resource",
            object_id=str(resource.id),
            details={"power_state": meta["power_state"], **meta},
        )
        return resource, event

    # AWS EC2
    out_id = outputs.get(f"{resource.name}-id")
    out_ip = outputs.get(f"{resource.name}-ip")
    aws_id = out_id or meta.get("aws_id")
    if not aws_id:
        return None

    if out_id and meta.get("aws_id") != out_id:
        meta["aws_id"] = out_id
        changed = True

    client = ec2_clients.setdefault(
        resource.region,
        boto3.client("ec2", region_name=resource.region),
    )

    info = fetch_aws_info(client, aws_id)
    if info["public_ip"] and meta.get("public_ip") != info["public_ip"]:
        meta["public_ip"] = info["public_ip"]
        changed = True
    if meta.get("launch_time") != info["launch_time"]:
        meta["launch_time"] = info["launch_time"]
        changed = True

    mapping = {
        "pending": ResourceState.pending,
        "running": ResourceState.running,
        "shutting-down": ResourceState.terminating,
        "stopping": ResourceState.terminating,
        "stopped": ResourceState.stopped,
        "terminated": ResourceState.terminated,
    }
    actual_state = mapping.get(info["state"], ResourceState.error)

    desired = resource.state
    if desired != actual_state:
        if desired == ResourceState.running:
            client.start_instances(InstanceIds=[aws_id])
            client.get_waiter("instance_running").wait(InstanceIds=[aws_id])
            resource.state = ResourceState.running
            changed = True
        elif desired == ResourceState.stopped:
            client.stop_instances(InstanceIds=[aws_id])
            client.get_waiter("instance_stopped").wait(InstanceIds=[aws_id])
            resource.state = ResourceState.stopped
            changed = True
        else:
            resource.state = actual_state
            changed = True

    if out_ip and meta.get("public_ip") != out_ip:
        meta["public_ip"] = out_ip
        changed = True

    if not changed:
        return None

    resource.meta = meta
    event = AuditEvent(
        user_id=getattr(resource, "created_by", None),
        project_id=resource.project_id,
        action="reconcile",
        object_type="resource",
        object_id=str(resource.id),
        details={"new_state": resource.state, **meta},
    )
    return resource, event


@shared_task(name="cmp_core.tasks.reconcile_project")
def reconcile_project(project_id: str):
    logger.info(f"Start reconcile for project {project_id}")
    with SessionLocal() as session:
        resources = load_resources(session, project_id)
        outputs = up_project(project_id, resources)

        ec2_clients: dict[str, boto3.client] = {}
        azure_cred = DefaultAzureCredential()
        azure_compute_clients: dict[str, ComputeManagementClient] = {}
        azure_network_clients: dict[str, NetworkManagementClient] = {}

        with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            futures = {
                executor.submit(
                    reconcile_single,
                    r,
                    outputs,
                    ec2_clients,
                    azure_cred,
                    azure_compute_clients,
                    azure_network_clients,
                ): r
                for r in resources
            }
            for future in as_completed(futures):
                result = future.result()
                if result:
                    resource, event = result
                    session.add(resource)
                    session.add(event)

        session.commit()
    logger.info(f"Finish reconcile for project {project_id}")


@shared_task(name="cmp_core.tasks.destroy_project")
def destroy_project_task(project_id: str):
    """
    Tear down ALL cloud resources in the Pulumi stack for this project.
    """
    destroy_project(project_id)


@shared_task(name="cmp_core.tasks.reconcile_all_projects")
def reconcile_all_projects():
    """
    Find every project and enqueue a reconcile for each.
    """
    with SessionLocal() as session:
        result = session.execute(select(Project.id))
        project_ids = [str(pid) for pid in result.scalars().all()]
        for pid in project_ids:
            reconcile_project.delay(pid)
