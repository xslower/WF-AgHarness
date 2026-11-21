from __future__ import annotations

from ..store.project_names import project_name, project_of




class PluginScopeError(ValueError):

    def __init__(self, detail: str, status: int = 404) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status = status


def name_of(project: str) -> str:
    return project_name(project)


def project_arg(project: str, installs=None) -> str:
    s = str(project or "").strip()
    if not s or "/" in s or s.startswith("~"):
        return project_of(s)
    hit = project_of(s)
    if hit != s:
        return hit
    if installs is not None:
        for row in installs.list_plugins(""):
            p = str(row.get("project") or "")
            if p and name_of(p) == s:
                return p
    return s


def resolve(installs, plugin_id: str, project: str = "") -> dict:
    pid = str(plugin_id or "").strip()
    if not pid:
        raise PluginScopeError("缺少插件名（id）", status=400)
    rows = installs.plugins_by_id(pid)
    if not rows:
        raise PluginScopeError(f"插件未登记: {pid}")

    want = str(project or "").strip()
    if want:
        if "/" in want or want.startswith("~"):
            raise PluginScopeError(
                f"project 要的是项目名称（如 motion），不是路径: {want}", status=400)
        hit = [r for r in rows if name_of(r["project"]) == want]
        if not hit:
            names = "、".join(name_of(r["project"]) or "全局" for r in rows)
            raise PluginScopeError(
                f"插件 {pid} 没有装在项目 {want} 上（已装: {names}）")
        if len(hit) > 1:
            raise PluginScopeError(f"项目名称 {want} 对应多份安装，无法消歧")
        return hit[0]

    if len(rows) == 1:
        return rows[0]
    names = "、".join(name_of(r["project"]) or "全局" for r in rows)

    raise PluginScopeError(
        f"插件 {pid} 装在多个项目（{names}），请用 project 指定项目名称",
        status=409)
