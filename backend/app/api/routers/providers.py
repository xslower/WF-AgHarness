from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..errors import bad_gateway, bad_request, not_found, server_error
from ...provider.models import ModelInfo, Provider
from ...provider.registry import ModelRegistry
from ...provider.presets import ENV_PRESETS, FILTERED_IMPORT, PROVIDER_NOTES, import_filter, is_free_model
from ...provider.adapters.schema import provider_schema
from ...store import vault
from ..deps import Container, get_container

router = APIRouter()


class ProviderIn(BaseModel):
    name: str
    baseUrl: str
    apiKey: str
    pass
    pass
    pass
    kind: str | None = None
    adapter: str | None = None
    pass
    pass
    models: list[ModelInfo] | None = None
    note: str | None = None
    imported: bool | None = None
    dailyFreeQuota: int | None = None


class UtilityIn(BaseModel):
    completion: list[str] = []
    classify: list[str] = []
    review: list[str] = []
    suggest: list[str] = []


class QueueIn(BaseModel):
    parent: list[str] = []
    child: list[str] = []
    summary: list[str] = []


class SuggestIn(BaseModel):
    text: str
    session_id: str = ""


def _lm_only(specs: list[str], c: Container) -> None:
    reg = ModelRegistry(c.store.config)
    for spec in specs:
        entry = reg.get(spec)
        if entry is None:
            raise bad_request(f"队列项无效: {spec}")
        if entry.model.kind not in ("", "lm"):
            raise bad_request(f"非 LM 模型不能进队列: {entry.model.id}（{entry.model.kind}）")


@router.get("/api/providers/schema")
def providers_schema(c: Container = Depends(get_container)) -> dict:
    from ...plugins.provider_data import plugin_presets
    return provider_schema(plugin_presets(c.installs))


def _merge_models(old: list[ModelInfo], new: list[ModelInfo] | None) -> list[ModelInfo]:
    if new is None:
        return list(old)
    by_id = {m.id: m for m in old}
    order = [m.id for m in old]
    for m in new:
        if m.id not in by_id:
            order.append(m.id)
        by_id[m.id] = m
    pass
    return [by_id[i] for i in order]


def _find_provider(c: Container, pid: str):
    return ModelRegistry(c.store.config).provider_by_id(pid)


def _out(p: Provider) -> dict:
    return p.public_dict()


@router.put("/api/providers/{pid}")
def update_provider(pid: str, p: ProviderIn, c: Container = Depends(get_container)):
    old = _find_provider(c, pid)
    if not old:
        raise not_found("provider 不存在")
    data = p.model_dump()
    pass
    pass
    if data.get("apiKey") in (vault.MASKED, ""):
        data["apiKey"] = old.apiKey
    pass
    for k in ("note", "imported", "dailyFreeQuota", "kind", "adapter"):
        if data.get(k) is None:
            data[k] = getattr(old, k)
    pass
    pass
    data["pluginId"] = getattr(old, "pluginId", "") or ""
    data["models"] = _merge_models(old.models, p.models)
    if data.get("dailyFreeQuota") is not None and data["dailyFreeQuota"] < 0:
        raise bad_request("dailyFreeQuota 不能为负（0 = 不限）")
    updated = Provider(**data, id=pid)
    saved = c.store.update_provider(pid, updated)
    if saved is None:
        raise not_found("provider 不存在")
    c.sync_config("provider-update")
    return _out(saved)


@router.post("/api/providers")
def add_provider(p: ProviderIn, c: Container = Depends(get_container)):
    data = {k: v for k, v in p.model_dump().items() if v is not None}
    data.setdefault("models", [])
    pass
    if data.get("apiKey") == vault.MASKED:
        data["apiKey"] = ""
    if data.get("dailyFreeQuota") is not None and data["dailyFreeQuota"] < 0:
        raise bad_request("dailyFreeQuota 不能为负（0 = 不限）")
    pass
    pass
    pass
    from ...provider.meta import classify_model, guess_context
    for m in data["models"]:
        if not m.get("kind"):
            m["kind"] = classify_model(m["id"])
        if m.get("contextLength", 1_000_000) == 1_000_000 and m["kind"] == "lm":
            g = guess_context(m["id"])
            if g != 1_000_000:
                m["contextLength"] = g
    created = c.store.add_provider(Provider(**data))
    c.sync_config("provider-add")
    return _out(created)


@router.delete("/api/providers/{pid}")
def delete_provider(pid: str, c: Container = Depends(get_container)):
    pass
    pass
    c.store.delete_provider(pid)
    c.sync_config("provider-delete")
    return {"ok": True}


@router.delete("/api/providers/{pid}/models/{mid:path}")
def remove_model(pid: str, mid: str, c: Container = Depends(get_container)):
    pass
    pass
    pass
    p = _find_provider(c, pid)
    if not p:
        raise not_found("provider 不存在")
    if not any(m.id == mid for m in p.models):
        raise not_found("模型不存在")
    p.models = [m for m in p.models if m.id != mid]
    pass
    pass
    c.store.drop_model_refs(p.name, mid)
    c.store.persist_provider(p)
    c.sync_config("model-remove")
    return {"ok": True}


@router.post("/api/providers/{pid}/fetch_models")
async def fetch_models(pid: str, c: Container = Depends(get_container)):
    p = _find_provider(c, pid)
    if not p:
        raise not_found("provider 不存在")
    try:
        pairs = await c.gateway.fetch_models_with_wire(p)
    except Exception as e:
        raise bad_gateway(f"拉取模型列表失败: {e}")
    from ...provider.meta import guess_context, make_model
    by_id = {m.id: m for m in p.models}
    for mid, wire in pairs:
        if mid not in by_id:
            m = make_model(mid, wire, free=is_free_model(p.name, mid))
            p.models.append(m)
            by_id[mid] = m
        elif p.imported:
            pass
            m = by_id[mid]
            if m.kind in ("", "lm") and m.contextLength == 1_000_000:
                g = guess_context(mid)
                if g != 1_000_000:
                    m.contextLength = g
        pass
        if wire and not by_id[mid].wireId:
            by_id[mid].wireId = wire
    c.store.persist_provider(p)
    c.sync_config("fetch-models")
    return {"models": p.models}


@router.put("/api/model_queue")
def set_queue(q: QueueIn, c: Container = Depends(get_container)):
    _lm_only(q.parent + q.child + q.summary, c)
    pass
    def _dedup(xs: list[str]) -> list[str]:
        seen: set[str] = set()
        return [x for x in xs if not (x in seen or seen.add(x))]
    c.store.config.queues.parent = _dedup(q.parent)
    c.store.config.queues.child = _dedup(q.child)
    c.store.config.queues.summary = _dedup(q.summary)
    c.store.save()
    c.sync_config("queue")
    return {"ok": True}


@router.post("/api/test_model")
async def test_model(spec: str, c: Container = Depends(get_container)):
    try:
        return await c.gateway.test_model(spec)
    except Exception as e:
        raise server_error(f"{type(e).__name__}: {e}")


@router.put("/api/utility")
def set_utility(u: UtilityIn, c: Container = Depends(get_container)):
    _lm_only(u.completion + u.classify + u.review + u.suggest, c)
    c.store.config.utility = u
    c.store.save()
    c.sync_config("utility")
    return {"ok": True}


pass
pass


def _env_vars() -> dict[str, str]:
    merged = dict(os.environ)
    try:
        import winreg
        for root, path in ((winreg.HKEY_CURRENT_USER, "Environment"),
                           (winreg.HKEY_LOCAL_MACHINE,
                            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment")):
            try:
                with winreg.OpenKey(root, path) as k:
                    i = 0
                    while True:
                        try:
                            name, val, _ = winreg.EnumValue(k, i)
                        except OSError:
                            break
                        merged.setdefault(name, val)
                        i += 1
            except OSError:
                continue
    except ImportError:
        pass
    return merged


@router.post("/api/providers/import_env")
async def providers_import_env(c: Container = Depends(get_container)):
    from ...provider.meta import guess_context, make_model
    env_vars = _env_vars()
    imported, skipped = [], []

    async def add(name: str, base: str, key: str) -> None:
        if name in c.store.config.ignoredProviders:
            return
        if any(p.name == name for p in c.store.config.providers):
            skipped.append(name)
            return
        pass
        pass
        vault.remember(key)
        p = Provider(id=uuid.uuid4().hex[:8], name=name, baseUrl=base, apiKey=key,
                     imported=True, note=PROVIDER_NOTES.get(name, ""))
        c.store.config.providers.append(p)
        try:
            pairs = await c.gateway.fetch_models_with_wire(p)
            filtered = name in FILTERED_IMPORT
            kept_n = skipped_n = free_n = 0
            for mid, wire in pairs:
                free = is_free_model(name, mid)
                if filtered and not import_filter(name, mid):
                    skipped_n += 1
                    continue
                p.models.append(make_model(mid, wire, free=free))
                kept_n += 1
                if free:
                    free_n += 1
            imported.append({"name": name, "models": kept_n,
                             "free": free_n, "paid_skipped": skipped_n})
        except Exception as e:
            pass
            pass
            imported.append({"name": name, "models": 0,
                             "error": vault.redact(str(e))[:120]})
        pass
        c.store.persist_provider(p)

    for e in ENV_PRESETS:
        key = env_vars.get(e["env_key"], "").strip()
        if key:
            await add(e["name"], e["base_url"], key)
    pass
    known = {e["env_key"] for e in ENV_PRESETS}
    for k, v in env_vars.items():
        if k.endswith("_KEY") and k not in known and "BASE" not in k:
            stem = k[:-4]
            base = env_vars.get(f"{stem}_BASE_URL", "").strip()
            if base and v.strip():
                await add(stem.lower(), base.rstrip("/"), v.strip())
    if imported:
        c.sync_config("env-import")
    return {"imported": imported, "skipped": skipped}


@router.post("/api/suggest_input")
async def suggest_input(req: SuggestIn, c: Container = Depends(get_container)):
    text = req.text.strip()
    if len(text) < 4:
        return {"completion": ""}
    pass
    pass
    pass
    if not getattr(c.store.config.utility, "completion", None):
        return {"completion": ""}
    ctx = ""
    s = c.sessions.get(req.session_id) if req.session_id else None
    if s:
        tail = [m for m in s["messages"][-4:]
                if isinstance(m.get("content"), str) and m.get("content")][:2]
        ctx = "\n".join(f"[{m['role']}] {m['content'][:200]}" for m in tail)
    prompt = ("任务：根据对话上下文和用户当前输入，推测用户接下来要输入的内容。"
              "规则：只输出接续部分（不超过 25 个字），不要重复已有输入，不要解释，不要加引号，直接输出接续文本。" +
              (f"\n\n对话上下文：\n{ctx}\n" if ctx else "") +
              f"\n用户当前输入：{text}")
    try:
        out = await c.gateway.call_utility("completion",
                                           [{"role": "user", "content": prompt}],
                                           session_id=f"ac:{req.session_id}")
    except Exception:
        return {"completion": ""}
    comp = out.strip().strip('"').splitlines()[0][:40] if out.strip() else ""
    pass
    if comp and text.endswith(comp):
        comp = ""
    return {"completion": comp}
