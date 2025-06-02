# cmp_core/tasks/pulumi.py

import logging
import re

import boto3
from azure.core.exceptions import ResourceNotFoundError  # Import the specific exception
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
from sqlalchemy.orm import Session  # selectinload for eager loading if needed

logger = logging.getLogger(__name__)
MAX_THREADS = 10  # можна налаштувати через конфіг


# Helper function to map Azure power states to your ResourceState enum
def map_azure_power_state_to_resource_state(
    azure_power_state: str | None, current_db_state: ResourceState
) -> ResourceState:  # Added current_db_state
    if not azure_power_state:
        # If Azure has no power state, it might be an error or still pending.
        # Avoid overriding specific error states or in-progress states without more info.
        if current_db_state in [
            ResourceState.PROVISIONING,
            ResourceState.PENDING_PROVISION,
        ]:
            return (
                ResourceState.PROVISIONING
            )  # Or PENDING_PROVISION if you prefer to wait for explicit signal
        if current_db_state in [ResourceState.UPDATING, ResourceState.PENDING_UPDATE]:
            return ResourceState.UPDATING  # Or keep as is
        return ResourceState.UNKNOWN  # Default for unexpected lack of power state

    state_lower = azure_power_state.lower()

    if "running" in state_lower:  # e.g., "VM running"
        return ResourceState.RUNNING
    elif "deallocated" in state_lower:  # e.g., "VM deallocated"
        return ResourceState.STOPPED
    elif "starting" in state_lower:
        return ResourceState.STARTING  # Reflect Azure's view
    elif "stopping" in state_lower:
        return ResourceState.STOPPING  # Reflect Azure's view
    elif "deallocating" in state_lower:
        return ResourceState.STOPPING  # Or DEPROVISIONING if it's part of termination
    # Add more mappings if Azure has other relevant power states
    else:
        logger.warning(
            f"Unknown Azure power state encountered: {azure_power_state} for resource in DB state {current_db_state.value}"
        )
        # If in a stable state, but Azure reports something weird, mark as UNKNOWN or keep current.
        # If it was in an error state, probably keep it as error.
        if current_db_state.value.startswith("ERROR_"):
            return current_db_state
        return ResourceState.UNKNOWN


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


def parse_azure_vm_id(vm_id: str) -> tuple[str | None, str | None, str | None]:
    """
    Parses an Azure VM ID string into subscription ID, resource group name, and VM name.
    Example ID: /subscriptions/YOUR_SUB_ID/resourceGroups/YOUR_RG_NAME/providers/Microsoft.Compute/virtualMachines/YOUR_VM_NAME
    Returns (None, None, None) if parsing fails.
    """
    if not vm_id:
        return None, None, None
    match = re.search(
        r"/subscriptions/(?P<subscription_id>[^/]+)/resourceGroups/(?P<resource_group_name>[^/]+)/providers/Microsoft.Compute/virtualMachines/(?P<vm_name>[^/]+)",
        vm_id,
        re.IGNORECASE,
    )
    if match:
        return (
            match.group("subscription_id"),
            match.group("resource_group_name"),
            match.group("vm_name"),
        )
    logger.warning(f"Could not parse Azure VM ID with regex: {vm_id}")
    return None, None, None


def _get_rg_and_name_from_id(resource_id: str) -> tuple[str | None, str | None]:
    """
    Extracts resource group and resource name from a generic Azure resource ID.
    Assumes standard ID format: /.../resourceGroups/{RG}/providers/.../{TYPE}/{NAME}
    """
    if not resource_id:
        return None, None
    parts = resource_id.split("/")
    try:
        # Find 'resourceGroups' and get the next part as RG name
        # Then the last part is the resource name.
        rg_index = parts.index("resourceGroups")
        resource_group_name = parts[rg_index + 1]
        resource_name = parts[-1]
        return resource_group_name, resource_name
    except (ValueError, IndexError) as e:
        logger.warning(
            f"Could not parse RG and Name from resource ID '{resource_id}': {e}"
        )
        return None, None


def fetch_azure_info(
    vm_id_str: str,
    cred: DefaultAzureCredential,
    compute_clients: dict,
    network_clients: dict,
) -> dict:
    # Use the specific parser for VM ID to get subscription_id
    subscription_id, vm_resource_group_name, actual_vm_name_from_id = parse_azure_vm_id(
        vm_id_str
    )

    if not all([subscription_id, vm_resource_group_name, actual_vm_name_from_id]):
        logger.error(
            f"Failed to parse essential components from Azure VM ID: {vm_id_str} using parse_azure_vm_id."
        )
        return {}

    compute = compute_clients.setdefault(
        subscription_id, ComputeManagementClient(cred, subscription_id)
    )
    network = network_clients.setdefault(
        subscription_id, NetworkManagementClient(cred, subscription_id)
    )

    try:
        vm = compute.virtual_machines.get(
            vm_resource_group_name, actual_vm_name_from_id, expand="instanceView"
        )

        power_state = "unknown"  # Default
        if vm.instance_view and vm.instance_view.statuses:
            for status_obj in vm.instance_view.statuses:  # Renamed status to status_obj
                if status_obj.code and status_obj.code.lower().startswith(
                    "powerstate/"
                ):
                    power_state = (
                        status_obj.display_status
                    )  # Use display_status which is like "VM running"
                    break  # Found power state

        public_ip_address = None
        if vm.network_profile and vm.network_profile.network_interfaces:
            nic_ref = vm.network_profile.network_interfaces[0]  # Assuming first NIC
            if nic_ref.id:
                nic_rg, nic_name = _get_rg_and_name_from_id(nic_ref.id)
                if nic_rg and nic_name:
                    try:
                        nic = network.network_interfaces.get(nic_rg, nic_name)
                        if nic.ip_configurations:
                            ip_config = nic.ip_configurations[
                                0
                            ]  # Assuming first IP config
                            if (
                                ip_config.public_ip_address
                                and ip_config.public_ip_address.id
                            ):
                                pip_rg, pip_name = _get_rg_and_name_from_id(
                                    ip_config.public_ip_address.id
                                )
                                if pip_rg and pip_name:
                                    pip = network.public_ip_addresses.get(
                                        pip_rg, pip_name
                                    )
                                    public_ip_address = pip.ip_address
                    except Exception as e_pip:
                        logger.warning(
                            f"Could not fetch public IP for NIC {nic_name} in RG {nic_rg}: {e_pip}"
                        )
                else:
                    logger.warning(
                        f"Could not parse RG and Name from NIC ID: {nic_ref.id}"
                    )
        return {
            "azure_vm_id": vm.id,
            "actual_vm_name": vm.name,
            "power_state": power_state,  # This will be "VM running", "VM deallocated" etc.
            "public_ip": public_ip_address,
            "subscription_id": subscription_id,
            "resource_group_name": vm_resource_group_name,
            "location": vm.location,
        }
    except ResourceNotFoundError:
        logger.warning(
            f"Azure VM {actual_vm_name_from_id} in RG {vm_resource_group_name} (Sub: {subscription_id}) not found during fetch_azure_info."
        )
        raise
    except Exception as e:
        logger.error(
            f"Error fetching Azure VM info for {actual_vm_name_from_id} in RG {vm_resource_group_name}: {e}",
            exc_info=True,
        )
        return {}


def reconcile_single(
    resource: Resource,
    outputs: dict,  # Pulumi outputs
    ec2_clients: dict,
    azure_cred: DefaultAzureCredential,
    azure_compute_clients: dict,
    azure_network_clients: dict,
) -> tuple[Resource, AuditEvent] | None:
    meta = (resource.meta or {}).copy()
    original_db_state = (
        resource.state
    )  # This is the state *before* Pulumi ran (e.g., PROVISIONING)
    changed = False
    event_action = "reconcile_pulumi_sync"  # Default event action
    event_details = {"original_db_state": original_db_state.value}

    logger.info(
        f"Reconciling single resource: {resource.name} (ID: {resource.id}), original DB state: {original_db_state.value}"
    )

    # --- Handle DEPROVISIONING state ---
    if original_db_state == ResourceState.DEPROVISIONING:
        event_action = "deprovision_reconcile"
        # Check if Pulumi still reports the resource (it shouldn't if deletion was successful)
        # For AWS, if f"{resource.name}-id" is NOT in outputs, it's gone.
        # For Azure, if f"{resource.name}-id" is NOT in outputs, it's gone.
        # Pulumi's refresh step before `up` should handle drift where resource was manually deleted.

        resource_id_from_outputs = outputs.get(f"{resource.name}-id")

        if not resource_id_from_outputs:
            logger.info(
                f"Resource {resource.name} (deprovisioning) not found in Pulumi outputs. Marking as TERMINATED."
            )
            resource.state = ResourceState.TERMINATED
            meta["cloud_id"] = None  # Clear cloud specific ID
            if resource.provider.value == "aws":
                meta.pop("aws_id", None)
            if resource.provider.value == "azure":
                meta.pop("azure_vm_id", None)
            meta["public_ip"] = None
            changed = True
        else:
            # This case should ideally not happen if Pulumi `up` ran correctly for a delete.
            # It implies Pulumi failed to delete it.
            logger.error(
                f"Resource {resource.name} (deprovisioning) still found in Pulumi outputs. Marking as ERROR_DEPROVISIONING."
            )
            resource.state = ResourceState.ERROR_DEPROVISIONING
            changed = True

        resource.meta = meta
        event_details["final_db_state"] = resource.state.value
        event = AuditEvent(
            user_id=getattr(resource, "created_by", None),
            project_id=resource.project_id,
            action=event_action,
            object_type="resource",
            object_id=str(resource.id),
            details=event_details,
        )
        return resource, event

    # --- Standard reconciliation for PROVISIONING, UPDATING, or stable states ---
    cloud_id_from_outputs = outputs.get(f"{resource.name}-id")
    cloud_ip_from_outputs = outputs.get(f"{resource.name}-ip")
    # Pulumi might also output a status, but we prefer to fetch live status for accuracy
    # cloud_status_from_outputs = outputs.get(f"{resource.name}-status")

    if not cloud_id_from_outputs:
        event_details["pulumi_outputs_missing_id"] = True
        if original_db_state == ResourceState.DEPROVISIONING:
            logger.info(
                f"Resource {resource.name} (deprovisioning) not found in Pulumi outputs. Marking as TERMINATED."
            )
            resource.state = ResourceState.TERMINATED
            if resource.provider.value == "aws":
                meta.pop("aws_id", None)
            if resource.provider.value == "azure":
                meta.pop("azure_vm_id", None)
            meta.pop("cloud_id", None)  # Clear generic cloud_id if used
            meta["public_ip"] = None  # Clear public IP
            changed = True
            event_action = "deprovision_success_confirmed"
        elif original_db_state == ResourceState.TERMINATED:
            logger.info(
                f"Resource {resource.name} is already TERMINATED and not in Pulumi outputs. No state change."
            )
            # Ensure meta reflects a terminated state (IDs and IP are None/absent)
            # This part handles if meta somehow got inconsistent for a terminated resource.
            if resource.provider.value == "aws" and meta.get("aws_id") is not None:
                meta.pop("aws_id", None)
                changed = True
            if (
                resource.provider.value == "azure"
                and meta.get("azure_vm_id") is not None
            ):
                meta.pop("azure_vm_id", None)
                changed = True
            if meta.get("cloud_id") is not None:  # Generic cloud_id
                meta.pop("cloud_id", None)
                changed = True
            if meta.get("public_ip") is not None:
                meta["public_ip"] = None
                changed = True

            if not changed:  # If meta was already consistent for terminated state
                return None  # No update needed for the resource or audit event
        else:
            # Was PROVISIONING, UPDATING, or a stable/error state (but not TERMINATED or DEPROVISIONING)
            logger.error(
                f"Resource {resource.name} has no ID in Pulumi outputs. Original state: {original_db_state.value}. Marking as error."
            )
            if original_db_state == ResourceState.PROVISIONING:
                resource.state = ResourceState.ERROR_PROVISIONING
            elif original_db_state == ResourceState.UPDATING:
                resource.state = ResourceState.ERROR_UPDATING
            else:  # Was RUNNING, STOPPED, ERROR etc.
                resource.state = ResourceState.ERROR
                event_details["drift_detected"] = (
                    "Resource disappeared from Pulumi outputs unexpectedly."
                )
            changed = True

        resource.meta = meta
        event_details["final_db_state"] = resource.state.value
        event = AuditEvent(
            user_id=getattr(resource, "created_by", None),
            project_id=resource.project_id,
            action=event_action,
            object_type="resource",
            object_id=str(resource.id),
            details=event_details,
        )
        return resource, event

    # Update meta with basic Pulumi outputs if they changed
    if resource.provider.value == "aws":
        if meta.get("aws_id") != cloud_id_from_outputs:
            meta["aws_id"] = cloud_id_from_outputs
            changed = True
    elif resource.provider.value == "azure":
        if meta.get("azure_vm_id") != cloud_id_from_outputs:
            meta["azure_vm_id"] = cloud_id_from_outputs
            changed = True

    if (
        meta.get("public_ip") != cloud_ip_from_outputs
        and cloud_ip_from_outputs is not None
    ):  # Don't overwrite with None if already set
        meta["public_ip"] = cloud_ip_from_outputs
        changed = True

    # Fetch live status from cloud provider
    try:
        live_info = {}
        new_resource_state = ResourceState.UNKNOWN  # Default

        if resource.provider.value == "aws":
            client = ec2_clients.setdefault(
                resource.region, boto3.client("ec2", region_name=resource.region)
            )
            live_info = fetch_aws_info(
                client, cloud_id_from_outputs
            )  # cloud_id_from_outputs is aws_id

            # Update meta from live_info (AWS)
            if (
                live_info.get("public_ip")
                and meta.get("public_ip") != live_info["public_ip"]
            ):
                meta["public_ip"] = live_info["public_ip"]
                changed = True
            if (
                live_info.get("launch_time")
                and meta.get("launch_time") != live_info["launch_time"]
            ):
                meta["launch_time"] = live_info["launch_time"]
                changed = True

            # Determine new state based on live AWS state
            aws_state_str = live_info.get("state")
            if aws_state_str == "running":
                new_resource_state = ResourceState.RUNNING
            elif aws_state_str == "stopped":
                new_resource_state = ResourceState.STOPPED
            elif aws_state_str == "pending":
                new_resource_state = ResourceState.PROVISIONING  # Or STARTING
            elif aws_state_str == "stopping":
                new_resource_state = ResourceState.STOPPING
            elif aws_state_str == "shutting-down":
                new_resource_state = ResourceState.STOPPING  # Or DEPROVISIONING
            elif aws_state_str == "terminated":
                new_resource_state = ResourceState.TERMINATED
            else:
                new_resource_state = ResourceState.UNKNOWN

        elif resource.provider.value == "azure":
            live_info = fetch_azure_info(
                cloud_id_from_outputs,
                azure_cred,
                azure_compute_clients,
                azure_network_clients,
            )  # cloud_id_from_outputs is azure_vm_id

            # Update meta from live_info (Azure) - more detailed updates
            for key in [
                "actual_vm_name",
                "subscription_id",
                "resource_group_name",
                "location",
                "public_ip",
                "power_state",
            ]:
                fetched_val = live_info.get(key)
                # For public_ip, allow it to become None if Azure says so. For others, only update if fetched_val is not None.
                if key == "public_ip":
                    if meta.get(key) != fetched_val:
                        meta[key] = fetched_val
                        changed = True
                elif fetched_val is not None and meta.get(key) != fetched_val:
                    meta[key] = fetched_val
                    changed = True

            if live_info.get("location") and resource.region != live_info["location"]:
                resource.region = live_info["location"]
                changed = True

            live_cloud_state_str = live_info.get("power_state")  # e.g., "VM running"
            new_resource_state = map_azure_power_state_to_resource_state(
                live_cloud_state_str, original_db_state
            )
            event_details["live_azure_power_state"] = live_cloud_state_str

        else:
            new_resource_state = ResourceState.UNKNOWN  # Should not happen
            logger.error(
                f"Unknown provider {resource.provider.value} in reconcile_single for resource {resource.name}"
            )

        # State transition logic based on original_db_state and new_resource_state from cloud
        if original_db_state == ResourceState.PROVISIONING:
            if new_resource_state == ResourceState.RUNNING:
                resource.state = ResourceState.RUNNING
                event_action = "provision_success_confirmed"
            elif (
                new_resource_state == ResourceState.STOPPED
            ):  # e.g. created but stopped
                resource.state = ResourceState.STOPPED
                event_action = "provision_stopped_confirmed"
            else:
                resource.state = ResourceState.ERROR_PROVISIONING
                meta["error_message"] = (
                    f"Post-provisioning state is {new_resource_state.value}, expected RUNNING or STOPPED."
                )
                event_action = "provision_failure_unexpected_state"
            changed = True
        elif original_db_state == ResourceState.UPDATING:
            if new_resource_state == ResourceState.RUNNING:
                resource.state = ResourceState.RUNNING
                event_action = "update_success_confirmed_running"
            elif new_resource_state == ResourceState.STOPPED:
                resource.state = ResourceState.STOPPED
                event_action = "update_success_confirmed_stopped"
            else:
                resource.state = ResourceState.ERROR_UPDATING
                meta["error_message"] = (
                    f"Post-update state is {new_resource_state.value}, expected RUNNING or STOPPED."
                )
                event_action = "update_failure_unexpected_state"
            changed = True
        # --- AUTO-HEALING LOGIC FOR RUNNING INSTANCE FOUND STOPPED ---
        elif (
            original_db_state == ResourceState.RUNNING
            and new_resource_state == ResourceState.STOPPED
        ):
            logger.warning(
                f"Resource {resource.name} (DB state: RUNNING) found STOPPED in cloud. Triggering auto-start."
            )
            # Ensure audit_user_id is a string for the task signature
            audit_user_id = str(
                getattr(resource, "created_by", "system_reconciliation")
            )

            if resource.provider.value == "aws":
                from cmp_core.tasks.ec2 import start_ec2_task

                start_ec2_task.delay(str(resource.id), audit_user_id)
            elif resource.provider.value == "azure":
                from cmp_core.tasks.azure import (  # Assuming start_azure_task exists
                    start_azure_task,
                )

                start_azure_task.delay(str(resource.id), audit_user_id)
            else:
                logger.error(
                    f"Auto-healing: Unknown provider {resource.provider.value} for resource {resource.name} to start."
                )

            event_action = "reconcile_auto_heal_start_triggered"
            event_details["auto_heal_action"] = "start_triggered"
            event_details["cloud_state_detected"] = new_resource_state.value
            # DB state remains RUNNING (desired). Task will handle PENDING_START.
            changed = True  # Ensure audit event is created

        # --- AUTO-HEALING LOGIC FOR STOPPED INSTANCE FOUND RUNNING ---
        elif (
            original_db_state == ResourceState.STOPPED
            and new_resource_state == ResourceState.RUNNING
        ):
            logger.warning(
                f"Resource {resource.name} (DB state: STOPPED) found RUNNING in cloud. Triggering auto-stop."
            )
            # Ensure audit_user_id is a string for the task signature
            audit_user_id = str(
                getattr(resource, "created_by", "system_reconciliation")
            )

            if resource.provider.value == "aws":
                from cmp_core.tasks.ec2 import stop_ec2_task

                stop_ec2_task.delay(str(resource.id), audit_user_id)
            elif resource.provider.value == "azure":
                from cmp_core.tasks.azure import (  # Assuming stop_azure_task exists
                    stop_azure_task,
                )

                stop_azure_task.delay(str(resource.id), audit_user_id)
            else:
                logger.error(
                    f"Auto-healing: Unknown provider {resource.provider.value} for resource {resource.name} to stop."
                )

            event_action = "reconcile_auto_heal_stop_triggered"
            event_details["auto_heal_action"] = "stop_triggered"
            event_details["cloud_state_detected"] = new_resource_state.value
            # DB state remains STOPPED (desired). Task will handle PENDING_STOP.
            changed = True  # Ensure audit event is created

        elif (
            resource.state != new_resource_state
        ):  # General sync for other discrepancies
            logger.info(
                f"Resource {resource.name} state changing from {original_db_state.value} to {new_resource_state.value} based on live cloud state (general sync)."
            )
            resource.state = new_resource_state
            changed = True
            event_action = "reconcile_state_sync_from_cloud"

    except (
        ResourceNotFoundError
    ):  # Specifically for Azure if fetch_azure_info raises it
        logger.warning(
            f"Resource {resource.name} (ID: {cloud_id_from_outputs}) not found in cloud during live fetch. Marking as error."
        )
        resource.state = (
            ResourceState.ERROR
        )  # Or a more specific error like ERROR_PROVISIONING if original_db_state was PROVISIONING
        meta["cloud_id_status"] = "not_found_live"
        changed = True
    except Exception as e:
        logger.error(
            f"Error fetching live info for {resource.provider.value} resource {resource.name}: {e}",
            exc_info=True,
        )
        # Decide on error state based on original_db_state
        if original_db_state == ResourceState.PROVISIONING:
            resource.state = ResourceState.ERROR_PROVISIONING
        elif original_db_state == ResourceState.UPDATING:
            resource.state = ResourceState.ERROR_UPDATING
        else:
            resource.state = ResourceState.ERROR
        changed = True

    if not changed:
        logger.info(
            f"No changes detected for resource {resource.name} (ID: {resource.id}) after live fetch and state logic."
        )
        return None

    resource.meta = meta
    event_details["final_db_state"] = resource.state.value
    # Add more relevant meta to event_details if needed
    event_details.update(
        {
            k: meta[k]
            for k in ["public_ip", "aws_id", "azure_vm_id", "power_state"]
            if k in meta
        }
    )

    event = AuditEvent(
        user_id=getattr(resource, "created_by", None),
        project_id=resource.project_id,
        action=event_action,
        object_type="resource",
        object_id=str(resource.id),
        details=event_details,
    )
    return resource, event


@shared_task(name="cmp_core.tasks.reconcile_project")
def reconcile_project(project_id: str):
    logger.info(f"Start reconcile for project {project_id}")
    with SessionLocal() as session:
        try:
            resources_to_process = (
                session.query(Resource).filter_by(project_id=project_id).all()
            )
            if not resources_to_process:
                logger.info(
                    f"No resources found for project {project_id}. Skipping Pulumi up."
                )
                return

            # Update states to "in-progress" before calling Pulumi
            resources_for_pulumi_program = []
            for res in resources_to_process:
                if res.state == ResourceState.PENDING_PROVISION:
                    res.state = ResourceState.PROVISIONING
                    session.add(res)
                    logger.info(
                        f"Resource {res.name} state PENDING_PROVISION -> PROVISIONING"
                    )
                elif res.state == ResourceState.PENDING_UPDATE:
                    res.state = ResourceState.UPDATING
                    session.add(res)
                    logger.info(f"Resource {res.name} state PENDING_UPDATE -> UPDATING")
                elif res.state == ResourceState.PENDING_DEPROVISION:
                    res.state = ResourceState.DEPROVISIONING
                    session.add(res)
                    logger.info(
                        f"Resource {res.name} state PENDING_DEPROVISION -> DEPROVISIONING"
                    )

                # The _inline_program will skip DEPROVISIONING and TERMINATED states.
                # For other states (RUNNING, STOPPED, ERROR, PROVISIONING, UPDATING), they are included.
                if res.state not in [
                    ResourceState.TERMINATED
                ]:  # TERMINATED definitely skip
                    # Pass the state that Pulumi will see (e.g. PROVISIONING, not PENDING_PROVISION)
                    # We need to create a temporary representation or ensure _inline_program uses the current session's view
                    # For simplicity, let's assume _inline_program gets the updated state if we commit before up_project
                    # OR, pass a list of dicts/SimpleNamespace with the state set correctly.
                    # For now, let's assume the objects in resources_to_process reflect the new in-progress state.
                    resources_for_pulumi_program.append(res)

            session.commit()  # Commit state changes before calling Pulumi

            logger.info(
                f"Running Pulumi up for project {project_id} with {len(resources_for_pulumi_program)} relevant resources."
            )
            pulumi_outputs = up_project(
                project_id, resources_for_pulumi_program
            )  # Pass the filtered/state-updated list
            logger.info(
                f"Pulumi up finished for project {project_id}. Outputs: {pulumi_outputs}"
            )

            # Re-fetch resources to ensure we have the latest state from the DB after commit and before reconcile_single
            # This is important if reconcile_single runs much later or in a different context.
            # However, since we are in the same session block, resources_to_process should be fine.
            # For safety, one might re-query, but let's proceed with current objects.

            ec2_clients: dict = {}
            azure_cred = DefaultAzureCredential()
            azure_compute_clients: dict = {}
            azure_network_clients: dict = {}

            updated_resources_events = []
            for (
                resource_obj
            ) in (
                resources_to_process
            ):  # Iterate over all original resources for the project
                # The resource_obj here still has its state as it was *after* the pre-Pulumi update (e.g. PROVISIONING)
                # This state is used as `original_db_state` in `reconcile_single`
                logger.debug(
                    f"Preparing to call reconcile_single for {resource_obj.name}, state: {resource_obj.state.value}"
                )
                result = reconcile_single(
                    resource_obj,
                    pulumi_outputs,
                    ec2_clients,
                    azure_cred,
                    azure_compute_clients,
                    azure_network_clients,
                )
                if result:
                    updated_resources_events.append(result)

            if updated_resources_events:
                for res_to_save, event_to_save in updated_resources_events:
                    session.add(res_to_save)
                    session.add(event_to_save)
                session.commit()
                logger.info(
                    f"Committed {len(updated_resources_events)} resource/event updates after reconcile_single for project {project_id}."
                )
            else:
                logger.info(
                    f"No resource changes detected by reconcile_single for project {project_id}."
                )

        except Exception as e:
            logger.error(
                f"Error during reconcile_project for {project_id}: {e}", exc_info=True
            )
            # Potentially mark all "in-progress" resources for this project as ERROR here
            # For now, just log.
            session.rollback()  # Rollback any partial changes from this attempt
        finally:
            # Close any cloud clients if necessary (boto3 clients usually manage their own connections)
            pass

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
