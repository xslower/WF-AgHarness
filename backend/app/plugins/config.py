from __future__ import annotations

from typing import Any

from ..store import vault

pass
pass
MASKED = vault.MASKED

pass
_SEALED_TYPES = frozenset({"secret", "key"})

pass
CONFIG_TYPES = frozenset({"string", "text", "number", "boolean", "select",
                          "secret", "key", "path"})

pass
_DECL_KEYS = frozenset({"type", "label", "options", "required", "min", "max",
                        "placeholder", "default"})



class ConfigError(ValueError):
    pass


def normalize_config(items) -> list[dict]:
    if items is None:
        return []
    if not isinstance(items, dict):
        raise ConfigError(
            f"config 必须是映射（参数名: 默认值），不支持 {type(items).__name__} 写法")
    out: list[dict] = []
    for key, it in _config_rows(items):
        t = str(it.get("type") or _infer_type(it.get("default")))
        if t not in CONFIG_TYPES:
            raise ConfigError(f"config.{key} 的 type 不支持: {t}")
        pass
        row = {"key": key, "label": str(it.get("label") or key), "type": t}
        for k in ("default", "placeholder", "min", "max"):
            if k in it:
                row[k] = it[k]
        if isinstance(it.get("options"), list):
            row["options"] = [str(o) for o in it["options"]]
        if it.get("required"):
            row["required"] = True
        out.append(row)
    return out


pass
MAX_CONFIG_DEPTH = 3


def _config_rows(items: dict, prefix: str = "", depth: int = 1) -> list[tuple[str, dict]]:
    rows: list[tuple[str, dict]] = []
    for key, val in items.items():
        full = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(val, dict) and not (_DECL_KEYS & set(val)):
            if depth >= MAX_CONFIG_DEPTH:
                raise ConfigError(
                    f"config.{full} 嵌套超过 {MAX_CONFIG_DEPTH} 层"
                    f"（最多 `a.b.c`，再深就渲染不成配置项了）")
            rows.extend(_config_rows(val, full, depth + 1))
            continue
        if isinstance(val, (list, tuple)):
            raise ConfigError(
                f"config.{full} 是列表，配置只支持「参数名: 默认值」（列表没有对应控件）")
        if isinstance(val, dict):
            rows.append((full, val))
            continue
        rows.append((full, {"default": val}))
    return rows

def _infer_type(default) -> str:
    if isinstance(default, bool):
        return "boolean"
    if isinstance(default, (int, float)):
        return "number"
    return "string"


def coerce(spec: dict, raw: Any) -> Any:
    key = spec.get("key", "")
    t = spec.get("type", "string")
    if raw is None or raw == "":
        if spec.get("required"):
            raise ConfigError(f"配置项 {key} 必填")
        return spec.get("default")
    if t == "number":
        try:
            return float(raw) if "." in str(raw) else int(raw)
        except (TypeError, ValueError):
            raise ConfigError(f"配置项 {key} 必须是数字: {raw!r}")
    if t == "boolean":
        if isinstance(raw, bool):
            return raw
        return str(raw).strip().lower() in ("1", "true", "yes", "on")
    if t == "select":
        opts = spec.get("options") or []
        val = str(raw)
        if opts and val not in opts:
            raise ConfigError(f"配置项 {key} 只能是 {opts} 之一: {val!r}")
        return val
    return str(raw)


def validate(specs, values: dict) -> dict:
    out: dict = {}
    for spec in specs or ():
        key = spec.get("key")
        if not key:
            continue
        val = coerce(spec, (values or {}).get(key))
        if spec.get("type") == "number" and val is not None:
            lo, hi = spec.get("min"), spec.get("max")
            if lo is not None and val < lo:
                raise ConfigError(f"配置项 {key} 不能小于 {lo}: {val}")
            if hi is not None and val > hi:
                raise ConfigError(f"配置项 {key} 不能大于 {hi}: {val}")
        out[key] = val
    return out


def mask(specs, values: dict) -> dict:
    keys = {s.get("key") for s in specs or () if s.get("type") in _SEALED_TYPES}
    return {k: (MASKED if k in keys and v not in (None, "") else v)
            for k, v in (values or {}).items()}


pass
pass
pass
pass
pass
pass


def _file_store(pid: str, project: str):
    from . import homes
    return homes.config_json(pid, project)


def _read(path) -> dict:
    if path is None or not path.is_file():
        return {}
    from ..util import jsonx
    raw = jsonx.read_json(path, {})
    return raw.get("values") or {} if isinstance(raw, dict) else {}


def load(pid: str, project: str = "", specs=()) -> dict:
    from ..store import project_crypto
    path = _file_store(pid, project)
    if path is None:
        from ..store.plugin_config import PluginConfigStore
        raw = PluginConfigStore().get(pid, project)
    else:
        raw = {k: project_crypto.unseal_in(project, v)
               for k, v in _read(path).items()}
    if not specs:
        return raw
    return validate(specs, raw)



def save(pid: str, project: str, specs, values: dict) -> dict:
    incoming = dict(values or {})
    secret_keys = {s.get("key") for s in specs or ()
                   if s.get("type") in _SEALED_TYPES}
    if secret_keys:
        current = load(pid, project)
        for key in secret_keys:
            v = incoming.get(key)
            if v is None:
                if key in current:
                    incoming[key] = current[key]
                else:
                    incoming.pop(key, None)
                continue
            if v == MASKED or (isinstance(v, str) and not v.strip()):
                if key in current:
                    incoming[key] = current[key]
                else:
                    incoming[key] = ""
    clean = validate(specs, incoming)
    _write(pid, project, clean, secret_keys)
    return clean


def _write(pid: str, project: str, clean: dict, secret_keys: set) -> None:
    from ..store import project_crypto, vault
    path = _file_store(pid, project)
    if path is None:
        sealed = {k: (vault.seal(v) if k in secret_keys else v)
                  for k, v in clean.items()}
        from ..store.plugin_config import PluginConfigStore
        PluginConfigStore().put(pid, project, sealed)
        return
    from ..util import jsonx
    payload = {k: (project_crypto.seal_in(project, v) if k in secret_keys else v)
               for k, v in clean.items()}
    path.parent.mkdir(parents=True, exist_ok=True)
    jsonx.write_json(path, {"values": payload})


def masked(pid: str, project: str = "", specs=()) -> dict:
    raw = load(pid, project)
    values: dict = {}
    for spec in specs or ():
        key = spec.get("key")
        if not key:
            continue
        try:
            values[key] = coerce(spec, raw.get(key))
        except ConfigError:
            values[key] = spec.get("default", "")
    return {"values": mask(specs, values), "fields": list(specs or ())}


__all__ = ["ConfigError", "MASKED", "CONFIG_TYPES",
           "normalize_config", "coerce", "validate", "mask",
           "load", "save", "masked"]


pass
pass
pass
pass
pass
pass

def specs_of(installs, pid: str, project: str = "") -> tuple[dict, ...]:
    from . import package as pkgmod
    from . import tool_unit

    rec = installs.get_plugin(pid, project) or installs.get_plugin(pid, "")
    if rec is None:
        raise LookupError(f"未登记: {pid}")
    root, pkg = pkgmod.installed_view(rec, str(rec.get("project") or project))
    if root is not None and (root / tool_unit.TOOL_YAML).is_file():
        return tuple(tool_unit.from_dir(root).meta.get("config") or ())
    if pkg is None:
        raise ValueError(f"{pid} 的清单无法解析")
    return tuple(pkg.config)
