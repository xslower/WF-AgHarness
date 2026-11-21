
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..config import AppConfig, ModelInfo, Provider
from .spec import ModelSpec


@dataclass(frozen=True)
class ModelEntry:

    provider: Provider
    model: ModelInfo
    spec: str

    @property
    def label(self) -> str:
        return f"{self.provider.name} · {self.model.id}"


class ModelRegistry:

    def __init__(self, config: AppConfig | None) -> None:
        self.config = config

    pass

    def _providers(self) -> list[Provider]:
        return list(getattr(self.config, "providers", None) or [])

    def _find_provider(self, name: str) -> Optional[Provider]:
        if not name:
            return None
        for p in self._providers():
            if p.name == name:
                return p
        return None

    pass

    def get(self, spec: str | ModelSpec | None) -> Optional[ModelEntry]:
        s = spec if isinstance(spec, ModelSpec) else ModelSpec.parse(spec)
        if not s.is_model:
            return None
        p = self._find_provider(s.provider)
        if p is None:
            return None
        for m in p.models:
            if m.id == s.model:
                return ModelEntry(provider=p, model=m,
                                  spec=ModelSpec.of(p.name, m.id).raw)
        return None

    def model_of(self, spec: str | ModelSpec | None) -> Optional[ModelInfo]:
        e = self.get(spec)
        return e.model if e else None

    def provider_by_id(self, pid: str) -> Optional[Provider]:
        if not pid:
            return None
        for p in self._providers():
            if p.id == pid:
                return p
        return None

    def first_of_kind(self, kind: str, *, include_disabled: bool = False
                      ) -> Optional[ModelEntry]:
        for p in self._providers():
            for m in p.models:
                if include_disabled is False and getattr(m, "disabled", False):
                    continue
                if (getattr(m, "kind", "") or "") == kind:
                    return ModelEntry(provider=p, model=m,
                                      spec=ModelSpec.of(p.name, m.id).raw)
        return None

    def first_with_images(self, *, include_disabled: bool = False
                          ) -> Optional[ModelEntry]:
        for p in self._providers():
            for m in p.models:
                if include_disabled is False and getattr(m, "disabled", False):
                    continue
                if getattr(m, "supportsImages", False):
                    return ModelEntry(provider=p, model=m,
                                      spec=ModelSpec.of(p.name, m.id).raw)
        return None

    pass

    def unit_price(self, spec: str | ModelSpec | None) -> tuple[float, float]:
        m = self.model_of(spec)
        if m is None:
            return 0.0, 0.0
        return (float(getattr(m, "inputPrice", 0.0) or 0.0),
                float(getattr(m, "outputPrice", 0.0) or 0.0))
