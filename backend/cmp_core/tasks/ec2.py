# cmp_core/tasks/ec2.py
from cmp_core.celery_app import celery_app
from cmp_core.core.db_sync import SessionLocal
from cmp_core.lib.pulumi_ec2 import destroy_instance, up_instance
from cmp_core.models.audit import AuditEvent
from cmp_core.models.resource import Resource, ResourceState


@celery_app.task(name="cmp_core.tasks.create_ec2")
def create_ec2_task(resource_id: str, project_id: str, cfg: dict, user_id: str):
    """
    1) Run Pulumi up
    2) Update Resource row with outputs
    3) Emit AuditEvent
    """
    outputs = up_instance(project_id, cfg)

    db = SessionLocal()
    try:
        res = db.query(Resource).get(resource_id)
        # update the DB row with Pulumi outputs
        res.state = outputs["status"]
        res.meta = {
            "aws_id": outputs["aws_id"],
            "public_ip": outputs["public_ip"],
            "ami": outputs["ami"],
            "instance_type": outputs["instance_type"],
        }
        db.add(res)

        evt = AuditEvent(
            user_id=user_id,
            project_id=project_id,
            action="create_ec2",
            object_type="ec2",
            object_id=str(res.id),
            details=res.meta,
        )
        db.add(evt)

        db.commit()
    finally:
        db.close()

    return outputs


@celery_app.task(name="cmp_core.tasks.delete_ec2")
def delete_ec2_task(resource_id: str, user_id: str, project_id: str):
    """
    1) Run Pulumi destroy
    2) Mark Resource as terminated
    3) Emit AuditEvent
    """
    # 1) tear down in Pulumi
    destroy_instance(project_id)

    # 2) update DB
    db = SessionLocal()
    try:
        res: Resource = db.query(Resource).get(resource_id)
        res.state = ResourceState.terminated
        db.add(res)

        # 3) audit
        evt = AuditEvent(
            user_id=user_id,
            project_id=project_id,
            action="delete_ec2",
            object_type="ec2",
            object_id=resource_id,
            details={"name": res.name},
        )
        db.add(evt)

        db.commit()
    finally:
        db.close()
