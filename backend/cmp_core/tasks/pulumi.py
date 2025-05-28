# cmp_core/tasks/pulumi.py

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

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
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
MAX_THREADS = 10  # можна налаштувати через конфіг


# Helper function to map Azure power states to your ResourceState enum
def map_azure_power_state_to_resource_state(
    azure_power_state: str | None,
) -> ResourceState:
    if not azure_power_state:
        return (
            ResourceState.pending
        )  # Or error, depending on desired behavior for unknown

    state_lower = azure_power_state.lower()

    if state_lower == "running":
        return ResourceState.running
    elif state_lower == "deallocated":
        return ResourceState.stopped
    elif state_lower == "starting":
        return ResourceState.pending  # Or creating, if you prefer during startup phase
    elif state_lower == "stopping":
        return ResourceState.terminating  # Or a new "stopping" state if you add it
    elif state_lower == "deallocating":
        return ResourceState.terminating  # Or a new "stopping" state
    # Add more mappings if Azure has other relevant power states
    else:
        # For unknown or unhandled states, decide on a default.
        # 'pending' might be safe, or 'error' if it indicates an issue.
        logger.warning(f"Unknown Azure power state encountered: {azure_power_state}")
        return ResourceState.pending


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

        power_state = "unknown"
        if vm.instance_view and vm.instance_view.statuses:
            for status in vm.instance_view.statuses:
                if status.code and status.code.startswith("PowerState/"):
                    power_state = status.code.split("/")[-1]
                    break

        public_ip_address = None
        if vm.network_profile and vm.network_profile.network_interfaces:
            nic_ref = vm.network_profile.network_interfaces[0]  # Assuming first NIC
            if nic_ref.id:
                nic_rg, nic_name = _get_rg_and_name_from_id(nic_ref.id)
                if nic_rg and nic_name:
                    try:
                        nic = network.network_interfaces.get(nic_rg, nic_name)
                        if nic.ip_configurations:
                            ip_conf = nic.ip_configurations[
                                0
                            ]  # Assuming first IP config
                            if (
                                ip_conf.public_ip_address
                                and ip_conf.public_ip_address.id
                            ):
                                pip_id_str = ip_conf.public_ip_address.id
                                pip_rg, pip_name = _get_rg_and_name_from_id(pip_id_str)
                                if pip_rg and pip_name:
                                    try:
                                        pip = network.public_ip_addresses.get(
                                            pip_rg, pip_name
                                        )
                                        public_ip_address = pip.ip_address
                                    except Exception as e_pip:
                                        logger.warning(
                                            f"Could not get public IP '{pip_name}' in RG '{pip_rg}': {e_pip}"
                                        )
                    except Exception as e_nic:
                        logger.warning(
                            f"Could not get NIC '{nic_name}' in RG '{nic_rg}': {e_nic}"
                        )
                else:
                    logger.warning(
                        f"Could not parse RG and Name from NIC ID: {nic_ref.id}"
                    )

        return {
            "azure_vm_id": vm.id,
            "actual_vm_name": vm.name,
            "power_state": power_state,
            "public_ip": public_ip_address,
            "subscription_id": subscription_id,
            "resource_group_name": vm_resource_group_name,  # Use the RG name parsed from the VM ID
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
    outputs: dict,
    ec2_clients: dict,
    azure_cred: DefaultAzureCredential,
    azure_compute: dict,  # Renaming for clarity, this is azure_compute_clients
    azure_network: dict,  # Renaming for clarity, this is azure_network_clients
) -> tuple[Resource, AuditEvent] | None:
    meta = (resource.meta or {}).copy()
    original_db_state = resource.state
    original_region = resource.region  # For checking region drift
    changed = False
    event_action = "reconcile_status_update"
    logger.debug(
        f"Reconciling resource {resource.name} (ID: {resource.id}). Initial meta: {meta}"
    )

    # Azure VM
    if resource.provider.value == "azure":
        vm_id_from_outputs = outputs.get(f"{resource.name}-id")
        vm_id_from_meta = meta.get("azure_vm_id")
        # vm_id should be the full Azure Resource ID
        vm_id = vm_id_from_outputs or vm_id_from_meta

        # If the resource is marked for termination in our DB
        if original_db_state == ResourceState.terminating:
            event_action = "delete_reconcile"
            if not vm_id:
                logger.info(
                    f"Azure resource {resource.name} (state: {original_db_state.value}) marked terminating has no vm_id. Assuming deletion complete or never provisioned."
                )
                # If it's already 'terminated', no change. Otherwise, mark it.
                if resource.state != ResourceState.terminated:
                    resource.state = ResourceState.terminated  # Final state
                    changed = True
                if meta.get("power_state") != "deleted":
                    meta["power_state"] = "deleted"
                    changed = True
                if meta.get("public_ip") is not None:
                    meta["public_ip"] = None
                    changed = True
            else:
                try:
                    # Attempt to fetch info. A ResourceNotFoundError is the expected outcome.
                    fetch_azure_info(vm_id, azure_cred, azure_compute, azure_network)
                    # If FOUND, it's unexpected. Pulumi should have deleted it.
                    logger.warning(
                        f"Azure resource {resource.name} (ID: {vm_id}) is marked {original_db_state.value} but was still found in Azure. Deletion by Pulumi may have failed or is pending."
                    )
                    # Keep state as 'terminating' for next cycle. No 'changed' = True here unless meta needs sync.
                    return None  # Let next reconcile attempt it
                except ResourceNotFoundError:
                    logger.info(
                        f"Azure resource {resource.name} (ID: {vm_id}, state: {original_db_state.value}) confirmed deleted from Azure as expected."
                    )
                    event_action = "delete_confirmed"
                    if resource.state != ResourceState.terminated:
                        resource.state = ResourceState.terminated  # Final state
                        changed = True
                    if meta.get("power_state") != "deleted":
                        meta["power_state"] = "deleted"
                        changed = True
                    if meta.get("public_ip") is not None:
                        meta["public_ip"] = None
                        changed = True
                    # Optionally clear azure_vm_id from meta if it's truly gone and not needed for history
                    # if meta.get("azure_vm_id") is not None:
                    # meta["azure_vm_id"] = None
                    # changed = True
                except Exception as e:
                    logger.error(
                        f"Error during fetch for terminating Azure resource {resource.name} (ID: {vm_id}): {e}",
                        exc_info=True,
                    )
                    # Don't change state from terminating on unexpected error; let next cycle try.
                    return None

            if not changed:
                return None

            resource.meta = meta
            event_details = {
                "message": f"Resource deletion status: {event_action}",
                "final_db_state": resource.state.value,
                "final_meta_power_state": meta.get("power_state"),
                "azure_vm_id_processed": vm_id or "N/A",
            }
            event = AuditEvent(
                user_id=getattr(resource, "created_by", None),
                project_id=resource.project_id,
                action=event_action,
                object_type="resource",
                object_id=str(resource.id),
                details=event_details,
            )
            return resource, event

        # --- Standard reconciliation for active/pending resources ---
        if not vm_id:
            logger.warning(
                f"Azure resource {resource.name} (state: {original_db_state.value}) has no vm_id in outputs or meta. Cannot reconcile."
            )
            # If it's an active state but no ID, it might be an error or still creating
            if resource.state not in [ResourceState.pending, ResourceState.creating]:
                resource.state = ResourceState.error  # Or some other appropriate state
                meta["power_state"] = "unknown_id_missing"
                changed = True
            # else, leave as pending/creating
            if changed:  # only proceed if we actually marked it as error
                resource.meta = meta
                # Create event for this error state
                # ...
                return resource, AuditEvent(...)  # Simplified
            return None

        try:
            logger.debug(
                f"Calling fetch_azure_info for {resource.name} with vm_id: {vm_id}"
            )
            # Pass the client dictionaries correctly
            info = fetch_azure_info(vm_id, azure_cred, azure_compute, azure_network)
            logger.info(
                f"Fetched Azure info for {resource.name} (ID: {resource.id}): {info}"
            )

            if not info:
                logger.error(
                    f"fetch_azure_info returned empty for {resource.name}, vm_id: {vm_id}. Skipping update."
                )
                if resource.state != ResourceState.error:
                    resource.state = ResourceState.error
                    meta["power_state"] = "fetch_info_failed"
                    changed = True
                if changed:
                    resource.meta = meta
                    # Create and return event
                    return resource, AuditEvent(
                        user_id=getattr(resource, "created_by", None),
                        project_id=resource.project_id,
                        action="fetch_error",
                        object_type="resource",
                        object_id=str(resource.id),
                        details={"message": "Fetch info failed"},
                    )
                return None

        except ResourceNotFoundError:
            logger.warning(
                f"Azure resource {resource.name} (ID: {vm_id}, state: {original_db_state.value}) not found in Azure (drift). Marking as error."
            )
            event_action = "drift_deleted"
            if resource.state != ResourceState.error:
                resource.state = ResourceState.error
                changed = True
            if meta.get("power_state") != "deleted_drift":
                meta["power_state"] = "deleted_drift"
                meta["public_ip"] = None
                changed = True

            if not changed:
                return None
            resource.meta = meta
            return resource, AuditEvent(
                user_id=getattr(resource, "created_by", None),
                project_id=resource.project_id,
                action=event_action,
                object_type="resource",
                object_id=str(resource.id),
                details={"message": "Resource drifted and was deleted from cloud."},
            )
        except Exception as e:
            logger.error(
                f"Unhandled error during fetch_azure_info for active Azure resource {resource.name} (ID: {vm_id}): {e}",
                exc_info=True,
            )
            if resource.state != ResourceState.error:
                resource.state = ResourceState.error
                meta["power_state"] = "fetch_unhandled_error"
                changed = True
            if not changed:
                return None
            resource.meta = meta
            return resource, AuditEvent(
                user_id=getattr(resource, "created_by", None),
                project_id=resource.project_id,
                action="fetch_error_unhandled",
                object_type="resource",
                object_id=str(resource.id),
                details={"message": f"Unhandled fetch error: {str(e)}"},
            )

        # Update meta fields from fetched info
        # Ensure azure_vm_id in meta is the full ID from Azure if available
        fetched_azure_vm_id = info.get("azure_vm_id")
        if fetched_azure_vm_id and meta.get("azure_vm_id") != fetched_azure_vm_id:
            logger.debug(
                f"Updating meta.azure_vm_id for {resource.name} from '{meta.get('azure_vm_id')}' to '{fetched_azure_vm_id}'"
            )
            meta["azure_vm_id"] = fetched_azure_vm_id
            changed = True
        elif (
            vm_id_from_outputs and meta.get("azure_vm_id") != vm_id_from_outputs
        ):  # Fallback to output if fetch didn't provide one
            logger.debug(
                f"Updating meta.azure_vm_id for {resource.name} from Pulumi outputs to '{vm_id_from_outputs}'"
            )
            meta["azure_vm_id"] = vm_id_from_outputs
            changed = True

        # Update actual_vm_name, subscription_id, resource_group_name, location from info
        new_meta_values = {}
        for key in [
            "actual_vm_name",
            "subscription_id",
            "resource_group_name",
            "location",
        ]:
            fetched_val = info.get(key)
            # Ensure we only update if fetched_val is not None (or handle empty strings if needed)
            if fetched_val is not None and meta.get(key) != fetched_val:
                logger.debug(
                    f"Updating meta.{key} for {resource.name} from '{meta.get(key)}' to '{fetched_val}'"
                )
                new_meta_values[key] = fetched_val
                changed = True

        meta.update(new_meta_values)

        azure_location = info.get("location")
        if azure_location and resource.region != azure_location:
            logger.debug(
                f"Updating resource.region for {resource.name} from '{resource.region}' to '{azure_location}'"
            )
            resource.region = azure_location
            changed = True

        current_azure_power_state = info.get("power_state")
        fetched_public_ip = info.get("public_ip")  # Can be None if no IP

        # Handle public_ip update (allow setting to None if Azure has no IP)
        if (
            meta.get("public_ip") != fetched_public_ip
        ):  # This covers fetched_public_ip being None or a new IP
            logger.debug(
                f"Updating meta.public_ip for {resource.name} from '{meta.get('public_ip')}' to '{fetched_public_ip}'"
            )
            meta["public_ip"] = fetched_public_ip
            changed = True

        if (
            current_azure_power_state
            and meta.get("power_state") != current_azure_power_state
        ):
            logger.debug(
                f"Updating meta.power_state for {resource.name} from '{meta.get('power_state')}' to '{current_azure_power_state}'"
            )
            meta["power_state"] = current_azure_power_state
            changed = True

        if current_azure_power_state:
            new_resource_state = map_azure_power_state_to_resource_state(
                current_azure_power_state
            )
            if resource.state != new_resource_state:
                logger.debug(
                    f"Updating resource.state for {resource.name} from '{resource.state.value}' to '{new_resource_state.value}'"
                )
                resource.state = new_resource_state
                changed = True

        if not changed:
            logger.debug(
                f"No changes detected for resource {resource.name} (ID: {resource.id}) during reconciliation."
            )
            return None

        logger.info(
            f"Resource {resource.name} (ID: {resource.id}) changed. Final meta before return: {meta}"
        )
        resource.meta = meta
        event_details = {
            "original_db_state": original_db_state.value,
            "new_db_state": resource.state.value,
            "meta_power_state": meta.get("power_state"),
            "meta_public_ip": meta.get("public_ip"),
            "meta_azure_vm_id": meta.get("azure_vm_id"),
            "meta_actual_vm_name": meta.get("actual_vm_name"),
            "meta_subscription_id": meta.get("subscription_id"),
            "meta_resource_group_name": meta.get("resource_group_name"),
            "meta_location": meta.get("location"),
            "new_region": (
                resource.region if original_region != resource.region else None
            ),
        }
        event_details = {
            k: v for k, v in event_details.items() if v is not None
        }  # Clean None values
        event = AuditEvent(
            user_id=getattr(resource, "created_by", None),
            project_id=resource.project_id,
            action=event_action,
            object_type="resource",
            object_id=str(resource.id),
            details=event_details,
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
    # Use a non-nested session for the entire task if possible, or ensure proper session management per operation
    with SessionLocal() as session:
        try:
            resources = load_resources(session, project_id)
            # Ensure Azure credentials are set for Pulumi if not already globally configured
            # os.environ.setdefault("ARM_CLIENT_ID", settings.azure_client_id)
            # ... and other ARM_ variables ...
            outputs = up_project(
                project_id, resources
            )  # This calls Pulumi refresh and up

            ec2_clients: dict[str, boto3.client] = {}
            azure_cred = DefaultAzureCredential()  # Ensure this can acquire token
            azure_compute_clients: dict[str, ComputeManagementClient] = {}
            azure_network_clients: dict[str, NetworkManagementClient] = {}

            changed_resources_count = 0
            futures_map = {}  # For better error reporting if needed

            with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
                for r_item in resources:  # Use r_item to avoid conflict
                    # Detach resource from session for thread safety if it's going to be modified
                    # and then re-merged later. Or ensure reconcile_single gets all it needs
                    # and returns a "descriptor" of changes rather than the managed object itself.
                    # For now, we assume SessionLocal() within threads or careful handling.
                    # A simpler model for tasks is often to pass IDs and re-fetch in the thread/task.
                    future = executor.submit(
                        reconcile_single,
                        r_item,  # Pass the Resource object
                        outputs,
                        ec2_clients,
                        azure_cred,
                        azure_compute_clients,
                        azure_network_clients,
                    )
                    futures_map[future] = r_item.id

                for future in as_completed(futures_map):
                    resource_id_processed = futures_map[future]
                    try:
                        result = future.result()
                        if result:
                            # The 'resource' object returned by reconcile_single might be modified.
                            # We need to merge it back into the session.
                            updated_resource_obj, event_obj = result

                            # Re-attach or merge the updated_resource_obj into the current session
                            # This ensures SQLAlchemy tracks changes on objects associated with *this* session.
                            # If updated_resource_obj was fetched in a different session (it wasn't here, but common in other patterns),
                            # you'd need session.merge(updated_resource_obj).
                            # Since it's the same object modified, session.add() should work if it became detached or is new.
                            # If it's already in the session and modified, SQLAlchemy tracks it.
                            # For safety, let's ensure it's "active" in this session.

                            # Fetch the original resource from *this* session to apply updates
                            # This is safer if 'updated_resource_obj' might be from a different context
                            # or if we want to be explicit about which object is managed by 'session'.
                            # However, in this specific ThreadPoolExecutor setup, 'r_item' was from 'session'.
                            # So, 'updated_resource_obj' is the same 'r_item' instance.

                            # If 'updated_resource_obj' is the same instance as was in 'session.query(Resource)...all()',
                            # and it was modified, SQLAlchemy's identity map should handle it.
                            # session.add(updated_resource_obj) # If it was detached or to be sure
                            session.add(event_obj)
                            changed_resources_count += 1
                    except Exception as e:
                        logger.error(
                            f"Error processing reconcile_single for resource ID {resource_id_processed}: {e}",
                            exc_info=True,
                        )
                        # Decide if this should halt the commit or just log

            if changed_resources_count > 0:
                logger.info(
                    f"Committing changes for {changed_resources_count} resources in project {project_id}."
                )
                session.commit()
            else:
                logger.info(
                    f"No changes to commit for project {project_id} after reconciliation."
                )

        except Exception as e:
            logger.error(f"Reconcile project {project_id} failed: {e}", exc_info=True)
            session.rollback()  # Rollback on any top-level error in the try block
        finally:
            # Session is closed by 'with SessionLocal() as session:'
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
