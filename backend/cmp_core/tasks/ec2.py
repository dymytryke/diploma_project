# cmp_core/tasks/ec2.py
import logging

import boto3
from celery import shared_task
from cmp_core.core.db_sync import SessionLocal
from cmp_core.models.audit import AuditEvent
from cmp_core.models.resource import Resource, ResourceState

logger = logging.getLogger(__name__)


@shared_task(name="cmp_core.tasks.start_ec2_task")
def start_ec2_task(resource_id: str, user_id: str):  # user_id for audit event
    logger.info(f"Starting EC2 task for resource_id: {resource_id}")
    with SessionLocal() as session:
        try:
            resource = session.query(Resource).filter_by(id=resource_id).one_or_none()
            if not resource:
                logger.error(f"Resource {resource_id} not found for start_ec2_task.")
                return

            if resource.state != ResourceState.PENDING_START:
                logger.warning(
                    f"start_ec2_task called for resource {resource_id} not in PENDING_START state (current: {resource.state.value}). Proceeding cautiously."
                )
                # Or, you could choose to exit if not PENDING_START:
                # if resource.state != ResourceState.PENDING_START:
                #     logger.error(f"Resource {resource_id} is not in PENDING_START state. Aborting start task.")
                #     return

            resource.state = ResourceState.STARTING
            session.add(resource)
            session.commit()
            logger.info(f"Resource {resource_id} state set to STARTING.")

            aws_id = resource.meta.get("aws_id")
            if not aws_id:
                logger.error(f"aws_id not found in meta for resource {resource_id}.")
                resource.state = ResourceState.ERROR_STARTING
                resource.meta["error_message"] = "aws_id missing in metadata"
                session.add(resource)
                session.commit()
                return

            client = boto3.client("ec2", region_name=resource.region)
            client.start_instances(InstanceIds=[aws_id])

            # Wait for instance to be running (optional, can be long)
            # For simplicity, we'll assume start_instances initiates it and a poller/reconciler would confirm RUNNING.
            # Or, we can do a brief wait and check here.
            # For now, let's optimistically set to RUNNING if API call succeeds.
            # A more robust solution would involve a waiter or subsequent status check.

            resource.state = ResourceState.RUNNING
            logger.info(f"EC2 instance {aws_id} start initiated. State set to RUNNING.")
            action = "ec2_start_success"
            details = {"aws_id": aws_id, "final_state": resource.state.value}

        except Exception as e:
            logger.error(
                f"Error starting EC2 instance {resource_id}: {e}", exc_info=True
            )
            if resource:  # Check if resource was loaded
                resource.state = ResourceState.ERROR_STARTING
                resource.meta["error_message"] = str(e)
                action = "ec2_start_failure"
                details = {
                    "aws_id": resource.meta.get("aws_id"),
                    "error": str(e),
                    "final_state": resource.state.value,
                }
            else:  # Should not happen if initial check passes
                action = "ec2_start_failure_no_resource"
                details = {"resource_id": resource_id, "error": str(e)}
        finally:
            if resource:  # Ensure resource is defined for audit event
                event = AuditEvent(
                    user_id=user_id,
                    project_id=resource.project_id,
                    action=action,
                    object_type="resource",
                    object_id=str(resource.id),
                    details=details,
                )
                session.add(event)
            session.commit()
    logger.info(f"Finished EC2 start task for resource_id: {resource_id}")


@shared_task(name="cmp_core.tasks.stop_ec2_task")
def stop_ec2_task(resource_id: str, user_id: str):
    logger.info(f"Starting EC2 stop task for resource_id: {resource_id}")
    with SessionLocal() as session:
        try:
            resource = session.query(Resource).filter_by(id=resource_id).one_or_none()
            if not resource:
                logger.error(f"Resource {resource_id} not found for stop_ec2_task.")
                return

            if resource.state != ResourceState.PENDING_STOP:
                logger.warning(
                    f"stop_ec2_task called for resource {resource_id} not in PENDING_STOP state (current: {resource.state.value}). Proceeding cautiously."
                )

            resource.state = ResourceState.STOPPING
            session.add(resource)
            session.commit()
            logger.info(f"Resource {resource_id} state set to STOPPING.")

            aws_id = resource.meta.get("aws_id")
            if not aws_id:
                logger.error(f"aws_id not found in meta for resource {resource_id}.")
                resource.state = ResourceState.ERROR_STOPPING
                resource.meta["error_message"] = "aws_id missing in metadata"
                session.add(resource)
                session.commit()
                return

            client = boto3.client("ec2", region_name=resource.region)
            client.stop_instances(InstanceIds=[aws_id])

            # Similar to start, we optimistically set to STOPPED.
            # A robust solution would use waiters or subsequent status checks.
            resource.state = ResourceState.STOPPED
            logger.info(f"EC2 instance {aws_id} stop initiated. State set to STOPPED.")
            action = "ec2_stop_success"
            details = {"aws_id": aws_id, "final_state": resource.state.value}

        except Exception as e:
            logger.error(
                f"Error stopping EC2 instance {resource_id}: {e}", exc_info=True
            )
            if resource:
                resource.state = ResourceState.ERROR_STOPPING
                resource.meta["error_message"] = str(e)
                action = "ec2_stop_failure"
                details = {
                    "aws_id": resource.meta.get("aws_id"),
                    "error": str(e),
                    "final_state": resource.state.value,
                }
            else:
                action = "ec2_stop_failure_no_resource"
                details = {"resource_id": resource_id, "error": str(e)}
        finally:
            if resource:
                event = AuditEvent(
                    user_id=user_id,
                    project_id=resource.project_id,
                    action=action,
                    object_type="resource",
                    object_id=str(resource.id),
                    details=details,
                )
                session.add(event)
            session.commit()
    logger.info(f"Finished EC2 stop task for resource_id: {resource_id}")
