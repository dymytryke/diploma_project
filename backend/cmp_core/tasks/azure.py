# cmp_core/tasks/azure.py

import logging  # Add logging
import re  # For parsing Azure ID

from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient

# Імпорт вашого celery_app (або створіть новий):
from cmp_core.celery_app import celery_app
from cmp_core.core.db_sync import SessionLocal
from cmp_core.models.audit import AuditEvent
from cmp_core.models.resource import Resource, ResourceState

logger = logging.getLogger(__name__)  # Add logger


def _parse_azure_id(vm_id: str) -> tuple[str | None, str | None, str | None]:
    """
    Parses an Azure VM ID string into subscription ID, resource group name, and VM name.
    Example ID: /subscriptions/YOUR_SUB_ID/resourceGroups/YOUR_RG_NAME/providers/Microsoft.Compute/virtualMachines/YOUR_VM_NAME
    Returns (None, None, None) if parsing fails.
    """
    if not vm_id:
        return None, None, None
    # Corrected regex to be more robust and handle potential case variations in provider segment
    match = re.search(
        r"/subscriptions/(?P<subscription_id>[^/]+)/resourceGroups/(?P<resource_group_name>[^/]+)/providers/Microsoft\.Compute/virtualMachines/(?P<vm_name>[^/]+)",
        vm_id,
        re.IGNORECASE,  # Add IGNORECASE for provider segment
    )
    if match:
        return (
            match.group("subscription_id"),
            match.group("resource_group_name"),
            match.group("vm_name"),
        )
    logger.warning(f"Could not parse Azure VM ID with regex: {vm_id}")
    return None, None, None


@celery_app.task(name="cmp_core.tasks.start_azure_vm")  # Original name
def start_azure_task(resource_id: str, user_id: str):  # Renamed for consistency
    logger.info(f"Starting Azure VM task for resource_id: {resource_id}")
    with SessionLocal() as session:  # Use with statement for session management
        resource: Resource | None = None
        action = "azure_vm_start_attempt"  # Default action for audit
        details = {"resource_id": resource_id}

        try:
            resource = session.query(Resource).filter_by(id=resource_id).one_or_none()
            if not resource:
                logger.error(f"Resource {resource_id} not found for start_azure_task.")
                # No resource to update, so can't set error state on it.
                # Audit event will capture the attempt.
                action = "azure_vm_start_failure_no_resource"
                details["error"] = "Resource not found"
                return  # Exit if no resource

            if resource.provider.value != "azure":
                logger.error(f"Resource {resource_id} is not an Azure resource.")
                resource.state = (
                    ResourceState.ERROR_STARTING
                )  # Mark error on the resource
                resource.meta["error_message"] = "Not an Azure resource"
                action = "azure_vm_start_failure_wrong_provider"
                details["error"] = "Not an Azure resource"
                session.add(resource)
                return

            azure_vm_id = resource.meta.get("azure_vm_id")
            if not azure_vm_id:
                logger.error(
                    f"azure_vm_id not found in meta for resource {resource_id}."
                )
                resource.state = ResourceState.ERROR_STARTING
                resource.meta["error_message"] = "azure_vm_id missing"
                action = "azure_vm_start_failure_no_vm_id"
                details["error"] = "azure_vm_id missing"
                session.add(resource)
                return

            if resource.state != ResourceState.PENDING_START:
                logger.warning(
                    f"start_azure_task called for resource {resource_id} not in PENDING_START state (current: {resource.state.value}). Proceeding cautiously."
                )
                # Optionally, exit if not PENDING_START

            resource.state = ResourceState.STARTING
            session.add(resource)
            session.commit()  # Commit STARTING state
            logger.info(f"Resource {resource_id} state set to STARTING.")
            details["initial_state_set"] = "STARTING"

            sub, rg, name = _parse_azure_id(azure_vm_id)
            if not all([sub, rg, name]):
                logger.error(
                    f"Failed to parse Azure VM ID: {azure_vm_id} for resource {resource_id}"
                )
                resource.state = ResourceState.ERROR_STARTING
                resource.meta["error_message"] = (
                    f"Failed to parse Azure VM ID: {azure_vm_id}"
                )
                action = "azure_vm_start_failure_parse_id"
                details["error"] = "Failed to parse Azure VM ID"
                session.add(resource)
                return

            cred = DefaultAzureCredential()
            client = ComputeManagementClient(cred, sub)

            logger.info(
                f"Attempting to start Azure VM: {name} in RG: {rg} (Sub: {sub})"
            )
            poller = client.virtual_machines.begin_start(rg, name)
            poller.result()  # Wait for completion

            # After successful start, fetch current instance view to get actual power state
            try:
                vm_instance_view = client.virtual_machines.instance_view(rg, name)
                actual_power_state = "unknown"
                if vm_instance_view.statuses:
                    for status_obj in vm_instance_view.statuses:
                        if status_obj.code and status_obj.code.lower().startswith(
                            "powerstate/"
                        ):
                            actual_power_state = (
                                status_obj.display_status
                            )  # e.g., "VM running"
                            break
                resource.meta["power_state"] = actual_power_state
                logger.info(
                    f"Azure VM {name} started. Actual power state: {actual_power_state}"
                )
            except Exception as e_pv:
                logger.warning(
                    f"Could not fetch power state for Azure VM {name} after start: {e_pv}"
                )
                resource.meta["power_state"] = "running (assumed)"  # Fallback

            resource.state = ResourceState.RUNNING
            action = "azure_vm_start_success"
            details = {
                "azure_vm_id": azure_vm_id,
                "final_state": resource.state.value,
                "power_state": resource.meta.get("power_state"),
            }
            logger.info(
                f"Azure VM {azure_vm_id} start completed. State set to RUNNING."
            )

        except Exception as e:
            logger.error(f"Error starting Azure VM {resource_id}: {e}", exc_info=True)
            if resource:  # Check if resource was loaded
                resource.state = ResourceState.ERROR_STARTING
                if resource.meta is None:
                    resource.meta = {}
                resource.meta["error_message"] = str(e)
                action = "azure_vm_start_failure"
                details = {
                    "azure_vm_id": resource.meta.get("azure_vm_id"),
                    "error": str(e),
                    "final_state": resource.state.value,
                }
            else:  # This case is handled by the initial resource check, but as a fallback
                action = "azure_vm_start_failure_no_resource_in_exception"
                details = {"resource_id": resource_id, "error": str(e)}
        finally:
            if (
                resource
            ):  # If resource object exists, add it to session for final commit
                session.add(resource)

            # Create audit event regardless of resource presence if an attempt was made
            event_user_id = user_id
            event_project_id = (
                resource.project_id if resource else None
            )  # Get project_id if resource exists
            event_object_id = str(resource.id) if resource else resource_id

            # Ensure details has final state if resource exists
            if resource and "final_state" not in details:
                details["final_state"] = (
                    resource.state.value if resource.state else "unknown"
                )

            audit_event = AuditEvent(
                user_id=event_user_id,
                project_id=event_project_id,
                action=action,
                object_type="resource",
                object_id=event_object_id,
                details=details,
            )
            session.add(audit_event)
            session.commit()  # Commit resource state changes and audit event
    logger.info(f"Finished Azure VM start task for resource_id: {resource_id}")


@celery_app.task(name="cmp_core.tasks.stop_azure_vm")  # Original name
def stop_azure_task(resource_id: str, user_id: str):  # Renamed for consistency
    logger.info(f"Starting Azure VM stop task for resource_id: {resource_id}")
    with SessionLocal() as session:
        resource: Resource | None = None
        action = "azure_vm_stop_attempt"
        details = {"resource_id": resource_id}

        try:
            resource = session.query(Resource).filter_by(id=resource_id).one_or_none()
            if not resource:
                logger.error(f"Resource {resource_id} not found for stop_azure_task.")
                action = "azure_vm_stop_failure_no_resource"
                details["error"] = "Resource not found"
                return

            if resource.provider.value != "azure":
                logger.error(f"Resource {resource_id} is not an Azure resource.")
                resource.state = ResourceState.ERROR_STOPPING
                resource.meta["error_message"] = "Not an Azure resource"
                action = "azure_vm_stop_failure_wrong_provider"
                details["error"] = "Not an Azure resource"
                session.add(resource)
                return

            azure_vm_id = resource.meta.get("azure_vm_id")
            if not azure_vm_id:
                logger.error(
                    f"azure_vm_id not found in meta for resource {resource_id}."
                )
                resource.state = ResourceState.ERROR_STOPPING
                resource.meta["error_message"] = "azure_vm_id missing"
                action = "azure_vm_stop_failure_no_vm_id"
                details["error"] = "azure_vm_id missing"
                session.add(resource)
                return

            if resource.state != ResourceState.PENDING_STOP:
                logger.warning(
                    f"stop_azure_task called for resource {resource_id} not in PENDING_STOP state (current: {resource.state.value}). Proceeding cautiously."
                )

            resource.state = ResourceState.STOPPING
            session.add(resource)
            session.commit()  # Commit STOPPING state
            logger.info(f"Resource {resource_id} state set to STOPPING.")
            details["initial_state_set"] = "STOPPING"

            sub, rg, name = _parse_azure_id(azure_vm_id)
            if not all([sub, rg, name]):
                logger.error(
                    f"Failed to parse Azure VM ID: {azure_vm_id} for resource {resource_id}"
                )
                resource.state = ResourceState.ERROR_STOPPING
                resource.meta["error_message"] = (
                    f"Failed to parse Azure VM ID: {azure_vm_id}"
                )
                action = "azure_vm_stop_failure_parse_id"
                details["error"] = "Failed to parse Azure VM ID"
                session.add(resource)
                return

            cred = DefaultAzureCredential()
            client = ComputeManagementClient(cred, sub)

            logger.info(
                f"Attempting to stop (deallocate) Azure VM: {name} in RG: {rg} (Sub: {sub})"
            )
            # Using begin_power_off by default deallocates.
            # If you only want to stop without deallocating, use:
            # poller = client.virtual_machines.begin_power_off(rg, name, skip_shutdown=True) # This is not standard, check SDK for non-deallocating stop
            # For deallocation (common for cost saving):
            poller = client.virtual_machines.begin_deallocate(rg, name)
            poller.result()  # Wait for completion

            try:
                vm_instance_view = client.virtual_machines.instance_view(rg, name)
                actual_power_state = "unknown"
                if vm_instance_view.statuses:
                    for status_obj in vm_instance_view.statuses:
                        if status_obj.code and status_obj.code.lower().startswith(
                            "powerstate/"
                        ):
                            actual_power_state = (
                                status_obj.display_status
                            )  # e.g., "VM deallocated"
                            break
                resource.meta["power_state"] = actual_power_state
                logger.info(
                    f"Azure VM {name} stopped/deallocated. Actual power state: {actual_power_state}"
                )
            except Exception as e_pv:
                logger.warning(
                    f"Could not fetch power state for Azure VM {name} after stop: {e_pv}"
                )
                resource.meta["power_state"] = "deallocated (assumed)"  # Fallback

            resource.state = ResourceState.STOPPED
            action = "azure_vm_stop_success"
            details = {
                "azure_vm_id": azure_vm_id,
                "final_state": resource.state.value,
                "power_state": resource.meta.get("power_state"),
            }
            logger.info(f"Azure VM {azure_vm_id} stop completed. State set to STOPPED.")

        except Exception as e:
            logger.error(f"Error stopping Azure VM {resource_id}: {e}", exc_info=True)
            if resource:
                resource.state = ResourceState.ERROR_STOPPING
                if resource.meta is None:
                    resource.meta = {}
                resource.meta["error_message"] = str(e)
                action = "azure_vm_stop_failure"
                details = {
                    "azure_vm_id": resource.meta.get("azure_vm_id"),
                    "error": str(e),
                    "final_state": resource.state.value,
                }
            else:
                action = "azure_vm_stop_failure_no_resource_in_exception"
                details = {"resource_id": resource_id, "error": str(e)}
        finally:
            if resource:
                session.add(resource)

            event_user_id = user_id
            event_project_id = resource.project_id if resource else None
            event_object_id = str(resource.id) if resource else resource_id

            if resource and "final_state" not in details:
                details["final_state"] = (
                    resource.state.value if resource.state else "unknown"
                )

            audit_event = AuditEvent(
                user_id=event_user_id,
                project_id=event_project_id,
                action=action,
                object_type="resource",
                object_id=event_object_id,
                details=details,
            )
            session.add(audit_event)
            session.commit()
    logger.info(f"Finished Azure VM stop task for resource_id: {resource_id}")
