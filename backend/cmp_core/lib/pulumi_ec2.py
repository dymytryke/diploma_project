# cmp_core/lib/pulumi_ec2.py

import os
from typing import Any, Dict

import pulumi
import pulumi_aws as aws
from pulumi.automation import ConfigValue, UpResult, create_or_select_stack

_PROJECT_NAME = "cmp-aws-ec2"


def _stack_name(project_id: str) -> str:
    return f"{project_id}-aws-ec2"


def _inline_program(config: Dict[str, Any]) -> None:
    inst = aws.ec2.Instance(
        resource_name=config["name"],
        ami=config["ami"],
        instance_type=config["instance_type"],
        # no availability_zone here
        tags={"Name": config["name"]},
    )

    pulumi.export("aws_id", inst.id)
    pulumi.export("public_ip", inst.public_ip)
    pulumi.export("ami", inst.ami)
    pulumi.export("instance_type", inst.instance_type)
    # just export the string directly:
    pulumi.export("status", inst.instance_state)


def up_instance(project_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
    os.environ.setdefault("AWS_ACCESS_KEY_ID", os.getenv("AWS_ACCESS_KEY_ID", ""))
    os.environ.setdefault(
        "AWS_SECRET_ACCESS_KEY", os.getenv("AWS_SECRET_ACCESS_KEY", "")
    )

    stack = create_or_select_stack(
        stack_name=_stack_name(project_id),
        project_name=_PROJECT_NAME,
        program=lambda: _inline_program(config),
    )

    # tell Pulumi which region to use
    stack.set_config("aws:region", ConfigValue(value=config["region"]))

    result: UpResult = stack.up(on_output=print)
    return {k: out.value for k, out in result.outputs.items()}


def destroy_instance(project_id: str) -> None:
    os.environ.setdefault("AWS_ACCESS_KEY_ID", os.getenv("AWS_ACCESS_KEY_ID", ""))
    os.environ.setdefault(
        "AWS_SECRET_ACCESS_KEY", os.getenv("AWS_SECRET_ACCESS_KEY", "")
    )

    stack = create_or_select_stack(
        stack_name=_stack_name(project_id),
        project_name=_PROJECT_NAME,
        program=lambda: None,
    )
    stack.destroy(on_output=print)
