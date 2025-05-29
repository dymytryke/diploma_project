# cmp_core/lib/providers/aws.py
import pulumi
import pulumi_aws as aws
from cmp_core.lib.pulumi_adapter import register_provider
from cmp_core.models.resource import ResourceState
from pulumi import ResourceOptions


@register_provider("aws")
def aws_handler(resources, pulumi_providers):
    # bucket specs by region
    regions: dict[str, list] = {}
    for r in resources:
        if r.provider != "aws":
            continue
        regions.setdefault(r.region, []).append(r)

    for region, specs in regions.items():
        provider = pulumi_providers.setdefault(
            region,
            aws.Provider(f"aws-p-{region}", region=region),
        )

        for r in specs:
            if "ami" not in r.meta or "instance_type" not in r.meta:
                pulumi.log.warn(f"skipping {r.name!r}: missing ami/instance_type")
                continue

            if r.meta.get("aws_id"):
                # on first-ever apply this will import, thereafter Pulumi ignores import_
                opts = ResourceOptions(provider=provider, import_=r.meta["aws_id"])
            else:
                opts = ResourceOptions(provider=provider)

            inst = aws.ec2.Instance(
                resource_name=r.name,
                ami=r.meta["ami"],
                instance_type=r.meta["instance_type"],
                tags={"Name": r.name},
                opts=opts,
            )

            pulumi.export(f"{r.name}-id", inst.id)
            pulumi.export(f"{r.name}-ip", inst.public_ip)

            aws_to_our = {
                "pending": ResourceState.PROVISIONING,  # Use new state
                "running": ResourceState.RUNNING,  # Use new state
                "shutting-down": ResourceState.STOPPING,  # Use new state (or PENDING_DEPROVISION/DEPROVISIONING)
                "stopping": ResourceState.STOPPING,  # Use new state
                "stopped": ResourceState.STOPPED,  # Use new state
                "terminated": ResourceState.TERMINATED,  # Use new state
            }
            pulumi.export(
                f"{r.name}-status",
                inst.instance_state.apply(
                    lambda s: aws_to_our.get(
                        s, ResourceState.UNKNOWN
                    ).value  # Map to enum value, default to UNKNOWN
                ),
            )
