import pulumi
from cmp_core.lib.pulumi_adapter import register_provider
from cmp_core.models.resource import ResourceState
from pulumi import ResourceOptions
from pulumi_azure_native import compute, network, resources


@register_provider("azure")
def azure_handler(specs, pulumi_providers):
    for spec in specs:
        # 1) Resource Group
        rg = resources.ResourceGroup(
            f"{spec.name}-rg",
            resource_group_name=f"{spec.name}-rg",
            location=spec.meta["location"],
        )

        # 2) Virtual Network
        vnet = network.VirtualNetwork(
            f"{spec.name}-vnet",
            resource_group_name=rg.name,
            location=rg.location,
            address_space=network.AddressSpaceArgs(
                address_prefixes=[spec.meta["vnet_address_prefix"]],
            ),
        )

        # 3) Subnet
        subnet = network.Subnet(
            f"{spec.name}-subnet",
            resource_group_name=rg.name,
            virtual_network_name=vnet.name,
            address_prefix=spec.meta["subnet_prefix"],
        )

        # 4) Public IP
        pip = network.PublicIPAddress(
            f"{spec.name}-pip",
            resource_group_name=rg.name,
            location=rg.location,
            public_ip_allocation_method=spec.meta["public_ip_allocation_method"],
        )

        # 5) Network Interface
        nic = network.NetworkInterface(
            f"{spec.name}-nic",
            resource_group_name=rg.name,
            location=rg.location,
            ip_configurations=[
                network.NetworkInterfaceIPConfigurationArgs(
                    name=f"{spec.name}-ipcfg",
                    subnet=network.SubnetArgs(id=subnet.id),
                    private_ip_allocation_method="Dynamic",
                    public_ip_address=network.PublicIPAddressArgs(id=pip.id),
                )
            ],
        )

        # 6) Virtual Machine (import if existing)
        vm_opts = ResourceOptions()
        if spec.meta.get("azure_id"):
            vm_opts = ResourceOptions(import_=spec.meta["azure_id"])

        vm = compute.VirtualMachine(
            spec.name,
            resource_group_name=rg.name,
            location=rg.location,
            hardware_profile=compute.HardwareProfileArgs(
                vm_size=spec.meta["vm_size"],
            ),
            os_profile=compute.OSProfileArgs(
                computer_name=spec.name,
                admin_username=spec.meta["admin_username"],
                admin_password=spec.meta["admin_password"],
            ),
            storage_profile=compute.StorageProfileArgs(
                image_reference=compute.ImageReferenceArgs(
                    **spec.meta["image_reference"]
                ),
            ),
            network_profile=compute.NetworkProfileArgs(
                network_interfaces=[
                    compute.NetworkInterfaceReferenceArgs(
                        id=nic.id,
                        primary=True,
                    )
                ],
            ),
            opts=vm_opts,
        )

        # 7) Export for reconcile (ID and public IP)
        pulumi.export(f"{spec.name}-id", vm.id)
        pulumi.export(f"{spec.name}-ip", pip.ip_address)

        # 8) Export a simple status from the VM's instance view
        # Use the instance_view property of the vm resource itself
        # TODO: Properly map Azure's display_status (e.g., "VM running", "Provisioning succeeded") to your ResourceState enum values
        status = vm.instance_view.apply(
            lambda iv: (
                iv.statuses[1].display_status  # This is a string like "VM running"
                if iv
                and iv.statuses
                and len(iv.statuses) > 1
                and iv.statuses[1]
                and iv.statuses[1].display_status
                else ResourceState.PROVISIONING.value  # Default to provisioning if status not clear yet
            )
        )
        pulumi.export(f"{spec.name}-status", status)
