from __future__ import annotations

import json
import os
from pathlib import Path

from ..store import layout
from ..tools.builtin.fs.outline import INDEX_SUFFIXES, rows_for

pass
MAX_MAP_CHARS = 20_000
MAX_FILES = 3_000
pass
_SKIP_DIRS = {".git", ".agent", ".trash", ".venv", "venv", "node_modules",
              "__pycache__", "dist", "build", ".pytest_cache", ".mypy_cache",
              "site-packages", "runs", "data", ".idea", ".vscode", "coverage"}


def _project_root(cwd: str, project: str = "") -> Path | None:
    if project:
        p = Path(project).expanduser()
        try:
            p = p.resolve()
        except OSError:
            return None
        return p if p.is_dir() else None
    try:
        p = Path(cwd or "").expanduser().resolve()
    except OSError:
        return None
    if not p.is_dir():
        p = p.parent
    cur = p
    while True:
        if layout.is_project(cur):
            return cur
        parent = cur.parent
        if parent == cur:
            return None
        cur = parent


def _index_path(cwd: str, project: str = "") -> Path | None:
    root = _project_root(cwd, project)
    if root is None:
        return None
    return root / layout.AGENT_DIR_NAME / "code_map.json"


def _scan(root: Path, old: dict[str, dict] | None = None) -> tuple[list[dict], bool]:
    old = old or {}
    out: list[dict] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames
                             if d not in _SKIP_DIRS and not d.startswith("."))
        for name in sorted(filenames):
            if not name.endswith(INDEX_SUFFIXES):
                continue
            p = Path(dirpath) / name
            rel = str(p.relative_to(root))
            try:
                mt = p.stat().st_mtime
            except OSError:
                continue
            prev = old.get(rel)
            if prev and abs(float(prev.get("mtime", 0)) - mt) < 1e-6:
                out.append({"path": rel, "mtime": mt,
                            "rows": prev.get("rows", [])})
            else:
                try:
                    text = p.read_text(encoding="utf-8", errors="replace")
                    rows = rows_for(text, name)
                except OSError:
                    continue
                if not rows:
                    continue
                out.append({"path": rel, "mtime": mt, "rows": rows})
            if len(out) >= MAX_FILES:
                return out, True
    return out, False


def build_index(cwd: str, force: bool = False,
                project: str = "") -> tuple[list[dict], bool]:
    ipath = _index_path(cwd, project)
    if ipath is None:
        return [], False
    pass
    root = ipath.parent.parent
    old: dict[str, dict] = {}
    if not force and ipath.exists():
        try:
            for e in json.loads(ipath.read_text(encoding="utf-8")).get("files", []):
                old[e["path"]] = e
        except (OSError, ValueError, KeyError):
            old = {}
    merged, capped = _scan(root, old)
    pass
    if force or not _same_index(old, merged):
        try:
            ipath.parent.mkdir(parents=True, exist_ok=True)
            ipath.write_text(json.dumps({"files": merged}, ensure_ascii=False),
                             encoding="utf-8")
        except OSError:
            pass
    return merged, capped


def _same_index(old: dict[str, dict], new: list[dict]) -> bool:
    if len(old) != len(new):
        return False
    for e in new:
        prev = old.get(e["path"])
        if not prev or prev.get("rows") != e["rows"]:
            return False
    return True


def _match(e: dict, keys: list[str]) -> bool:
    hay = (e["path"] + " " + " ".join(e["rows"])).lower()
    return any(k in hay for k in keys)


def _filter_by_prefix(files: list[dict], cwd: str, subpath: str,
                      project: str = "") -> tuple[list[dict], str]:
    raw = (subpath or "").strip()
    if not raw:
        return files, ""
    top = _project_root(cwd, project)
    if top is None:
        return files, ""
    p = Path(raw)
    if not p.is_absolute():
        p = Path(cwd) / p
    try:
        p = p.resolve()
    except OSError:
        return [], f"路径无法解析: {raw}"
    try:
        rel = p.relative_to(top)
    except ValueError:
        return [], (f"path 不在当前项目内（项目根 {top}）：{raw}；"
                    "代码地图只索引本项目，跨项目请先切换到对应项目目录")
    prefix = str(rel).replace("\\", "/")
    if prefix == ".":
        return files, ""
    scoped = [e for e in files
              if e["path"] == prefix or e["path"].startswith(prefix + "/")]
    if not scoped:
        if not p.exists():
            return [], f"路径不存在: {raw}"
        return [], (f"目录 {raw} 下没有可索引的源码文件"
                    f"（支持 {' '.join(INDEX_SUFFIXES)}）；"
                    "其它语言请用 grep(path=..., outline=false) 正文检索")
    return scoped, ""


pass
def _tree_lines(files: list[dict], rows_per: int | None) -> list[str]:
    width = min(56, max((len(e["path"]) for e in files), default=20))
    out: list[str] = []
    for e in sorted(files, key=lambda x: x["path"]):
        out.append(f"{e['path']:<{width}}  ({len(e['rows'])} 个符号)")
        if rows_per:
            out.extend("    " + r for r in e["rows"][:rows_per])
    return out


def _bounded(lines: list[str], tail: str) -> str:
    out = "\n".join(lines)
    if len(out) <= MAX_MAP_CHARS:
        return out
    kept: list[str] = []
    used = 0
    for ln in lines:
        if used + len(ln) + 1 > MAX_MAP_CHARS:
            break
        kept.append(ln)
        used += len(ln) + 1
    dropped = len(lines) - len(kept)
    return "\n".join(kept) + f"\n...[{tail}；已省略后面 {dropped} 行]"


def query_index(cwd: str, keys: list[str], limit: int = 60,
                subpath: str = "", project: str = "") -> str:
    files, capped = build_index(cwd, project=project)
    if not files:
        return "(代码地图为空：项目里没有可解析的源码文件，或不在项目目录内)"
    files, scope_err = _filter_by_prefix(files, cwd, subpath,
                                         project=project)
    if scope_err:
        return f"(代码地图查询失败：{scope_err})"
    ks = [k.lower() for k in keys if k and str(k).strip()]
    note = (f"（索引达 {MAX_FILES} 文件上限，后续文件未收录；"
            "定位不到时请用 grep 正文检索或缩小 path）" if capped else "")
    if not ks:
        head = (f"项目代码地图（{len(files)} 个源文件{note}，传 key 可查方法签名；"
                "取原文用 f_read(path, lines=\"A,B\")）：\n")
        return head + _bounded(_tree_lines(files[:limit], None),
                              "地图已截，请传 key 或缩小 path")
    hits = [e for e in files if _match(e, ks)][:limit]
    if not hits:
        return f"(代码地图中无匹配：{ks}){note}"
    head = (f"代码地图命中 {len(hits)} 个文件（key={ks}{note}；"
            "取原文用 f_read(path, lines=\"A,B\")）：\n")
    return head + _bounded(_tree_lines(hits, 40),
                          "地图已截，请缩小 key 或用 grep 精确定位")


def render_for_spawn(cwd: str, hints: list[str], project: str = "") -> str:
    files, capped = build_index(cwd, project=project)
    if not files:
        return ""
    ks = [str(h).lower() for h in (hints or []) if h and str(h).strip()]
    note = "，索引达上限未收全" if capped else ""
    head = (f"【项目代码地图】（{len(files)} 个源文件{note}，索引非全文，"
            "拿到路径:行号后用 f_read(lines=) 取原文）")
    if ks:
        hits = [e for e in files if _match(e, ks)][:8]
        if hits:
            body = (f"疑似相关（hints={ks[:6]}）：\n"
                    + "\n".join(_tree_lines(hits, 25)))
        else:
            body = (f"（hints={ks[:6]} 在地图中无命中，以下为目录清单）\n"
                    + "\n".join(_tree_lines(files[:30], None)))
    else:
        body = "\n".join(_tree_lines(files[:30], None))
    pass
    return _bounded([head] + body.split("\n"), "地图已截")
