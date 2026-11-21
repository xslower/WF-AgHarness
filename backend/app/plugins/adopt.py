from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from . import package as pkgmod
from .install import InstallStore, register_package
from ..store import layout
from ..util import pathx

logger = logging.getLogger("harness.plugin.adopt")


pass

def _local_plugin_dirs(project: str) -> list[Path]:
    root = layout.project_plugins_dir(project)
    if not root.is_dir():
        return []
    return [d for d in sorted(root.iterdir())
            if d.is_dir() and not d.name.startswith(".") and pkgmod.is_package_dir(d)]


def _local_skill_dirs(project: str) -> list[Path]:
    root = layout.project_skills_dir(project)
    if not root.is_dir():
        return []
    out: list[Path] = []
    for d in sorted(root.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        if (d / "SKILL.md").is_file():
            out.append(d)
            continue
        for sub in sorted(d.iterdir()):
            if sub.is_dir() and not sub.name.startswith(".") \
                    and (sub / "SKILL.md").is_file():
                out.append(sub)
    return out


def _local_tool_units(project: str) -> list:
    from . import tool_unit
    return tool_unit.units_under(layout.project_tools_dir(project), strict=False)


def _skill_rel_of(rel_path: str) -> str:
    parts = Path(rel_path).parts
    key = (layout.AGENT_DIR_NAME, layout.SKILLS_DIR_NAME)
    for i in range(len(parts) - 1):
        if (parts[i], parts[i + 1]) == key and i + 2 < len(parts):
            return "/".join(parts[i + 2: -1])
    return rel_path


def _project_of(project: str) -> Path:
    p = pathx.project_dir(project)
    if not layout.is_project(p):
        raise ValueError(f"不是项目目录（未登记）: {project}")
    return p


def registered_skill_dirs(installs: InstallStore, project: str) -> list[Path]:
    from . import location
    out: list[Path] = []
    for scope in layout.project_chain(project):
        for row in installs.files_by_kind("skill_bundle", str(scope)):
            try:
                d = location.resolve_registered(row, str(scope)).parent
            except ValueError:
                continue
            if (d / "SKILL.md").is_file() and d not in out:
                out.append(d)
    return out


def scan_local(project: str, installs: InstallStore) -> dict:
    p = pathx.project_dir(project)
    if not layout.is_project(p):
        return {"plugins": [], "skills": [], "tools": [], "dev": []}
    top = str(p)
    pass
    installed_ids = {r["id"] for r in installs.list_plugins(top)}

    installed_skills = {_skill_rel_of(r["rel_path"])
                        for r in installs.files_by_kind("skill_bundle", top)}
    installed_tools = {r["rel_path"]
                       for r in installs.files_by_kind("tool", top)}

    plugins: list[dict] = []
    dev: list[dict] = []
    for d in _local_plugin_dirs(top):
        registered = False
        info: dict[str, Any] = {"id": d.name, "path": str(d), "name": d.name,
                                "kinds": [], "version": "", "desc": ""}
        try:
            pkg = pkgmod.load_package(d)
            pass
            pass
            info.update(pkgmod.meta_of(pkg))
            registered = pkg.id in installed_ids
        except ValueError as e:
            info["error"] = str(e)
        info["registered"] = registered
        errors = diagnose(top, d) if not registered else []
        if info.get("config_error"):
            errors = [*errors, info["config_error"]]
        info["errors"] = errors
        pass
        pass
        pass
        dev.append(info)

    skill_root = layout.project_skills_dir(top)
    skills: list[dict] = []
    for d in _local_skill_dirs(top):
        rel = d.relative_to(skill_root).as_posix()
        if rel not in installed_skills:
            skills.append({"name": rel, "display": d.name, "path": str(d)})

    tools: list[dict] = []
    from .location import rel_to
    for unit in _local_tool_units(top):
        if rel_to(unit.entry, top) in installed_tools:
            continue
        info = {"name": unit.name,
                "display": (unit.meta.get("name") or unit.name) if unit.is_dir
                          else unit.entry.name,
                "path": str(unit.root if unit.is_dir else unit.entry),
                "unit": "dir" if unit.is_dir else "file"}
        if unit.error:
            info["error"] = unit.error
        if unit.is_dir:
            info["desc"] = unit.meta.get("desc") or ""
            info["scope"] = unit.meta.get("scope") or "local"
            info["requestedProviderKeys"] = list(
                unit.meta.get("requested_provider_keys") or ())
            if unit.meta.get("config_error"):
                info["config_error"] = unit.meta["config_error"]
        tools.append(info)

    return {"plugins": plugins, "skills": skills, "tools": tools, "dev": dev}


def diagnose(project: str, source: str | Path, gateway=None) -> list[str]:
    from . import schema as tool_schema
    try:
        pkg = pkgmod.load_package(source)
        plan = pkgmod.plan_registrations(pkg, project)
        rows = [{"kind": i["kind"], "rel_path": i["rel_path"],
                 "extra": dict(i.get("extra") or {}), "project": project}
                for i in plan]
        errors, _ = tool_schema.validate_tool_files(rows, project, gateway=gateway)
        return errors
    except ValueError as e:
        return [str(e)]
    except Exception as e:
        return [f"{type(e).__name__}: {e}"]


pass

def _minimal_pkg(pid: str, root: Path, kinds: tuple[str, ...]) -> pkgmod.PluginPackage:
    raw = json.dumps({"id": pid, "name": pid, "version": "local",
                      "kinds": list(kinds)}, ensure_ascii=False)
    return pkgmod.PluginPackage(root=root, id=pid, name=pid, version="local",
                                kinds=kinds, raw=raw)


def adopt_skill(project: str, name: str,
                installs: Optional[InstallStore] = None,
                gateway=None) -> dict:
    installs = installs or InstallStore()
    top = _project_of(project)
    root = layout.project_skills_dir(top).resolve()
    d = (root / name).resolve()
    if not d.is_relative_to(root) or d == root or not (d / "SKILL.md").is_file():
        raise ValueError(f"skill 不存在或缺少 SKILL.md: {d}")
    from . import location
    pkg = _minimal_pkg(f"{location.SKILL_PID_PREFIX}{name}",
                       layout.project_skills_dir(top), ("skill_bundle",))
    files = [{"kind": "skill_bundle",
              "rel_path": location.rel_to(d / "SKILL.md", str(top)),
              "extra": {}, "project": str(top)}]
    return _register_minimal(pkg, str(top), installs, files)


def adopt_tool(project: str, name: str,
               installs: Optional[InstallStore] = None,
               gateway=None, granted_provider_keys=()) -> dict:
    from . import location, tool_unit
    installs = installs or InstallStore()
    top = _project_of(project)
    unit = tool_unit.discover(layout.project_tools_dir(top), name)
    if unit is None:
        raise ValueError(f"工具不存在或缺少 tool.yaml: {name}")
    scope = unit.meta.get("scope") or ""
    if scope == tool_unit.SCOPE_GLOBAL:
        raise ValueError(f"工具 {name} 声明了 global，独立工具只能是 local（§2.1）")
    pkg = _minimal_pkg(f"{location.TOOL_PID_PREFIX}{unit.name}", unit.root, ("tool",))
    pkg.requested_provider_keys = tuple(unit.meta.get("requested_provider_keys") or ())
    _check_tool_grants(pkg, granted_provider_keys)
    files = [{"kind": "tool", "rel_path": location.rel_to(unit.entry, str(top)),
              "extra": unit.extra(), "project": str(top)}]
    return _register_minimal(pkg, str(top), installs, files, gateway,
                             granted_provider_keys)


def adopt_mcp(project: str, name: str,
              installs: Optional[InstallStore] = None) -> dict:
    from . import location

    installs = installs or InstallStore()
    top = _project_of(project)
    root = layout.project_mcp_dir(top)
    path = root / f"{name}.json"
    if not path.is_file():
        raise ValueError(f"MCP 定义不存在: {path}")
    from ..mcp import spec as mcp_spec
    servers = {n: c.model_dump() for n, c in mcp_spec.load_file(path).items()}
    if not servers:
        raise ValueError(f"MCP 定义里没有可用的服务器: {path}")
    pkg = _minimal_pkg(f"{location.MCP_PID_PREFIX}{name}", root, ("mcp_server",))
    files = [{"kind": "mcp_server",
              "rel_path": location.rel_to(path, str(top)),
              "extra": {"servers": servers}, "project": str(top)}]
    return _register_minimal(pkg, str(top), installs, files)


def unadopt_mcp(project: str, name: str,
                installs: Optional[InstallStore] = None) -> None:
    from . import location

    installs = installs or InstallStore()
    try:
        p = _project_of(project)
    except ValueError:
        return
    try:
        installs.remove_plugin(f"{location.MCP_PID_PREFIX}{name}", str(p))
    except Exception:
        pass


def adopt_plugin(project: str, pid: str,
                 installs: Optional[InstallStore] = None,
                 gateway=None, granted_provider_keys=()) -> dict:
    installs = installs or InstallStore()
    top = _project_of(project)
    root = layout.project_plugins_dir(top) / pid
    if not pkgmod.is_package_dir(root):
        raise ValueError(f"插件包不存在或缺少 plugin.yaml: {root}")
    return register_package(pkgmod.load_package(root), str(top), installs,
                             gateway, granted_provider_keys)


def _check_tool_grants(pkg, granted) -> None:
    from .install import _check_key_grants
    _check_key_grants(pkg, granted)


def _register_minimal(pkg, project: str, installs: InstallStore,
                      files: list[dict], gateway=None,
                      granted_provider_keys=()) -> dict:
    from . import schema as tool_schema
    from .install import _commit
    if installs.get_plugin(pkg.id, project) is not None:
        raise ValueError(f"{pkg.id} 已登记，要重新登记请先卸载")
    errors, warnings = tool_schema.validate_tool_files(
        [dict(f) for f in files], project, gateway=gateway)
    if errors:
        raise ValueError("格式校验失败，整包拒装:\n  " + "\n  ".join(errors))
    out = _commit(pkg, project, files, installs, granted_provider_keys, warnings)
    return {"kind": pkg.kinds[0], **out}
