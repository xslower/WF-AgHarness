from __future__ import annotations

from .registry import ModelRegistry
from .spec import ModelSpec, SpecKind, queue_of


def effective_spec(config, raw: str | None) -> str:
    s = ModelSpec.parse(raw)
    if not (s.is_auto or s.is_queue):
        return s.raw
    qs = getattr(config, "queues", None)
    q = getattr(qs, queue_of(s.raw), None) or getattr(qs, "parent", None)
    return q[0] if q else ""


def check_spec(config, raw: str | None) -> tuple[str, str]:
    spec = (raw or "").strip()
    if not spec:
        return ("", "")
    s = ModelSpec.parse(spec)
    if s.is_queue:
        if not getattr(getattr(config, "queues", None), s.raw, None):
            return ("", f"{s.raw} 队列是空的，先在设置里加模型")
        return (spec, "")
    if s.kind is SpecKind.INVALID:
        return ("", f"模型标识格式不对：{spec!r}（应为 providerName/modelId）")
    entry = ModelRegistry(config).get(s)
    if entry is None:
        return ("", f"模型已不存在：{spec}（provider {s.provider} 下没有 {s.model}）")
    if getattr(entry.model, "disabled", False):
        return ("", f"模型已禁用：{spec}")
    return (spec, "")
