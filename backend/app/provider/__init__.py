from __future__ import annotations

from .ids import normalize_model_id, normalize_model_ids, normalize_pairs
from .models import ModelInfo, ModelQueues, ModelSchedule, Provider, TimeWindow, in_window, model_in_schedule
from .spec import QUEUE_NAMES, ModelSpec, SpecKind, queue_of

from .lazy import resolve

__all__ = [
    # spec
    "ModelSpec", "SpecKind", "queue_of", "QUEUE_NAMES",
    # ids
    "normalize_model_id", "normalize_model_ids", "normalize_pairs",
    # models
    "Provider", "ModelInfo", "ModelSchedule", "ModelQueues", "TimeWindow",
    "in_window", "model_in_schedule",
    # registry / availability / store / gateway（惰性）
    "ModelRegistry", "ModelEntry",
    "Availability", "AvailabilityChecker",
    "REASON_OK", "REASON_DISABLED", "REASON_SCHEDULE",
    "REASON_COOLING", "REASON_QUOTA",
    "ProviderStore", "ModelGateway", "Chunk", "Usage",
]


def __getattr__(name: str):
    return resolve(__name__, name, globals())


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
