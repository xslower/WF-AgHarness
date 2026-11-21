from __future__ import annotations

from dataclasses import dataclass, field

from pathlib import Path

from ..store import layout
from ..util import pathx
from . import bot_manifest, config as plugin_config, manifest

pass
pass
pass
MODE_DEV = "dev"
MODE_RELEASE = "release"
_MODES = frozenset({MODE_DEV, MODE_RELEASE})

pass
pass
pass
pass
pass
SCOPE_INTERNAL = "internal"
SCOPE_SYSTEM = "system"
pass
pass
SCOPE_GLOBAL = "global"
_CAP_SCOPES = frozenset({SCOPE_INTERNAL, SCOPE_SYSTEM, SCOPE_GLOBAL})
pass
pass
pass
pass
_CAP_SCOPE_ALIASES = {"internal": SCOPE_INTERNAL, "system": SCOPE_SYSTEM,
                      "local": SCOPE_SYSTEM, "project": SCOPE_SYSTEM,
                      SCOPE_GLOBAL: SCOPE_GLOBAL}
pass
_PLUGIN_TO_TOOL_SCOPE = {SCOPE_INTERNAL: "local", SCOPE_SYSTEM: "local",
                         SCOPE_GLOBAL: "global"}

pass
pass
pass
GLOBAL_KINDS = frozenset({"theme", "provider", "outbound_switch"})

KNOWN_KINDS = frozenset({
    "theme", "provider", "agent_profile", "workflow", "skill_bundle",
    "mcp_server", "tool", "api", "outbound_switch", "bot",
})

pass
_CONFIG_TYPES = plugin_config.CONFIG_TYPES

_ID_OK = set("abcdefghijklmnopqrstuvwxyz0123456789._-")

pass
pass
PLUGIN_YAML = "plugin.yaml"

pass
_KIND_DIRS = {
    "workflow": "workflows", "skill_bundle": "skills",
    "tool": "tools", "api": "api", "agent_profile": "agents",
    "outbound_switch": "outbound",
}


@dataclass
class PluginPackage:

    root: Path
    id: str
    name: str
    version: str
    kinds: tuple[str, ...]
    desc: str = ""
    entry: str = "index.html"
    config: tuple[dict, ...] = ()
    pass
    pass
    pass
    pass
    config_error: str = ""
    providers: tuple[dict, ...] = ()
    pass
    pass
    pass
    outbound_switches: tuple[dict, ...] = ()
    pass
    requested_provider_keys: tuple[str, ...] = ()
    raw: str = ""
    pass
    mode: str = ""
    pass
    pass
    bot: dict = field(default_factory=dict)
    pass
    tools: tuple[dict, ...] = ()
    skills: tuple[dict, ...] = ()

    @property
    def global_tools(self) -> bool:
        return any(cap.get("scope") == SCOPE_GLOBAL
                   for cap in self.tools) and "tool" in self.kinds

    @property
    def needs_project(self) -> bool:
        if self.global_tools and set(self.kinds) == {"tool"}:
            pass
            return False
        return any(k not in GLOBAL_KINDS for k in self.kinds)

    @property
    def is_dev(self) -> bool:
        return self.mode == MODE_DEV


def is_package_dir(path: str | Path) -> bool:
    return (Path(path) / PLUGIN_YAML).is_file()


def load_package(root: str | Path) -> PluginPackage:
    p = Path(root).expanduser()
    if not p.is_dir():
        raise ValueError(f"插件包目录不存在: {p}")
    yaml_path = p / PLUGIN_YAML
    if not yaml_path.is_file():
        raise ValueError(f"缺少 plugin.yaml: {p}")
    raw = yaml_path.read_text("utf-8")
    data = _parse_yaml(raw, p)
    pid = str(data.get("id") or "").strip()
    if not _valid_id(pid):
        raise ValueError(f"插件 id 非法（只允许小写字母/数字/._-，长度 2-64）: {pid!r}")
    return _build(data, raw, p, pid, root=p)


def load_package_from_text(raw: str, plugin_id: str) -> PluginPackage:
    where = Path(f"<installed:{plugin_id}>")
    return _build(_parse_yaml(raw, where), raw, where, plugin_id, root=Path())


def _build(data: dict, raw: str, where: Path, pid: str, *,
           root: Path) -> PluginPackage:
    cfg, cfg_err = _config_or_error(data.get("config"), where)
    kinds = _parse_kinds(data, where)
    return PluginPackage(
        root=root,
        id=pid,
        name=str(data.get("name") or pid),
        version=str(data.get("version") or "0.0.0"),
        kinds=kinds,
        desc=str(data.get("desc") or ""),
        entry=_normalize_entry(data.get("entry")),
        config=cfg,
        config_error=cfg_err,
        providers=tuple(manifest.providers(data.get("providers") or [])),
        outbound_switches=tuple(manifest.outbound_switches(
            data.get("outbound_switches") or [])),
        requested_provider_keys=tuple(manifest.requested_provider_keys(
            data.get("requested_provider_keys") or [])),
        raw=raw,
        mode=_parse_mode(data, where),
        bot=bot_manifest.parse_bot(data.get("bot"), where, kinds),
        tools=tuple(_normalize_capabilities(data.get("tools"), "tools", where)),
        skills=tuple(_normalize_capabilities(data.get("skills"), "skills", where)),
    )


pass
pass
pass
def meta_of(pkg: PluginPackage) -> dict:
    return {"id": pkg.id, "name": pkg.name, "version": pkg.version,
            "kinds": list(pkg.kinds), "mode": pkg.mode, "desc": pkg.desc,
            "requestedProviderKeys": list(pkg.requested_provider_keys),
            **({"config_error": pkg.config_error} if pkg.config_error else {})}


def installed_view(rec: dict, project: str = "") -> tuple[Path | None, "PluginPackage | None"]:
    from . import location
    root: Path | None = None
    try:
        root = location.resolve_package(rec, project)
        return root, load_package(root)
    except (ValueError, OSError, TypeError):
        pass
    manifest = rec.get("manifest")
    if manifest:
        try:
            return root, load_package_from_text(str(manifest), str(rec.get("id") or ""))
        except (ValueError, OSError, TypeError):
            pass
    return root, None


def _parse_yaml(raw: str, p: Path) -> dict:
    try:
        import yaml
        data = yaml.safe_load(raw) or {}
    except Exception as e:
        raise ValueError(f"plugin.yaml 解析失败: {p}: {e}") from e
    if not isinstance(data, dict):
        raise ValueError(f"plugin.yaml 必须是映射: {p}")
    return data


def _parse_mode(data: dict, p: Path) -> str:
    mode = str(data.get("mode") or "").strip()
    if mode not in _MODES:
        raise ValueError(f"plugin.yaml 缺少或非法的 mode（只能是 dev / release）: {p}")
    return mode


def _normalize_capabilities(items, section: str, p: Path) -> list[dict]:
    if not isinstance(items, list):
        return []
    out: list[dict] = []
    for it in items:
        if not isinstance(it, dict) or not it.get("name"):
            continue
        raw = str(it.get("scope") or SCOPE_SYSTEM).strip().lower()
        scope = _CAP_SCOPE_ALIASES.get(raw, "")
        if not scope:
            raise ValueError(f"plugin.yaml {section}.{it['name']} 的 scope 非法"
                             f"（只能 internal / system / global，"
                             f"也接受 tool.yaml 的 local / project）: {p}")
        if scope == SCOPE_GLOBAL and section != "tools":
            raise ValueError(f"plugin.yaml {section}.{it['name']}：global 只支持 tools: {p}")
        out.append({"name": str(it["name"]), "scope": scope})
    return out


def _parse_kinds(data: dict, p: Path) -> tuple[str, ...]:
    pass
    pass
    kinds = data.get("kinds") or []
    if isinstance(kinds, str):
        kinds = [kinds]
    kinds = tuple(str(k).strip() for k in kinds if str(k).strip())
    if not kinds:
        raise ValueError(f"plugin.yaml 缺少 kinds: {p}")
    unknown = [k for k in kinds if k not in KNOWN_KINDS]
    if unknown:
        raise ValueError(f"未知 kind: {', '.join(unknown)}"
                         f"（可选 {', '.join(sorted(KNOWN_KINDS))}）")
    return kinds


def _normalize_entry(value) -> str:
    rel = str(value or "index.html").replace("\\", "/").lstrip("/")
    if not rel or any(part in ("", ".", "..") for part in rel.split("/")):
        raise ValueError(f"plugin.yaml 的 entry 非法（必须是包内相对路径）: {value!r}")
    return rel


def _valid_id(pid: str) -> bool:
    return (2 <= len(pid) <= 64 and pid[0] in "abcdefghijklmnopqrstuvwxyz0123456789"
            and all(c in _ID_OK for c in pid))


def _config_or_error(items, where) -> tuple[tuple[dict, ...], str]:
    try:
        return tuple(plugin_config.normalize_config(items or None)), ""
    except ValueError as e:
        return (), f"{where}: {e}"


pass

pass
_NO_FILE_KINDS = frozenset({"provider", "bot"})


def plan_registrations(pkg: PluginPackage, project: str) -> list[dict]:
    from . import location

    pass
    pass
    pass
    pass
    pass
    pass
    pass
    if pkg.global_tools and pkg.needs_project:
        raise ValueError(
            f"插件 {pkg.id} 同时声明了全局工具（scope: global）和项目类 kind"
            f"（{', '.join(pkg.kinds)}）—— 全局与项目作用域不能共存，"
            f"把它拆成两个包")
    if pkg.global_tools:
        if project:
            raise ValueError(f"插件 {pkg.id} 声明了全局工具，不能装到项目里")
        location.require_in_data(pkg.root)
    elif pkg.needs_project and not layout.is_project(pathx.project_dir(project)):
        raise ValueError(f"插件 {pkg.id} 含项目类 kind（{', '.join(pkg.kinds)}），"
                         f"必须指定已登记的项目")
    elif not pkg.needs_project:
        location.require_in_data(pkg.root)
    else:
        location.require_in_project(pkg.root, project)
    for kind in pkg.kinds:
        if kind in GLOBAL_KINDS and pkg.needs_project:
            raise ValueError(f"全局型 kind={kind} 在项目包里不支持（§2）")

    plan: list[dict] = []
    for kind in pkg.kinds:
        if kind in _NO_FILE_KINDS:
            continue
        if kind == "mcp_server":
            pass
            pass
            pass
            planned = False
            for p in _files_under(pkg.root / "mcp"):
                if p.suffix != ".json":
                    continue
                servers = _mcp_servers(p)
                if servers:
                    plan.append(_row(kind, p, project, {"servers": servers}))
                    planned = True
            if not planned:
                src = pkg.root / layout.MCP_JSON
                if src.is_file():
                    plan.append(_row(kind, src, project,
                                     {"servers": _mcp_servers(src)}))
            continue
        if kind == "theme":
            for p in _files_under(pkg.root / "themes"):
                plan.append(_row(kind, p, project))
            continue
        sub = _KIND_DIRS.get(kind)
        if not sub:
            continue
        declared = (pkg.tools if kind == "tool"
                    else pkg.skills if kind == "skill_bundle" else None)
        if kind == "tool":
            pass
            pass
            plan.extend(_plan_tools(pkg, project, sub, declared))
            continue
        pass
        for p in _files_under(pkg.root / sub):
            if declared is not None:
                cap = _match_declared(p, declared, sub)
                if cap is None:
                    continue
            pass
            pass
            pass
            if kind in ("api", "outbound_switch") and p.suffix != ".py":
                continue
            extra = _kind_extra(kind, p, pkg, sub)
            if declared is not None:
                extra["scope"] = cap["scope"]
            if kind == "outbound_switch":
                decl = next((d for d in pkg.outbound_switches
                             if d["setup"] == p.stem), None)
                if decl is None:
                    continue
                extra.update({"provider": decl["provider"],
                              "handler": decl["handler"],
                              "setup": decl["setup"]})
            plan.append(_row(kind, p, project, extra))
    pass
    pass
    if "outbound_switch" in pkg.kinds:
        setup_file = pkg.root / "provider.py"
        if setup_file.is_file():
            plan.append(_row("provider_setup", setup_file, project,
                             {"handler": "provide"}))
    return plan


def _plan_tools(pkg: PluginPackage, project: str, sub: str,
                declared) -> list[dict]:
    from . import tool_unit
    rows: list[dict] = []
    for unit in tool_unit.units_under(pkg.root / sub, strict=False,
                                       with_config=False):
        cap = None
        if declared is not None:
            cap = _match_declared(Path(unit.name + ".py"), declared, sub)
            if cap is None:
                continue
        if unit.error:
            raise ValueError(f"工具 {unit.name} 的 tool.yaml 无效（插件 {pkg.id}）: {unit.error}")
        tool_unit.reject_own_config(unit, pkg.id)
        extra = unit.extra()
        scope = cap["scope"] if cap else SCOPE_SYSTEM
        _check_tool_scope(unit, scope, pkg.id)
        extra["scope"] = scope
        rows.append(_row("tool", unit.entry, project, extra))
    return rows


def _check_tool_scope(unit, scope: str, pid: str) -> None:
    declared = str((unit.meta or {}).get("scope") or "")
    if not declared:
        return
    effective = _PLUGIN_TO_TOOL_SCOPE.get(scope)
    if effective is None or declared != effective:
        raise ValueError(
            f"工具 {unit.name} 的 tool.yaml scope={declared} 与 plugin.yaml "
            f"scope={scope} 不一致（插件 {pid}）—— tool.yaml 只能写 "
            f"local / global，plugin.yaml 只能写 internal / system / global"
            f"（也接受 local / project）")


def _match_declared(p: Path, declared, sub: str):
    stem = p.stem
    for cap in declared:
        name = str(cap["name"]).replace("\\", "/")
        if name == stem or name == f"{stem}.py" or name == f"{stem}/SKILL.md" \
                or name.endswith(f"/{stem}") or name == p.name:
            return cap
    return None


def _row(kind: str, src: Path, project: str, extra: dict | None = None) -> dict:
    from . import location
    return {"kind": kind, "rel_path": location.rel_to(src, project),
            "src": src, "extra": extra or {}}


def _kind_extra(kind: str, p: Path, pkg: PluginPackage, sub: str) -> dict:
    if kind in ("api", "outbound_switch"):
        return {"kind": "code", "handler": "handle"}
    return {}


def _mcp_servers(path: Path) -> dict:
    from ..mcp import spec as mcp_spec
    return {n: c.model_dump() for n, c in mcp_spec.load_file(path).items()}


def _files_under(d: Path) -> list[Path]:
    if not d.is_dir():
        return []
    skip = {"__pycache__"}
    return [p for p in sorted(d.rglob("*"))
            if p.is_file() and p.suffix != ".pyc"
            and not any(part.startswith(".") or part in skip
                        for part in p.relative_to(d).parts)]
