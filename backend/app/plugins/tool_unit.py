from __future__ import annotations

import hashlib
import importlib.util
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("harness.plugin.tool_unit")

TOOL_YAML = "tool.yaml"

pass
pass
SCOPE_LOCAL = "local"
SCOPE_GLOBAL = "global"
pass
pass
pass
pass
pass
pass
_SCOPE_ALIASES = {
    "local": SCOPE_LOCAL, "project": SCOPE_LOCAL, "system": SCOPE_LOCAL,
    "global": SCOPE_GLOBAL,
}

pass
pass
pass
CASCADE_STANDALONE = "standalone"
CASCADE_SYSTEM_FIRST = "system_first"
CASCADE_PLUGIN_FIRST = "plugin_first"
_CASCADE_MODES = frozenset(
    {CASCADE_STANDALONE, CASCADE_SYSTEM_FIRST, CASCADE_PLUGIN_FIRST})

pass
_MODULE_CACHE: dict[tuple, object] = {}
_PATHS: set[str] = set()


@dataclass(frozen=True)
class ToolUnit:
    entry: Path
    is_dir: bool
    meta: dict = field(default_factory=dict)
    error: str = ""

    @property
    def name(self) -> str:
        return self.entry.parent.name if self.is_dir else self.entry.stem

    @property
    def root(self) -> Path:
        return self.entry.parent

    def extra(self) -> dict:
        out: dict = {}
        if self.is_dir:
            out["unit"] = "dir"
            for key in ("scope", "descs", "cascade"):
                if self.meta.get(key):
                    out[key] = self.meta[key]
        return out

    def fingerprint(self) -> tuple:
        if not self.is_dir:
            st = self.entry.stat()
            return ((str(self.entry), st.st_mtime, st.st_size),)
        files = sorted(p for p in self.root.rglob("*.py")
                       if p.is_file() and "__pycache__" not in p.parts)
        out = []
        for p in files:
            try:
                st = p.stat()
            except OSError:
                out.append((str(p), -1.0, -1))
                continue
            out.append((str(p), st.st_mtime, st.st_size))
        return tuple(out)
pass

def units_under(root: Path, *, strict: bool = True,
                with_config: bool = True) -> list[ToolUnit]:
    if not root.is_dir():
        return []
    out: dict[str, ToolUnit] = {}
    for p in sorted(root.glob("*.py")):
        if not p.name.startswith("."):
            out[p.stem] = from_file(p)
    for d in sorted(root.iterdir()):
        if not (d.is_dir() and not d.name.startswith(".")
                and (d / TOOL_YAML).is_file()):
            continue
        try:
            out[d.name] = from_dir(d, with_config=with_config)
        except (ValueError, OSError) as e:
            if strict:
                raise
            out[d.name] = _broken_unit(d, str(e), with_config=with_config)
    return [out[k] for k in sorted(out)]


def _broken_unit(d: Path, error: str, *, with_config: bool) -> ToolUnit:
    import yaml
    meta: dict = {"error": error}
    try:
        data = yaml.safe_load((d / TOOL_YAML).read_text("utf-8")) or {}
    except Exception:
        data = {}
    if isinstance(data, dict):
        for key in ("name", "desc", "version"):
            val = str(data.get(key) or "").strip()
            if val:
                meta[key] = val
        raw_scope = str(data.get("scope") or "").strip().lower()
        if _SCOPE_ALIASES.get(raw_scope):
            meta["scope"] = _SCOPE_ALIASES[raw_scope]
        entry = str(data.get("entry") or "").strip()
        if entry:
            meta["entry"] = entry
        pass
        if with_config:
            try:
                from .config import normalize_config
                meta["config"] = normalize_config(data.get("config") or None)
            except ValueError:
                meta["config"] = []
    entry_path = d / str(meta.get("entry") or TOOL_YAML)
    return ToolUnit(entry=entry_path, is_dir=True, meta=meta, error=error)


def discover(root: Path, name: str) -> ToolUnit | None:
    base = root.resolve()
    manifest = (base / name / TOOL_YAML).resolve()
    if manifest.is_relative_to(base) and manifest.is_file():
        return from_dir(manifest.parent)
    single = (base / f"{name}.py").resolve()
    if single.is_relative_to(base) and single.is_file():
        return from_file(single)
    return None


def from_file(p: Path) -> ToolUnit:
    return ToolUnit(entry=p.resolve(), is_dir=False)


def from_dir(d: Path, *, with_config: bool = True) -> ToolUnit:
    d = d.resolve()
    where = d / TOOL_YAML
    meta = parse_yaml(where.read_text("utf-8"), where, with_config=with_config)
    entry = (d / meta["entry"]).resolve()
    if not entry.is_relative_to(d) or entry.suffix != ".py" or not entry.is_file():
        raise ValueError(f"tool.yaml 的 entry 必须是目录内存在的 .py 文件: {where}")
    return ToolUnit(entry=entry, is_dir=True, meta=meta)


def from_row(entry: Path, extra: dict) -> ToolUnit:
    return ToolUnit(entry=entry, is_dir=str(extra.get("unit") or "") == "dir")


pass

def parse_yaml(raw: str, where: Path, *, with_config: bool = True) -> dict:
    import yaml
    try:
        data = yaml.safe_load(raw) or {}
    except Exception as e:
        raise ValueError(f"tool.yaml 解析失败: {where}: {e}") from e
    if not isinstance(data, dict):
        raise ValueError(f"tool.yaml 必须是映射: {where}")
    entry = str(data.get("entry") or "").strip().replace("\\", "/")
    parts = entry.split("/")
    if (not entry or entry.startswith("/")
            or any(part in ("", ".", "..") for part in parts)):
        raise ValueError(f"tool.yaml 缺少或非法的 entry（目录内相对路径）: {where}")
    if not entry.endswith(".py"):
        raise ValueError(f"tool.yaml 的 entry 必须是 .py 文件: {where}")
    raw_scope = str(data.get("scope") or "").strip().lower()
    scope = _SCOPE_ALIASES.get(raw_scope, "") if raw_scope else ""
    if raw_scope and not scope:
        raise ValueError(
            "tool.yaml 的 scope 非法（local / project / system = 项目内，"
            f"global = 全局）: {where}")
    from .config import normalize_config
    from .manifest import requested_provider_keys
    pass
    pass
    try:
        cfg = normalize_config(data.get("config") or None) if with_config else []
        cfg_err = ""
    except ValueError as e:
        cfg, cfg_err = [], str(e)
    return {"entry": entry, "scope": scope,
            "name": str(data.get("name") or "").strip(),
            "desc": str(data.get("desc") or "").strip(),
            "version": str(data.get("version") or "").strip(),
            "descs": _parse_tools(data.get("tools"), where),
            "config": cfg,
            "config_error": cfg_err,
            "requested_provider_keys": tuple(requested_provider_keys(
                data.get("requested_provider_keys") or [])),
            "cascade": _parse_cascade(data.get("cascade"), where)}


def _parse_tools(items, where: Path) -> dict[str, str]:
    if items is None:
        return {}
    if not isinstance(items, list):
        raise ValueError(f"tool.yaml 的 tools 必须是列表: {where}")
    out: dict[str, str] = {}
    for it in items:
        name = str(it.get("name") or "").strip() if isinstance(it, dict) else ""
        if not name:
            raise ValueError(f"tool.yaml 的 tools 每项都要有 name: {where}")
        desc = str(it.get("desc") or "").strip()
        if desc:
            out[name] = desc[:500]
    return out


def _parse_cascade(value, where: Path) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"tool.yaml 的 cascade 必须是映射: {where}")
    mode = str(value.get("mode") or CASCADE_STANDALONE).strip()
    if mode not in _CASCADE_MODES:
        raise ValueError("tool.yaml cascade.mode 非法（standalone / "
                         f"system_first / plugin_first）: {where}")
    target = str(value.get("target") or "").strip()
    if mode == CASCADE_STANDALONE:
        return {"mode": mode}
    if not target:
        raise ValueError(f"tool.yaml cascade.mode={mode} 需要 target（系统内现有工具名）: {where}")
    return {"mode": mode, "target": target}


pass

def drop_bytecode(src: Path) -> None:
    cache_dir = src.parent / "__pycache__"
    if not cache_dir.is_dir():
        return
    for pyc in cache_dir.glob(f"{src.stem}.*.pyc"):
        try:
            pyc.unlink()
        except OSError:
            logger.debug("删 .pyc 失败: %s", pyc, exc_info=True)


def _drop_unit_bytecode(unit: ToolUnit) -> None:
    files = ([unit.entry] if not unit.is_dir
             else [p for p in unit.root.rglob("*.py") if p.is_file()])
    for src in files:
        drop_bytecode(src)


def import_module(unit: ToolUnit, *, prefix: str, cached: bool = True):
    key = (prefix, unit.fingerprint())
    if cached and key in _MODULE_CACHE:
        return _MODULE_CACHE[key]
    pass
    _drop_unit_bytecode(unit)
    digest = hashlib.md5(str(unit.entry).encode("utf-8")).hexdigest()[:10]
    modname = f"{prefix}_{digest}"
    spec = importlib.util.spec_from_file_location(modname, unit.entry)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载插件工具: {unit.entry}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modname] = mod
    if unit.is_dir:
        _begin_import(unit)
    try:
        spec.loader.exec_module(mod)
    except Exception:
        sys.modules.pop(modname, None)
        raise
    if cached:
        _MODULE_CACHE[key] = mod
    return mod


def _begin_import(unit: ToolUnit) -> None:
    value = str(unit.root)
    if value not in _PATHS:
        _PATHS.add(value)
    else:
        sys.path.remove(value)
    sys.path.insert(0, value)
    for p in unit.root.glob("*.py"):
        if not p.name.startswith("."):
            sys.modules.pop(p.stem, None)


def reset_cache() -> None:
    _MODULE_CACHE.clear()


def reject_own_config(unit: "ToolUnit", pid: str) -> None:
    where = Path(unit.entry).parent / TOOL_YAML
    if not unit.is_dir or not where.is_file():
        return
    raw = parse_yaml(where.read_text("utf-8"), where, with_config=True)
    if raw.get("config"):
        raise ValueError(
            f"插件内工具 {unit.name} 的 tool.yaml 写了 config（插件 {pid}）—— "
            f"工具没有配置权：请写到插件包 plugin.yaml 的 config 段，"
            f"工具里用 reg.config('名字') 读（见 PLUGIN_DEV_GUIDE §3.1）")
