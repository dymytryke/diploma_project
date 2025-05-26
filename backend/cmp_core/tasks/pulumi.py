# cmp_core/tasks/pulumi.py

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import boto3
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


def reconcile_single(
    resource: Resource, outputs: dict, ec2_clients: dict
) -> tuple[Resource, AuditEvent] | None:
    meta = (resource.meta or {}).copy()
    changed = False

    out_id = outputs.get(f"{resource.name}-id")
    out_ip = outputs.get(f"{resource.name}-ip")
    aws_id = out_id or meta.get("aws_id")
    if not aws_id:
        return None

    # Оновлення aws_id
    if out_id and meta.get("aws_id") != out_id:
        meta["aws_id"] = out_id
        changed = True

    # Одержуємо/створюємо клієнт EC2
    client = ec2_clients.setdefault(
        resource.region, boto3.client("ec2", region_name=resource.region)
    )

    info = fetch_aws_info(client, aws_id)

    # Порівнюємо та оновлюємо public_ip і launch_time
    if info["public_ip"] and meta.get("public_ip") != info["public_ip"]:
        meta["public_ip"] = info["public_ip"]
        changed = True

    if meta.get("launch_time") != info["launch_time"]:
        meta["launch_time"] = info["launch_time"]
        changed = True

    # Мапінг станів
    mapping = {
        "pending": ResourceState.pending,
        "running": ResourceState.running,
        "shutting-down": ResourceState.terminating,
        "stopping": ResourceState.terminating,
        "stopped": ResourceState.stopped,
        "terminated": ResourceState.terminated,
    }
    actual_state = mapping.get(info["state"], ResourceState.error)

    # Конвергенція бажаного та фактичного стану
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
            # будь-який інший (pending, terminating тощо): синхронізуємо зі справжнім станом
            resource.state = actual_state
            changed = True

    # Додатковий синхронізований public_ip з Pulumi
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

        # Паралельне оброблення ресурсів
        with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            futures = {
                executor.submit(reconcile_single, r, outputs, ec2_clients): r
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
    db = SessionLocal()
    try:
        # Pull back just the project IDs (UUIDs)
        result = db.execute(select(Project.id))
        project_ids = [str(pid) for pid in result.scalars().all()]

        for pid in project_ids:
            reconcile_project.delay(pid)
    finally:
        db.close()
