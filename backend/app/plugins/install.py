from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

from . import package as pkgmod
from . import schema as plugin_tool_schema
from .plugin_sdk import PluginHost
from ..store import layout
from ..store.db import SqliteStore, Table
from ..util import pathx

logger = logging.getLogger("harness.plugin.installer")


def _key(project: object) -> str:
    return pathx.project_path(str(project or ""))

_INSTALLED_SCHEMA = """
CREATE TABLE IF NOT EXISTS installed_plugins (
  id           TEXT NOT NULL,
  version      TEXT NOT NULL,
  project      TEXT NOT NULL,
  installed_at REAL NOT NULL,
  source       TEXT NOT NULL,
  manifest     TEXT NOT NULL,
  PRIMARY KEY (id, project)
);
CREATE TABLE IF NOT EXISTS installed_files (
  plugin_id TEXT NOT NULL,
  project   TEXT NOT NULL,
  kind      TEXT NOT NULL,
  rel_path  TEXT NOT NULL,
  extra     TEXT NOT NULL DEFAULT '',
  scope     TEXT NOT NULL DEFAULT '',
  sha256    TEXT NOT NULL DEFAULT '',
  PRIMARY KEY (plugin_id, project, rel_path)
);
"""


def _ensure_files_schema(db) -> None:
    rows = list(db.execute("PRAGMA table_info(installed_files)"))
    cols = {r[1] for r in rows}
    if not cols:
        return
    pass
    pass
    pass
    wanted = {"plugin_id", "project", "kind", "rel_path", "extra",
              "scope", "sha256"}
    info = {r[1]: r for r in rows}
    def has_default(name: str) -> bool:
        r = info.get(name)
        return r is not None and r[4] is not None
    already_ok = (cols == wanted
                  and has_default("scope") and has_default("sha256")
                  and all(info[c][3] == 1 for c in ("scope", "sha256")))
    if already_ok:
        return
    pass
    pass
    db.execute("DROP TABLE IF EXISTS installed_files__new")
    db.execute("""
        CREATE TABLE installed_files__new (
          plugin_id TEXT NOT NULL,
          project   TEXT NOT NULL,
          kind      TEXT NOT NULL,
          rel_path  TEXT NOT NULL,
          extra     TEXT NOT NULL DEFAULT '',
          scope     TEXT NOT NULL DEFAULT '',
          sha256    TEXT NOT NULL DEFAULT '',
          PRIMARY KEY (plugin_id, project, rel_path)
        )""")
    src_cols = [r[1] for r in db.execute("PRAGMA table_info(installed_files)")]
    def pick(name: str, default: str) -> str:
        return name if name in src_cols else f"'{default}'"
    db.execute(
        "INSERT OR IGNORE INTO installed_files__new "
        "(plugin_id, project, kind, rel_path, extra, scope, sha256) "
        "SELECT plugin_id, project, kind, rel_path, "
        f"{pick('extra', '')}, {pick('scope', '')}, {pick('sha256', '')} "
        "FROM installed_files")
    db.execute("DROP TABLE installed_files")
    db.execute("ALTER TABLE installed_files__new RENAME TO installed_files")
    db.commit()


class InstallStore(SqliteStore):

    _schema = _INSTALLED_SCHEMA

    def __init__(self, db_path: Optional[Path] = None) -> None:
        super().__init__(db_path or layout.agent_db())
        pass
        pass
        with self._lock:
            _ensure_files_schema(self._db)
        self._plugins = Table(self._db, "installed_plugins")
        self._files = Table(self._db, "installed_files")

    pass
    def list_plugins(self, project: str = "") -> list[dict]:
        rows = self._plugins.select(order="installed_at DESC")
        want = _key(project)
        out: list[dict] = []
        seen: set[tuple[str, str]] = set()
        for r in rows:
            rp = _key(r["project"])
            if want and rp and rp != want:
                continue
            k = (str(r["id"]), rp)
            if k in seen:
                continue
            seen.add(k)
            row = dict(r)
            row["project"] = rp
            out.append(row)
        return out

    def get_plugin(self, pid: str, project: str = "") -> Optional[dict]:
        want = _key(project)
        for r in self._plugins.select({"id": pid}):
            rp = _key(r["project"])
            if rp == want:
                row = dict(r)
                row["project"] = rp
                return row
        return None
    def plugins_by_id(self, pid: str) -> list[dict]:
        out = []
        for r in self._plugins.select({"id": pid}):
            row = dict(r)
            row["project"] = _key(r["project"])
            out.append(row)
        return out

    def files_of(self, pid: str, project: str = "") -> list[dict]:
        want = _key(project)
        out = []
        for r in self._files.select(
                {"plugin_id": pid}, order="rel_path",
                cols="project, kind, rel_path, extra"):
            rp = _key(r["project"])
            if rp != want:
                continue
            row = dict(r)
            row["project"] = rp
            out.append(row)
        return out

    def files_by_kind(self, kind: str, project: str = "",
                      under: bool = False) -> list[dict]:
        rows = self._files.select(
            {"kind": kind}, order="rel_path",
            cols="plugin_id, project, kind, rel_path, extra")
        want = None if project is None else _key(project)
        out: list[dict] = []
        seen: set[tuple[str, str, str]] = set()
        for r in rows:
            rp = _key(r["project"])
            if want is not None and rp and rp != want:
                if not (under and want and rp.startswith(want + "/")):
                    continue
            k = (str(r["plugin_id"]), rp, str(r["rel_path"]))
            if k in seen:
                continue
            seen.add(k)
            row = dict(r)
            row["project"] = rp
            out.append(row)
        return out

    pass
    def add_plugin(self, pkg, project: str, source: str, files: list[dict]) -> None:
        p = _key(project)
        with self._lock:
            self._plugins.insert(
                {"id": pkg.id, "version": pkg.version, "project": p,
                 "installed_at": time.time(), "source": source, "manifest": pkg.raw},
                or_replace=True)
            self._files.insert_many(
                [{"plugin_id": pkg.id, "project": p, "kind": f["kind"],
                  "rel_path": f["rel_path"],
                  "extra": json.dumps(f.get("extra") or {}, ensure_ascii=False)}
                 for f in files], or_replace=True)
            self._db.commit()

    def retarget(self, old: str, new: str) -> int:
        from ..store.retarget import retarget_project_column

        old_key, new_key = _key(old), _key(new)
        if not old_key or old_key == new_key:
            return 0
        with self._lock:
            moved = retarget_project_column(self._db, "installed_plugins",
                                            old_key, new_key)
            moved += retarget_project_column(self._db, "installed_files",
                                             old_key, new_key)
            self._db.commit()
        return moved

    def remove_plugin(self, pid: str, project: str = "") -> None:
        want = _key(project)
        with self._lock:
            for r in self._plugins.select({"id": pid}, cols="id, project"):
                if _key(r["project"]) == want:
                    self._plugins.delete({"id": pid, "project": r["project"]})
            for r in self._files.select(
                    {"plugin_id": pid}, cols="plugin_id, project, rel_path"):
                if _key(r["project"]) == want:
                    self._files.delete({"plugin_id": pid,
                                        "project": r["project"],
                                        "rel_path": r["rel_path"]})
            self._db.commit()


pass
pass
_RUNTIME_RELOAD: object = None


def bind_runtime_reload(fn) -> None:
    global _RUNTIME_RELOAD
    _RUNTIME_RELOAD = fn


def _reload_runtime() -> None:
    if _RUNTIME_RELOAD is None:
        return
    try:
        _RUNTIME_RELOAD()
    except Exception:
        logger.warning("插件运行时刷新失败", exc_info=True)



def install(source: str | Path, project: str = "",
            store: Optional[InstallStore] = None,
            gateway=None, granted_provider_keys=()) -> dict:
    return register_package(pkgmod.load_package(source), project, store, gateway,
                            granted_provider_keys)


def register_package(pkg, project: str = "",
                     store: Optional[InstallStore] = None,
                     gateway=None, granted_provider_keys=()) -> dict:
    _check_key_grants(pkg, granted_provider_keys)
    store = store or InstallStore()
    if pkg.needs_project and not project:
        raise ValueError(f"插件 {pkg.id} 含项目类 kind（{', '.join(pkg.kinds)}），"
                         f"必须指定 project")
    if store.get_plugin(pkg.id, project) is not None:
        raise ValueError(f"插件 {pkg.id} 已登记在 {project or '全局'}，"
                         f"要重新登记请先卸载")

    plan = pkgmod.plan_registrations(pkg, project)
    files, warnings = _register_rows(pkg, plan, project, gateway)
    _check_duplicate_paths(store, pkg.id, project, files)

    pass
    pass
    created = None
    if any(f["kind"] == "provider_setup" for f in files):
        from . import provider_setup as ph
        created = ph.create_provider(
            pkg.id, ph.setup_provider(plan, project, pkg.id,
                                      PluginHost.for_setup(pkg, project)))

    out = _commit(pkg, project, files, store, granted_provider_keys, warnings)
    out["providers"] = [str((created or {}).get("name") or "")] if created else []
    return out


def _commit(pkg, project: str, files: list[dict], store: InstallStore,
            granted, warnings: list[str]) -> dict:
    from . import location
    src = location.rel_to(pkg.root, project) if project else \
        location.rel_to(pkg.root)
    store.add_plugin(pkg, project, src, files)
    from ..store.plugin_config import PluginConfigStore
    PluginConfigStore().set_grants(pkg.id, project, granted)
    _reload_runtime()
    logger.info("插件已就地登记: %s v%s → %s（%d 个文件）",
                pkg.id, pkg.version, project or "全局", len(files))
    return {"id": pkg.id, "version": pkg.version, "project": project,
            "files": [f["rel_path"] for f in files], "warnings": warnings}


def _check_key_grants(pkg, granted) -> None:
    declared = set(getattr(pkg, "requested_provider_keys", ()) or ())
    if not declared:
        return
    given = set(granted or ())
    if given != declared:
        missing = sorted(declared - given)
        extra = sorted(given - declared)
        detail = []
        if missing:
            detail.append(f"未获用户许可: {', '.join(missing)}")
        if extra:
            detail.append(f"未在清单声明: {', '.join(extra)}")
        raise ValueError(f"插件 {pkg.id} 申请读取系统 provider 的 key，"
                         f"安装前需逐项确认（{'; '.join(detail)}）")


def _register_rows(pkg, plan: list[dict], project: str, gateway) -> tuple[list[dict], list[str]]:
    files: list[dict] = []
    for item in plan:
        files.append({"kind": item["kind"], "rel_path": item["rel_path"],
                      "extra": dict(item.get("extra") or {}),
                      "project": project})
    errors, warnings = plugin_tool_schema.validate_tool_files(
        files, project, gateway=gateway)
    if errors:
        raise ValueError("格式校验失败，整包拒装（包目录仍可在子项目里开发）:\n  "
                         + "\n  ".join(errors))
    return files, warnings


def _check_duplicate_paths(store, pid: str, project: str,
                           files: list[dict]) -> None:
    wanted = {f["rel_path"] for f in files}
    want = _key(project)
    rows = store._files.select(cols="plugin_id, project, rel_path")
    clash = [r for r in rows
             if r["rel_path"] in wanted and r["plugin_id"] != pid
             and _key(r["project"]) == want]
    if clash:
        raise ValueError(f"登记冲突：{clash[0]['rel_path']} 已属于插件 "
                         f"{clash[0]['plugin_id']}")


def uninstall(pid: str, project: str = "",
              store: Optional[InstallStore] = None) -> dict:
    store = store or InstallStore()
    if store.get_plugin(pid, project) is None:
        raise KeyError(f"插件未登记: {pid} @ {project or '全局'}")
    files = [f["rel_path"] for f in store.files_of(pid, project)]
    pass
    pass
    removed_providers = []
    try:
        from . import provider_setup as ph
        removed_providers = ph.delete_providers(pid) or []
    except Exception:
        logger.warning("卸载插件 %s 时 provider 清理失败", pid, exc_info=True)
    store.remove_plugin(pid, project)
    _reload_runtime()
    logger.info("插件已摘登记: %s @ %s（%d 行，%d 个 provider）",
                pid, project or "全局", len(files), len(removed_providers))
    return {"id": pid, "project": project, "removed": files,
            "removed_providers": [str(p) for p in removed_providers]}
