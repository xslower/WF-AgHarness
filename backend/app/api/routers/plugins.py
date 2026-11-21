from __future__ import annotations

import yaml
from fastapi import APIRouter, Depends
from pydantic import BaseModel


from ..errors import bad_request, not_found, from_error, http_error
from ..deps import Container, get_container

router = APIRouter()


def _project_arg(project: str, installs=None) -> str:
    from ...plugins.resolve import project_arg
    return project_arg(project, installs)


def _list_for_scope(installs, project: str, scope: str) -> list[dict]:
    if project:
        return installs.list_plugins(project)
    rows = installs.list_plugins("")
    if (scope or "global").strip().lower() == "all":
        return rows
    return [r for r in rows if not r["project"]]


def _catalog(installs) -> list[dict]:
    from ...store import layout
    from ...plugins import package as pkgmod

    root = layout.plugins_dir()
    if not root.is_dir():
        return []
    installed = {str(r["id"]): r for r in installs.list_plugins("")
                 if not r["project"]}
    out: list[dict] = []
    for d in sorted(root.iterdir()):
        if not d.is_dir() or d.name.startswith(".") or not pkgmod.is_package_dir(d):
            continue
        row: dict = {"id": d.name, "name": d.name, "version": "",
                     "kinds": [], "mode": "", "desc": "", "path": str(d),
                     "installed": False, "error": "",
                     "requestedProviderKeys": []}
        try:
            row.update(pkgmod.meta_of(pkgmod.load_package(d)))
        except ValueError as e:
            row["error"] = str(e)
        rec = installed.get(row["id"])
        if rec is not None:
            row["installed"] = True
            row["version"] = str(rec.get("version") or row["version"])
        out.append(row)
    return out




class InstallIn(BaseModel):
    source: str
    project: str = ""
    pass
    grantedProviderKeys: list[str] = []


@router.post("/api/plugins/install")
def plugins_install(body: InstallIn, c: Container = Depends(get_container)):
    from ...plugins.install import install as do_install
    try:
        return do_install(body.source, _project_arg(body.project, c.installs), store=c.installs,
                          gateway=c.gateway,
                          granted_provider_keys=body.grantedProviderKeys)
    except ValueError as e:
        raise bad_request(str(e))
    except Exception as e:
        raise from_error(e, prefix="安装插件失败")



@router.delete("/api/plugins/installed/{pid}")
def plugins_uninstall(pid: str, project: str = "",
                      c: Container = Depends(get_container)):
    from ...plugins.install import uninstall as do_uninstall
    try:
        return do_uninstall(pid, _project_arg(project, c.installs), store=c.installs)
    except KeyError as e:
        raise not_found(str(e))


@router.get("/api/plugins/installed")
def plugins_installed(project: str = "", scope: str = "global",
                      c: Container = Depends(get_container)):
    rows = _list_for_scope(c.installs, _project_arg(project, c.installs), scope)
    return {"installed": rows, "project": project or None}


class AdoptIn(BaseModel):
    kind: str
    name: str
    project: str = ""
    grantedProviderKeys: list[str] = []


@router.get("/api/plugins/catalog")
def plugins_catalog(c: Container = Depends(get_container)):
    return {"plugins": _catalog(c.installs)}


@router.get("/api/plugins/discover")
def plugins_discover(project: str = "", c: Container = Depends(get_container)):
    from ...plugins.adopt import scan_local
    return scan_local(_project_arg(project, c.installs), c.installs)


class PluginModeIn(BaseModel):
    id: str
    mode: str
    pass
    project: str = ""


@router.post("/api/plugins/mode")
def plugins_set_mode(body: PluginModeIn, c: Container = Depends(get_container)):
    from ...plugins.mode import resolve_project_package, set_mode
    try:
        root = resolve_project_package(body.id.strip(), body.project, c.installs)
        raw = set_mode(root, body.mode.strip().lower())
        mode = str((yaml.safe_load(raw) or {}).get("mode") or "")
    except (ValueError, OSError) as e:
        raise bad_request(str(e))
    except Exception as e:
        raise from_error(e, prefix="切换插件模式失败")
    from ...event.bus import HUB
    HUB.publish("plugins.changed", {"id": body.id, "mode": mode,
                                    "project": body.project})
    return {"id": body.id, "mode": mode, "project": body.project or None}




@router.post("/api/plugins/adopt")
def plugins_adopt(body: AdoptIn, c: Container = Depends(get_container)):
    from ...plugins.adopt import adopt_plugin, adopt_skill, adopt_tool
    kind = (body.kind or "").strip().lower()
    project = _project_arg(body.project, c.installs)
    try:
        if kind == "skill":
            return adopt_skill(project, body.name, installs=c.installs,
                               gateway=c.gateway)
        if kind == "tool":
            return adopt_tool(project, body.name, installs=c.installs,
                              gateway=c.gateway,
                              granted_provider_keys=body.grantedProviderKeys)
        if kind == "plugin":
            return adopt_plugin(project, body.name, installs=c.installs,
                                gateway=c.gateway,
                                granted_provider_keys=body.grantedProviderKeys)
    except ValueError as e:
        raise bad_request(str(e))
    except Exception as e:
        raise from_error(e, prefix="安装插件失败")
    raise bad_request(f"未知 kind: {body.kind}（只支持 skill / tool / plugin）")


pass


pass
@router.get("/api/plugins/{pid}/detail")
def plugins_detail(pid: str, project: str = "",
                   c: Container = Depends(get_container)):
    from ...plugins import detail
    from ...plugins import resolve as resolver

    try:
        rec = resolver.resolve(c.installs, pid.strip(), project)
    except resolver.PluginScopeError as e:
        raise http_error(e.status, e.detail)
    return detail.describe(rec)


def _specs_of(c: Container, pid: str, project: str) -> tuple[dict, ...]:
    from ...plugins.config import specs_of

    try:
        return specs_of(c.installs, pid, _project_arg(project, c.installs))
    except LookupError:
        raise not_found(f"插件未登记: {pid}")
    except ValueError as e:
        raise bad_request(str(e))


@router.get("/api/plugins/config/{pid}")
def plugins_get_config(pid: str, project: str = "",
                       c: Container = Depends(get_container)):
    from ...plugins.config import masked
    project = _project_arg(project, c.installs)
    specs = _specs_of(c, pid, project)
    return {"id": pid, "project": project or None,
            **masked(pid, project, specs)}


class BotComposeIn(BaseModel):
    values: dict = {}


@router.post("/api/plugins/bot/{pid}/compose")
def plugins_bot_compose(pid: str, body: BotComposeIn, project: str = "",
                        c: Container = Depends(get_container)):
    from ...plugins.bot import compose_question

    try:
        return compose_question(c.installs, pid, _project_arg(project, c.installs),
                                body.values or {})
    except LookupError:
        raise not_found(f"插件未登记: {pid}")
    except ValueError as e:
        raise bad_request(str(e))


class PluginConfigIn(BaseModel):
    values: dict = {}


@router.put("/api/plugins/config/{pid}")
def plugins_put_config(pid: str, body: PluginConfigIn, project: str = "",
                       c: Container = Depends(get_container)):
    from ...plugins.config import ConfigError, masked, save
    project = _project_arg(project, c.installs)
    specs = _specs_of(c, pid, project)
    try:
        save(pid, project, specs, body.values or {})
    except ConfigError as e:
        raise bad_request(str(e))
    return {"id": pid, "project": project or None,
            **masked(pid, project, specs)}

