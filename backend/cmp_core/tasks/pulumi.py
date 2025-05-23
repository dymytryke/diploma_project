# cmp_core/tasks/pulumi.py

import boto3
from celery import shared_task
from cmp_core.core.db_sync import SessionLocal
from cmp_core.lib.pulumi_project import destroy_project, up_project
from cmp_core.models.audit import AuditEvent
from cmp_core.models.project import Project
from cmp_core.models.resource import Resource, ResourceState
from sqlalchemy import select


@shared_task(name="cmp_core.tasks.reconcile_project")
def reconcile_project(project_id: str):
    """
    1) Load all of this project’s Resource rows
    2) Call Pulumi up (with our inline program & handlers)
    3) For each Resource, pick up the id, ip, status exports,
       then call EC2 DescribeInstances to get launch_time.
    4) If anything changed (state, out_id, public_ip, launch_time),
       write back and emit an audit event.
    """
    db = SessionLocal()
    ec2_clients: dict[str, boto3.client] = {}

    try:
        resources = db.query(Resource).filter_by(project_id=project_id).all()

        # run pulumi up (you may have already inserted your refresh() patch here)
        outputs = up_project(project_id, resources)

        for r in resources:
            # 1) copy existing meta
            meta = (r.meta or {}).copy()
            changed = False

            # 2) pick up the Pulumi exports (may be None)
            out_id = outputs.get(f"{r.name}-id")
            out_ip = outputs.get(f"{r.name}-ip")

            # we need a real AWS instance ID to drive any describe/start/stop
            aws_id = out_id or meta.get("aws_id")
            if not aws_id:
                # nothing to do until Pulumi first creates it
                continue

            # update meta with any newly exported aws_id
            if out_id and meta.get("aws_id") != out_id:
                meta["aws_id"] = out_id
                changed = True

            # 3) lazily create a per‐region client
            client = ec2_clients.setdefault(
                r.region, boto3.client("ec2", region_name=r.region)
            )

            # 4) pull the live AWS instance
            inst = client.describe_instances(InstanceIds=[aws_id])["Reservations"][0][
                "Instances"
            ][0]

            # 5) reconcile public IP
            real_ip = inst.get("PublicIpAddress", "")
            if real_ip and meta.get("public_ip") != real_ip:
                meta["public_ip"] = real_ip
                changed = True

            # 6) reconcile launch time
            real_lt = inst["LaunchTime"].isoformat()
            if meta.get("launch_time") != real_lt:
                meta["launch_time"] = real_lt
                changed = True

            # 7) converge desired (DB) <> actual (AWS) state
            aws_state = inst["State"]["Name"]
            mapping = {
                "pending": ResourceState.pending,
                "running": ResourceState.running,
                "shutting-down": ResourceState.terminating,
                "stopping": ResourceState.terminating,
                "stopped": ResourceState.stopped,
                "terminated": ResourceState.terminated,
            }
            actual = mapping.get(aws_state, ResourceState.error)

            # if we think it should be running, but it isn’t, start it
            if r.state == ResourceState.running and actual != ResourceState.running:
                client.start_instances(InstanceIds=[aws_id])
                client.get_waiter("instance_running").wait(InstanceIds=[aws_id])
                # now it really is running
                r.state = ResourceState.running
                changed = True

            # if we think it should be stopped, but it isn’t, stop it
            if r.state == ResourceState.stopped and actual != ResourceState.stopped:
                client.stop_instances(InstanceIds=[aws_id])
                client.get_waiter("instance_stopped").wait(InstanceIds=[aws_id])
                r.state = ResourceState.stopped
                changed = True

            # if it was pending, we’ll just take the real state
            if r.state == ResourceState.pending and actual is not None:
                r.state = actual
                changed = True

            # 8) (optionally) sync Pulumi’s IP export if you want,
            #     but out_ip may be stale compared to describe_instances
            if out_ip and meta.get("public_ip") != out_ip:
                meta["public_ip"] = out_ip
                changed = True

            # 9) write back if anything drifted
            if changed:
                r.meta = meta
                db.add(r)
                evt = AuditEvent(
                    user_id=getattr(r, "created_by", None),
                    project_id=project_id,
                    action="reconcile",
                    object_type="resource",
                    object_id=str(r.id),
                    details={"new_state": r.state, **meta},
                )
                db.add(evt)
        db.commit()

    finally:
        db.close()


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
