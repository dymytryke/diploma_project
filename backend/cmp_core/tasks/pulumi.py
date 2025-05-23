# cmp_core/tasks/pulumi.py

import boto3
from celery import shared_task
from cmp_core.core.db_sync import SessionLocal
from cmp_core.lib.pulumi_project import destroy_project, up_project
from cmp_core.models.audit import AuditEvent
from cmp_core.models.resource import Resource


@shared_task(name="cmp_core.tasks.reconcile_project")
def reconcile_project(project_id: str):
    """
    1) Load all of this project’s Resource rows
    2) Call Pulumi up (with our inline program & handlers)
    3) For each Resource, pick up the id, ip, status exports,
       then call EC2 DescribeInstances to get launch_time.
    4) If anything changed (state, aws_id, public_ip, launch_time),
       write back and emit an audit event.
    """
    db = SessionLocal()
    ec2_clients: dict[str, boto3.client] = {}

    try:
        resources = db.query(Resource).filter_by(project_id=project_id).all()

        # run pulumi up (you may have already inserted your refresh() patch here)
        outputs = up_project(project_id, resources)

        for r in resources:
            # 1) copy existing meta so we never get an unbound-local error
            meta = (r.meta or {}).copy()
            changed = False

            # 2) pick up the Pulumi exports
            out_id = outputs.get(f"{r.name}-id")
            out_ip = outputs.get(f"{r.name}-ip")
            out_status = outputs.get(f"{r.name}-status")

            # 3) reconcile state
            if out_status and r.state != out_status:
                r.state = out_status
                changed = True

            # 4) reconcile aws_id / public_ip
            if out_id and meta.get("aws_id") != out_id:
                meta["aws_id"] = out_id
                changed = True
            if out_ip and meta.get("public_ip") != out_ip:
                meta["public_ip"] = out_ip
                changed = True

            # 5) fetch launch_time via boto3, keyed by each resource.region
            if out_id:
                region = r.region
                # lazily create a client for this region
                if region not in ec2_clients:
                    ec2_clients[region] = boto3.client("ec2", region_name=region)
                resp = ec2_clients[region].describe_instances(InstanceIds=[out_id])
                lt = resp["Reservations"][0]["Instances"][0]["LaunchTime"].isoformat()
                # if launch_time changed, record it
                if meta.get("launch_time") != lt:
                    meta["launch_time"] = lt
                    changed = True

            # 6) if anything changed, write back & audit
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
