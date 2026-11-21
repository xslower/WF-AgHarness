from __future__ import annotations

import inspect
import json
import logging

logger = logging.getLogger("harness.tools.cascade")

pass
pass
CAPABILITIES = frozenset({"web", "asr", "ocr", "gen_image", "embed"})

pass
_ALIAS = {
    "generate_image": "gen_image",
    "image": "gen_image",
    "transcribe_audio": "asr",
    "embedding": "embed",
    "vectors": "embed",
}

_ORDERS = frozenset({"before", "after"})

pass
_PROVIDERS: dict[str, list[dict]] = {}


def normalize(capability: str) -> str:
    cap = _ALIAS.get(str(capability or "").strip(), str(capability or "").strip())
    if cap not in CAPABILITIES:
        raise ValueError(f"不支持级联的能力: {capability!r}"
                         f"（只支持 {', '.join(sorted(CAPABILITIES))}）")
    return cap


def register(capability: str, plugin_id: str, fn, order: str = "after") -> None:
    cap = normalize(capability)
    order = order if order in _ORDERS else "after"
    entries = _PROVIDERS.setdefault(cap, [])
    pass
    entries[:] = [e for e in entries if e["plugin_id"] != plugin_id]
    entries.append({"plugin_id": plugin_id, "fn": fn, "order": order})
    logger.debug("级联注册: %s <- %s（%s）", cap, plugin_id, order)


def providers(capability: str) -> list[dict]:
    try:
        cap = normalize(capability)
    except ValueError:
        return []
    entries = list(_PROVIDERS.get(cap, ()))
    return entries


def reset() -> None:
    _PROVIDERS.clear()


def is_failure(result) -> bool:
    if not isinstance(result, str):
        return False
    s = result.lstrip()
    if not s.startswith("{"):
        return False
    try:
        obj = json.loads(s)
    except ValueError:
        return False
    if not isinstance(obj, dict):
        return False
    if obj.get("ok") is False:
        return True
    return bool(obj.get("error"))


def _call_args(fn, args: dict, ctx) -> tuple[dict, bool]:
    try:
        params = inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return dict(args), False
    var_kw = any(p.kind == p.VAR_KEYWORD for p in params.values())
    if var_kw:
        kwargs = dict(args)
    else:
        kwargs = {k: v for k, v in args.items() if k in params}
    return kwargs, ("ctx" in params or var_kw)


async def _invoke(fn, args: dict, ctx) -> str:
    try:
        kwargs, need_ctx = _call_args(fn, args, ctx)
        if need_ctx:
            kwargs["ctx"] = ctx
        result = fn(**kwargs)
        if inspect.isawaitable(result):
            result = await result
        return result if isinstance(result, str) else json.dumps(
            result, ensure_ascii=False)
    except Exception as e:
        logger.debug("级联实现失败: %s: %s", getattr(fn, "__name__", fn), e,
                     exc_info=True)
        return json.dumps({"error": f"{type(e).__name__}: {e}"},
                          ensure_ascii=False)


async def _system(system_fn) -> str:
    try:
        result = system_fn()
        if inspect.isawaitable(result):
            result = await result
        return result if isinstance(result, str) else json.dumps(
            result, ensure_ascii=False)
    except Exception as e:
        logger.debug("系统实现失败: %s", e, exc_info=True)
        return json.dumps({"error": f"{type(e).__name__}: {e}"},
                          ensure_ascii=False)


async def run(capability: str, args: dict, ctx, system_fn):
    entries = providers(capability)
    if not entries:
        return await _system(system_fn)

    before = [e for e in entries if e["order"] == "before"]
    after = [e for e in entries if e["order"] != "before"]
    last = None
    for entry in before:
        last = await _invoke(entry["fn"], args, ctx)
        if not is_failure(last):
            return last
    last = await _system(system_fn)
    if not is_failure(last):
        return last
    for entry in after:
        last = await _invoke(entry["fn"], args, ctx)
        if not is_failure(last):
            return last
    return last
