from __future__ import annotations

from fastapi import APIRouter, Depends

from ...config import Settings
from ..deps import Container, get_container

router = APIRouter()


@router.get("/api/config")
def get_config(c: Container = Depends(get_container)):
    from ...provider.meta import describe_model
    cfg = c.store.config
    providers = []
    for p in cfg.providers:
        pp = p.public_dict()
        for m in pp["models"]:
            m["description"] = describe_model(m["id"])
        providers.append(pp)
    return {"providers": providers, "queues": cfg.queues,
            "utility": cfg.utility, "settings": cfg.settings}


@router.put("/api/settings")
def put_settings(s: Settings, c: Container = Depends(get_container)):
    sent = s.model_dump(exclude_unset=True)
    cur = c.store.config.settings.model_dump()
    cur.update(sent)
    c.store.config.settings = Settings(**cur)
    c.store.save()
    c.sync_config("settings")
    return c.store.config.settings


@router.get("/api/usage")
def get_usage(c: Container = Depends(get_container)):
    aliases: dict[str, str] = {}
    prov_names: set[str] = set()
    for p in c.store.config.providers:
        prov_names.add(p.name)
        extra = getattr(p, "model_extra", None) or {}
        legacy = str(extra.get("_legacyId") or "") if isinstance(extra, dict) else ""
        if legacy and legacy != p.name:
            aliases[legacy] = p.name
    d = c.usage.summary(aliases=aliases)
    pass
    return d

