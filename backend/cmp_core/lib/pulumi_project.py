# cmp_core/lib/pulumi_project.py

import importlib
import os
import pkgutil
from types import SimpleNamespace
from typing import Any, Dict, List

# ──────────────────────────────────────────────────────────────────────────────
# ensure every provider module under cmp_core.lib.providers is loaded,
# so their @register_provider(...) calls actually run:
import cmp_core.lib.providers  # the package
import pulumi
from cmp_core.core.config import settings
from cmp_core.lib.pulumi_adapter import all_handlers
from cmp_core.models.resource import ResourceState
from pulumi.automation import UpResult, create_or_select_stack

for _, modname, _ in pkgutil.iter_modules(cmp_core.lib.providers.__path__):
    importlib.import_module(f"cmp_core.lib.providers.{modname}")
# ──────────────────────────────────────────────────────────────────────────────


def _stack_name(project_id: str) -> str:
    return f"cmp-cloud-project-{project_id}-stack"


def _project_name() -> str:
    return "cmp-cloud-project"


def _inline_program(resources: List[Any]) -> None:
    """
    This gets run _inside_ Pulumi.  We group your SQLAlchemy Resource
    objects by provider, wrap them in a simple spec, then call each handler.
    """
    pulumi_providers: Dict[str, Any] = {}
    specs_by_provider: Dict[str, List[SimpleNamespace]] = {}

    # turn each Resource into a tiny ResourceSpec-like object
    for r in resources:

        # 🚨 If a resource is marked for deprovisioning (or is already being deprovisioned),
        # omit it from the program. Pulumi will see it's missing and plan a delete.
        if r.state in [ResourceState.PENDING_DEPROVISION, ResourceState.DEPROVISIONING]:
            pulumi.log.info(
                f"Omitting resource {r.name} from Pulumi program due to state: {r.state.value}"
            )
            continue

        # Also, if it's already terminated, don't try to manage it.
        if r.state == ResourceState.TERMINATED:
            pulumi.log.info(
                f"Skipping already terminated resource {r.name} in Pulumi program."
            )
            continue

        provider = getattr(r.provider, "value", r.provider)

        # sanitize region: reject empty or obviously wrong values (e.g. "t3.micro")
        region = r.region or ""

        spec = SimpleNamespace(
            provider=provider,
            name=r.name,
            region=region,
            meta=r.meta or {},
        )
        specs_by_provider.setdefault(provider, []).append(spec)

    # dispatch to each handler
    for provider_name, specs in specs_by_provider.items():
        handler = all_handlers().get(provider_name)
        if not handler:
            print(f"[pulumi_project] ⚠️  no handler for provider '{provider_name}'")
            continue
        print(
            f"[pulumi_project] 👷 calling handler '{provider_name}' with specs:", specs
        )
        handler(specs, pulumi_providers)


def up_project(project_id: str, resources: List[Any]) -> Dict[str, Any]:
    # ensure AWS creds in env
    os.environ.setdefault("AWS_ACCESS_KEY_ID", os.getenv("AWS_ACCESS_KEY_ID", ""))
    os.environ.setdefault(
        "AWS_SECRET_ACCESS_KEY", os.getenv("AWS_SECRET_ACCESS_KEY", "")
    )

    # ensure Azure creds in env for Pulumi (DefaultAzureCredential)
    os.environ.setdefault("ARM_CLIENT_ID", settings.azure_client_id)
    os.environ.setdefault("ARM_CLIENT_SECRET", settings.azure_client_secret)
    os.environ.setdefault("ARM_TENANT_ID", settings.azure_tenant_id)
    os.environ.setdefault("ARM_SUBSCRIPTION_ID", settings.azure_subscription_id)

    stack = create_or_select_stack(
        stack_name=_stack_name(project_id),
        project_name=_project_name(),
        program=lambda: _inline_program(resources),
    )

    # run a refresh so that any manually‐deleted resources get pruned
    try:
        print("⟳ refreshing Pulumi state to match real cloud")
        stack.refresh(on_output=print)
    except Exception as e:
        print("⚠️  pulumi refresh failed:", e)

    result: UpResult = stack.up(on_output=print)
    return {k: out.value for k, out in result.outputs.items()}


def destroy_project(project_id: str) -> None:
    """
    Tear down ALL resources in the stack for this project.
    """

    # ensure AWS creds in env
    os.environ.setdefault("AWS_ACCESS_KEY_ID", os.getenv("AWS_ACCESS_KEY_ID", ""))
    os.environ.setdefault(
        "AWS_SECRET_ACCESS_KEY", os.getenv("AWS_SECRET_ACCESS_KEY", "")
    )

    # ensure Azure creds in env for Pulumi (DefaultAzureCredential)
    os.environ.setdefault("ARM_CLIENT_ID", settings.azure_client_id)
    os.environ.setdefault("ARM_CLIENT_SECRET", settings.azure_client_secret)
    os.environ.setdefault("ARM_TENANT_ID", settings.azure_tenant_id)
    os.environ.setdefault("ARM_SUBSCRIPTION_ID", settings.azure_subscription_id)

    stack = create_or_select_stack(
        stack_name=_stack_name(project_id),
        project_name=_project_name(),
        program=lambda: None,  # no‐op program for destroy
    )
    stack.destroy(on_output=print)
