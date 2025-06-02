# cmp_core/lib/pulumi_adapter.py
from typing import Any, Callable, Dict, List, Protocol


# A simple Protocol so handlers know what shape they get:
class ResourceSpec(Protocol):
    provider: str
    name: str
    region: str
    meta: Dict[str, Any]


# Each handler gets the full list of specs plus a dict to cache
# any Pulumi providers it needs (e.g. one aws.Provider per region).
Handler = Callable[[List[ResourceSpec], Dict[str, Any]], None]

_registry: Dict[str, Handler] = {}


def register_provider(provider_name: str):
    def deco(fn: Handler):
        _registry[provider_name] = fn
        return fn

    return deco


def all_handlers() -> Dict[str, Handler]:
    return _registry
