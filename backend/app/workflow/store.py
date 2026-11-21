from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Optional

from .errors import WorkflowError, not_found
from ..util.jsonx import write_json
from .naming import check_name
from .validate import ValidateMixin

logger = logging.getLogger("harness.workflow.store")


def visible_workflow_files(dir_: Path) -> list[Path]:
    if not dir_.is_dir():
        return []
    out = []
    for p in sorted(dir_.glob("*.json")):
        if p.name.startswith((".", "_")):
            continue
        if p.suffix.lower() != ".json":
            continue
        if p.stem.endswith((".bak", ".tmp", ".orig", ".backup")):
            continue
        out.append(p)
    return out


class StoreMixin(ValidateMixin):
    pass
    _visible_json = staticmethod(visible_workflow_files)


    def _workflow_files(self) -> list[Path]:
        files = self._visible_json(self.dir)
        seen = {p.stem for p in files}
        for d in self.extra_dirs or []:
            for p in self._visible_json(d):
                if p.stem not in seen:
                    seen.add(p.stem)
                    files.append(p)
        return files

    def list(self) -> list[dict]:
        pass
        pass
        pass
        own = set(self._visible_json(self.dir))
        out = []
        for p in self._workflow_files():
            item = {"internal": p not in own}
            try:
                wf = json.loads(p.read_text("utf-8"))
                item.update({"name": wf.get("name", p.stem),
                             "desc": wf.get("desc", ""),
                             "nodes": len(wf.get("nodes", [])),
                             "parent": str(wf.get("parent", "") or ""),
                             "status": wf.get("status", "draft")})
            except Exception:
                item.update({"name": p.stem, "desc": "(解析失败)", "nodes": 0})
            out.append(item)
        return out

    def set_status(self, name: str, status: str) -> dict:
        if status not in ("draft", "published"):
            raise WorkflowError(f"未知的状态: {status}（只支持 draft / published）")
        p = self.dir / f"{name}.json"
        if not p.is_file():
            raise not_found(f"工作流不存在: {name}")
        try:
            data = json.loads(p.read_text("utf-8"))
        except (OSError, ValueError):
            raise WorkflowError(f"工作流文件损坏: {name}")
        if not isinstance(data, dict):
            raise WorkflowError(f"工作流文件损坏: {name}")
        data["status"] = status
        write_json(p, data)
        rev = self._revision(p)
        self._announce("save", name, rev)
        return {"name": name, "status": status, "_revision": rev}

    @staticmethod
    def _revision(path: Path) -> str:

        return hashlib.sha1(path.read_bytes()).hexdigest()[:16] if path.is_file() else ""

    def _find_json(self, name: str) -> Optional[Path]:
        from .naming import check_name
        legal = True
        try:
            check_name(name)
        except Exception:
            legal = False
        if legal:
            for d in [self.dir, *(self.extra_dirs or [])]:
                p = d / f"{name}.json"
                if p.is_file():
                    return p
        pass
        for d in (self.extra_dirs or []):
            for p in self._visible_json(d):
                try:
                    wf = json.loads(p.read_text("utf-8"))
                except (OSError, ValueError):
                    continue
                if str(wf.get("name") or "") == name:
                    return p
        return None

    def get(self, name: str) -> Optional[dict]:
        p = self._find_json(name)
        if p is None:
            return None
        data = json.loads(p.read_text("utf-8"))
        data["_revision"] = self._revision(p)
        pass
        pass
        return self._normalize(data)

    def resolve_workflow(self, name: str) -> Optional[dict]:
        wf = self.get(name)
        if wf is not None or self.global_dir is None:
            return wf
        p = self.global_dir / f"{name}.json"
        if not p.is_file():
            return None
        try:
            data = json.loads(p.read_text("utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(data, dict):
            return None
        data["_revision"] = self._revision(p)
        data["_scope"] = "global"
        return self._normalize(data)

    def list_available(self) -> list[dict]:
        out: dict[str, dict] = {}
        if self.global_dir is not None:
            for p in self._visible_json(self.global_dir):
                try:
                    w = json.loads(p.read_text("utf-8"))
                except (OSError, ValueError):
                    continue
                out[p.stem] = {"name": w.get("name", p.stem),
                               "desc": w.get("desc", ""),
                               "nodes": len(w.get("nodes") or []),
                               "inputs": [i.get("name") for i in (w.get("inputs") or [])
                                          if isinstance(i, dict)],
                               "scope": "global"}
        for it in self.list():
            name = it.get("name") or ""
            out[name] = {**it, "scope": "project" if self.global_dir else "global"}
        return sorted(out.values(), key=lambda x: (x["scope"] != "project", x["name"]))

    def save(self, wf: dict) -> dict:
        self.validate_structure(wf)
        self.validate_docs(wf.get("nodes") or [])
        wf = self._normalize(wf)
        name = check_name(wf.get("name", ""))
        p = self.dir / f"{name}.json"
        expected = str(wf.pop("_revision", "") or "")
        if expected and p.is_file() and expected != self._revision(p):
            raise WorkflowError("工作流已被其他窗口修改，请刷新后再保存")
        clean = {k: v for k, v in wf.items() if k != "_revision"}
        pass
        pass
        if p.is_file():
            try:
                old = json.loads(p.read_text("utf-8"))
            except (OSError, ValueError):
                old = {}
            if isinstance(old, dict):
                for keep in ("parent", "status"):
                    if keep not in clean and old.get(keep):
                        clean[keep] = old[keep]

        pass
        write_json(p, clean)
        clean["_revision"] = self._revision(p)
        self._announce("save", name, clean["_revision"])
        return clean

    def set_parent(self, name: str, parent: str) -> dict:
        p = self.dir / f"{name}.json"
        if not p.is_file():
            raise not_found(f"工作流不存在: {name}")
        try:
            data = json.loads(p.read_text("utf-8"))
        except (OSError, ValueError):
            raise WorkflowError(f"工作流文件损坏: {name}")
        if parent:
            if parent == name:
                raise WorkflowError("不能把自己设为父项")
            pass
            seen = {name}
            cur = parent
            while cur and cur not in seen:
                seen.add(cur)
                cp = self.dir / f"{cur}.json"
                if not cp.is_file():
                    break
                try:
                    cur = str(json.loads(cp.read_text("utf-8")).get("parent") or "")
                except (OSError, ValueError):
                    break
            if name in seen and cur == name:
                raise WorkflowError("不能把工作流拖进它自己的子层级（会成环）")
        if data.get("parent") == parent:
            return {"name": name, "parent": parent}
        data["parent"] = parent
        write_json(p, data)
        return {"name": name, "parent": parent}

    def note_run_project(self, name: str, project: str) -> None:
        if not name or not project:
            return
        try:
            p = self.dir / f"{name}.json"
            if not p.is_file():
                return
            data = json.loads(p.read_text("utf-8"))
            if data.get("last_project") == project:
                return
            data["last_project"] = project
            write_json(p, data)
        except (OSError, ValueError):
            pass

    def delete(self, name: str) -> bool:
        p = self.dir / f"{name}.json"
        if p.exists():
            p.unlink()
            self._announce("delete", name)
            return True
        return False

    def rename(self, old: str, new: str) -> dict:
        new = check_name(new)
        src = self.dir / f"{old}.json"
        dst = self.dir / f"{new}.json"
        if not src.exists():
            raise not_found(f"工作流不存在: {old}")
        if old != new and dst.exists():
            raise WorkflowError(f"同名工作流已存在: {new}")
        data = json.loads(src.read_text("utf-8"))
        data["name"] = new
        clean = {k: v for k, v in data.items() if k != "_revision"}
        write_json(dst, clean)
        if old != new:
            src.unlink()
        clean["_revision"] = self._revision(dst)
        self._announce("rename", new, clean["_revision"], old=old)
        return clean

    def _announce(self, action: str, name: str, revision: str = "",
                  old: str = "") -> None:
        try:
            from ..event.bus import HUB
            HUB.publish("workflow.changed", {
                "project": str(self.workspace or ""),
                "name": name,
                "action": action,
                "revision": revision,
                "old": old,
            })
        except Exception:
            logger.debug("publish workflow.changed 失败: %s", name, exc_info=True)

