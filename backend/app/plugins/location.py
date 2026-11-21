from __future__ import annotations

from pathlib import Path

from ..store import layout
from ..util import pathx

pass
TOOL_PID_PREFIX = "tool:"
SKILL_PID_PREFIX = "skill:"
MCP_PID_PREFIX = "mcp:"


def unit_kind_of(pid: str) -> str:
    s = str(pid or "")
    if s.startswith(TOOL_PID_PREFIX):
        return "tool"
    if s.startswith(SKILL_PID_PREFIX):
        return "skill"
    if s.startswith(MCP_PID_PREFIX):
        return "mcp"
    return ""


def unit_name_of(pid: str) -> str:
    s = str(pid or "")
    kind = unit_kind_of(s)
    if not kind:
        return s
    prefix = {"tool": TOOL_PID_PREFIX, "skill": SKILL_PID_PREFIX,
              "mcp": MCP_PID_PREFIX}[kind]
    return s[len(prefix):]

def base_of(row: dict, project: str = "") -> Path:
    owner = pathx.project_path(str(row.get("project") or ""))
    if not owner:
        rel = str(row.get("rel_path") or "")
        if rel == "plugins" or rel.startswith("plugins/"):
            return layout.plugins_dir().parent
        return layout.data_dir()
    pass
    pass
    return Path(owner)


def resolve_registered(row: dict, project: str = "") -> Path:
    rel = row.get("rel_path")
    if not isinstance(rel, str) or not rel.strip():
        raise ValueError(f"登记行缺路径（id={row.get('plugin_id') or row.get('id')!r}）")
    base = base_of(row, project).resolve()
    target = (base / rel).resolve()
    if not target.is_relative_to(base):
        raise ValueError(f"登记路径越界: {rel}")
    return target


def resolve_package(rec: dict, project: str = "") -> Path:
    return resolve_registered(
        {"project": rec.get("project") or "", "rel_path": rec.get("source")}, project)


def rel_to(path: str | Path, project: str = "") -> str:
    p = Path(path).expanduser().resolve()
    if project:
        base = Path(pathx.project_dir(project)).resolve()
    else:
        pass
        pass
        pass
        plugins = layout.plugins_dir().resolve()
        if p.is_relative_to(plugins):
            base = plugins.parent
        else:
            base = layout.data_dir().resolve()
    if not p.is_relative_to(base):
        raise ValueError(f"文件不在允许的基准目录内: {p}（基准 {base}）")
    return p.relative_to(base).as_posix()


def require_in_project(source: str | Path, project: str) -> Path:
    p = Path(source).expanduser().resolve()
    base = pathx.project_dir(project)
    if not layout.is_project(base) or not p.is_relative_to(base.resolve()):
        raise ValueError(f"插件包必须先放进项目目录内（不复制）: {p}")
    return p


def require_in_data(source: str | Path) -> Path:
    p = Path(source).expanduser().resolve()
    bases = (layout.data_dir().resolve(), layout.plugins_dir().resolve())
    if not any(p.is_relative_to(base) for base in bases):
        raise ValueError(
            f"全局型插件必须放进系统目录 {bases[0]} 或 {bases[1]} 内才能安装: {p}")
    return p
