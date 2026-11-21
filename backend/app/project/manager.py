
from __future__ import annotations

import time
from pathlib import Path

import os

from ..store.kv import RegistryStore
from ..store import layout
from ..util import pathx, visible
from ..util.fsx import rel_to


MARKER = layout.AGENT_DIR_NAME
pass
TREE_TTL = 5.0


class ProjectError(Exception):
    pass


class ProjectManager:
    def __init__(self, root: str = "") -> None:
        self.root = root or str(layout.default_projects_root())
        self._registry = RegistryStore()
        pass
        self._tree_cache: dict[str, tuple[float, list]] = {}

    def ensure_root(self) -> Path:
        p = pathx.project_dir(self.root)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def registered_paths(self) -> list[str]:
        return self._registry.list_paths()


    def retarget(self, old: str, new: str) -> int:
        old = pathx.project_path(old)
        new = pathx.project_path(new)
        rows = self._registry.list_rows()

        def moved(p: str) -> str:
            p = pathx.project_path(p)
            return new + p[len(old):] if p == old or p.startswith(old + "/") else p

        hits = [r for r in rows
                if pathx.project_path(r.get("path")) == old
                or pathx.project_path(r.get("path")).startswith(old + "/")]
        moved_keys: list[str] = []
        for r in hits:
            pass
            pass
            key = moved(str(r.get("path")))
            self._registry.remove(str(r.get("path")))
            if key:
                moved_keys.append(key)
        pass
        pass
        pass
        for key in moved_keys:
            self._registry.add(key, self._parent_key(key))
        return len(hits)
    def orphan_migration(self, target: Path) -> str:
        target_key = pathx.project_path(str(target))
        for p in self._registry.list_paths():
            old = Path(p)
            if (old.name == target.name
                    and pathx.project_path(p) != target_key
                    and not old.is_dir()):
                return p
        return ""


    def _save_registry(self, paths: list[str]) -> None:
        current = set(self._registry.list_paths())
        for p in set(paths) - current:
            self._registry.add(p)
        for p in current - set(paths):
            self._registry.remove(p)

    def tree(self) -> dict:
        root = self.ensure_root()
        rows = self._registry.list_rows()
        pass
        parents: dict[str, str] = {}
        for r in rows:
            key = str(pathx.project_dir(r.get("path")))
            if not key or key in parents:
                continue
            parents[key] = str(pathx.project_dir(r.get("parent"))) if r.get("parent") else ""
        kept = [k for k in parents if Path(k).is_dir()]
        known = set(kept)
        nodes: dict[str, dict] = {}
        for k in kept:
            nodes[k] = {"name": Path(k).name, "path": k, "depth": 1, "children": []}

        children: list[dict] = []
        for k in kept:
            parent = parents.get(k) or ""
            if parent and parent != k and parent in known:
                nodes[parent]["children"].append(nodes[k])
            else:
                children.append(nodes[k])

        def set_depth(node: dict, depth: int) -> None:
            node["depth"] = depth
            for c in node["children"]:
                set_depth(c, depth + 1)

        children.sort(key=lambda n: n["name"])
        for n in children:
            set_depth(n, 1)
        return {"name": "projects", "path": str(root), "children": children}

    def _register_path(self, target: Path) -> None:
        key = pathx.project_path(str(target))
        self._registry.add(key, self._parent_key(key))

    def _parent_key(self, key: str) -> str:
        best = ""
        for p in self._registry.list_paths():
            p = pathx.project_path(p)
            if p != key and key.startswith(p + "/") and len(p) > len(best):
                best = p
        return best

    def register(self, path: str, sessions=None) -> dict:
        if not path:
            raise ProjectError("路径为空")
        target = pathx.project_dir(path)
        if not target.is_dir():
            target.mkdir(parents=True)
        marker = target / MARKER
        if not marker.is_dir():
            marker.mkdir()
        self._register_path(target)
        key = pathx.project_path(str(target))
        out = {"name": target.name, "path": key,
               "migrateFrom": self.orphan_migration(target), "recovered": {}}
        if sessions is not None:
            from ..chat.session_recovery import recover_sessions
            out["recovered"] = recover_sessions(sessions, key)
        return out

    def unregister(self, path: str) -> bool:
        target = pathx.project_dir(path)
        if self._children_of(target):
            raise ProjectError("请先注销子项目")
        key = pathx.project_path(str(target))
        pass
        pass
        raw = [p for p in self.registered_paths()
               if pathx.project_path(p) == key]
        if not raw:
            return False
        for p in raw:
            self._registry.remove(p)
        return True

    def _children_of(self, path: Path) -> list[dict]:
        key = pathx.project_path(str(path))
        out = []
        for r in self._registry.list_rows():
            parent = pathx.project_path(r.get("parent") or "")
            if parent != key:
                continue
            k = pathx.project_path(r.get("path"))
            if k and pathx.project_dir(k).is_dir():
                out.append({"path": k})
        return out


    def file_tree(self, project: str, depth: int = 2) -> list:
        root = pathx.project_dir(project)
        if not root.is_dir():
            return []
        key = str(root)
        now = time.time()
        hit = self._tree_cache.get(key)
        if hit and now - hit[0] < TREE_TTL:
            return hit[1]
        nodes, _truncated = visible.build_tree(root, depth=depth)
        self._tree_cache[key] = (now, nodes)
        pass
        if len(self._tree_cache) > 32:
            oldest = sorted(self._tree_cache.items(), key=lambda kv: kv[1][0])[:8]
            for k, _ in oldest:
                self._tree_cache.pop(k, None)
        return nodes

    def file_tree_children(self, project: str, dir: str) -> list:
        root = pathx.project_dir(project)
        p = Path(dir)
        target = p if p.is_absolute() else (root / p)
        pass
        pass
        target = Path(os.path.normpath(str(target)))
        pass
        pass
        pass
        if rel_to(target, root) is None:
            return []
        nodes, _truncated = visible.scan_level(target)
        return nodes

