
from __future__ import annotations

from typing import Dict, Optional


class LLMProviderNotAllowed(ValueError):
    pass


def _family(provider: Optional[str]) -> str:
    return (provider or "").split("/")[0].lower()


def allowed_provider_families(config: Dict) -> set:
    cfg = config.get("llm", {}) or {}
    fams = {_family(p) for p in (cfg.get("allowed_providers") or [])}
    if cfg.get("provider"):
        fams.add(_family(cfg["provider"]))
    return {f for f in fams if f}


def resolve_llm(config: Dict, requested_provider: Optional[str] = None) -> Dict:
    from utils import get_llm_api_key, get_llm_base_url, get_llm_temperature

    default = config["llm"]["provider"]
    provider = requested_provider or default

    fams = allowed_provider_families(config)
    if fams and _family(provider) not in fams:
        raise LLMProviderNotAllowed("LLM provider not allowed")

    return {
        "provider": provider,
        "base_url": get_llm_base_url(config, provider),
        "api_token": get_llm_api_key(config, provider),
        "temperature": get_llm_temperature(config, provider),
    }
