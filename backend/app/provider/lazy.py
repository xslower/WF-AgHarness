from __future__ import annotations

import importlib

pass
LAZY = {
    "ModelRegistry": "registry",
    "ModelEntry": "registry",
    "Availability": "availability",
    "AvailabilityChecker": "availability",
    "REASON_OK": "availability",
    "REASON_DISABLED": "availability",
    "REASON_SCHEDULE": "availability",
    "REASON_COOLING": "availability",
    "REASON_QUOTA": "availability",
    "ProviderStore": "store",
    "ModelGateway": "gateway",
    "Chunk": "gateway",
    "Usage": "gateway",
}


def resolve(package: str, name: str, cache: dict):
    mod = LAZY.get(name)
    if mod is None:
        raise AttributeError(f"module {package!r} has no attribute {name!r}")
    m = importlib.import_module(f".{mod}", package)
    value = getattr(m, name)
    cache[name] = value
    return value
