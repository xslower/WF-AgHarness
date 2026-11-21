# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import json
import shutil
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING
from xml.etree import ElementTree as ET

from ...text_limit import abs_path as _abs
from ..fs.common import guard_paths, resolve as _resolve
from ._common import finish_doc, resolve_doc
from .exec import run_worker

if TYPE_CHECKING:  # 仅类型提示，避免工具实现反向依赖工具注册表
    from ... import ToolContext, ToolRegistry

P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PKG = "{http://schemas.openxmlformats.org/package/2006/relationships}"

PPT_ACTIONS = ("inspect", "read", "replace_text", "set_notes", "add_slide",
               "delete_slide", "move_slide", "add_textbox", "add_picture")
_EDIT_ACTIONS = set(PPT_ACTIONS) - {"inspect", "read"}


def _fail(code: str, msg: str, **extra) -> str:
    return json.dumps({"ok": False, "code": code, "error": msg, **extra},
                      ensure_ascii=False)


def _slide_order(z: zipfile.ZipFile) -> list[str]:
    rels = {}
    try:
        root = ET.fromstring(z.read("ppt/_rels/presentation.xml.rels"))
        for rel in root.findall(f"{PKG}Relationship"):
            rid, target = rel.get("Id"), rel.get("Target") or ""
            if target.startswith("slides/"):
                rels[rid] = "ppt/" + target
    except KeyError:
        pass
    try:
        pres = ET.fromstring(z.read("ppt/presentation.xml"))
    except KeyError:
        return []
    out = []
    lst = pres.find(f"{P}sldIdLst")
    if lst is None:
        return out
    for sld in lst.findall(f"{P}sldId"):
        rid = sld.get(f"{R}id")
        path = rels.get(rid)
        if path:
            out.append(path)
    if not out:  # rels 不全时退回按文件名排
        nums = sorted(int(n[len("ppt/slides/slide"):-4])
                      for n in z.namelist()
                      if n.startswith("ppt/slides/slide") and n.endswith(".xml"))
        out = [f"ppt/slides/slide{i}.xml" for i in nums]
    return out


def _text(el: ET.Element) -> str:
    return "".join(t.text or "" for t in el.iter(f"{A}t"))


def _para_lines(el: ET.Element) -> list[str]:
    lines = []
    for p in el.iter(f"{A}p"):
        s = "".join(t.text or "" for t in p.iter(f"{A}t")).strip()
        if s:
            lines.append(s)
    return lines


def _table_md(tbl: ET.Element) -> list[str]:
    rows = []
    for tr in tbl.findall(f"{A}tr"):
        rows.append([" ".join(_text(tc).split()) for tc in tr.findall(f"{A}tc")])
    if not rows:
        return []
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    return (["| " + " | ".join(rows[0]) + " |",
             "| " + " | ".join(["---"] * width) + " |"]
            + ["| " + " | ".join(r) + " |" for r in rows[1:]])


def _notes_path(z: zipfile.ZipFile, slide_path: str) -> str | None:
    name = Path(slide_path).name
    rel = f"ppt/slides/_rels/{name}.rels"
    try:
        root = ET.fromstring(z.read(rel))
    except KeyError:
        return None
    for r in root.findall(f"{PKG}Relationship"):
        t = r.get("Target") or ""
        if "notesSlide" in t:
            return "ppt/" + t.replace("../", "")
    return None


def _shape_summary(sp_tree: ET.Element) -> dict:
    shapes, tables, pics = 0, 0, 0
    for sp in sp_tree:
        if sp.tag == f"{P}sp":
            shapes += 1
        elif sp.tag == f"{P}graphicFrame":
            if sp.find(f".//{A}tbl") is not None:
                tables += 1
        elif sp.tag == f"{P}pic":
            pics += 1
    return {"shapes": shapes, "tables": tables, "pictures": pics}


def _slide_title(sp_tree: ET.Element) -> str:
    for sp in sp_tree.iter(f"{P}sp"):
        ph = sp.find(f".//{P}ph")
        if ph is not None and (ph.get("type") or "") in ("title", "ctrTitle"):
            return " ".join(_text(sp).split())[:120]
    # 没占位符标题：取文字最多的那个形状
    best = ""
    for sp in sp_tree.iter(f"{P}sp"):
        t = " ".join(_text(sp).split())
        if len(t) > len(best):
            best = t
    return best[:120]


def _load(z: zipfile.ZipFile, path: str) -> ET.Element:
    return ET.fromstring(z.read(path))


def _do_inspect(p: Path) -> dict:
    with zipfile.ZipFile(p) as z:
        order = _slide_order(z)
        slides = []
        for i, sp in enumerate(order, 1):
            root = _load(z, sp)
            tree = root.find(f"{P}cSld/{P}spTree")
            if tree is None:
                continue
            info = {"slide": i, "title": _slide_title(tree), **_shape_summary(tree),
                    "has_notes": _notes_path(z, sp) is not None}
            slides.append(info)
        return {"ok": True, "pages": len(order), "slides": slides}


def _do_read(p: Path, slide: int, pages: str) -> dict:
    with zipfile.ZipFile(p) as z:
        order = _slide_order(z)
        if pages:
            a, _, b = pages.partition("-")
            start = max(1, int(a))
            end = min(len(order), int(b) if b else start)
            want = list(range(start, end + 1))
        elif slide:
            if slide < 1 or slide > len(order):
                return {"ok": False, "code": "bad_slide",
                        "error": f"页码 {slide} 越界，共 {len(order)} 页（1 基）",
                        "pages": len(order)}
            want = [slide]
        else:
            want = [1]

        out = []
        for n in want:
            root = _load(z, order[n - 1])
            tree = root.find(f"{P}cSld/{P}spTree")
            lines = [f"## 第 {n} 页"]
            if tree is not None:
                for sp in tree:
                    if sp.tag == f"{P}sp":
                        lines.extend(_para_lines(sp))
                    elif sp.tag == f"{P}graphicFrame":
                        tbl = sp.find(f".//{A}tbl")
                        if tbl is not None:
                            lines.extend(_table_md(tbl))
                    elif sp.tag == f"{P}pic":
                        lines.append("[图片]")
            np = _notes_path(z, order[n - 1])
            if np:
                try:
                    lines.append("[备注] " + " ".join(_para_lines(_load(z, np))))
                except KeyError:
                    pass
            out.append({"slide": n, "text": "\n".join(lines)})
        return {"ok": True, "pages": len(order), "read": want, "slides": out}


async def ppt(action: str, ctx: "ToolContext", path: str = "", slide: int = 0,
              pages: str = "", old: str = "", new: str = "", text: str = "",
              to: int = 0, layout: int = -1, left: int = 0, top: int = 0,
              width: int = 0, height: int = 0, picture: str = "") -> str:
    if action not in PPT_ACTIONS:
        return _fail("bad_action", f"action 只能是 {list(PPT_ACTIONS)}，收到 {action!r}")

    def suffix_ok(fp: Path) -> str | None:
        if fp.suffix.lower() not in (".pptx", ".pptm"):
            return (f"ppt 只支持 .pptx/.pptm；{fp.suffix} 是老二进制格式，"
                    f"本机没有 libreoffice，请先另存为 .pptx")
        return None

    p, err = resolve_doc(path, ctx.cwd, _abs, _fail, suffix_ok)
    if err is not None:
        return err
    if not zipfile.is_zipfile(p):
        return _fail("bad_file", "不是有效的 pptx（zip 结构损坏）")

    # 写动作必须过安全裁决：`workspace` 档下出项目的路径要审批，`review` 档
    # 一律审批。原来这里直接写盘 —— 「命令有人管、文件没人管」的同一个洞，
    # f_write/f_path 已经堵上，ppt 漏了。
    if action not in ("inspect", "read"):
        blocked = await guard_paths(ctx, "modify", path)
        if blocked:
            return blocked

    try:
        if action == "inspect":
            return json.dumps({**_do_inspect(p), "path": str(p)}, ensure_ascii=False)
        if action == "read":
            return json.dumps({**_do_read(p, int(slide or 0), pages or ""),
                               "path": str(p)}, ensure_ascii=False)
    except (KeyError, ET.ParseError) as e:
        return _fail("bad_file", f"解析 pptx 失败: {type(e).__name__}: {e}")

    # ---- 以下都是写操作：先备份，再交给子进程的 python-pptx
    bak = p.with_suffix(p.suffix + ".bak")
    if not bak.exists():
        shutil.copy2(p, bak)

    payload = {"op": "ppt_edit", "path": str(p), "action": action,
               "slide": int(slide or 0), "old": old, "new": new, "text": text,
               "to": int(to or 0), "layout": int(layout) if layout >= 0 else None,
               "left": int(left or 0), "top": int(top or 0),
               "width": int(width or 0), "height": int(height or 0),
               "picture": str(_resolve(ctx, picture)) if picture else ""}
    out = await asyncio.to_thread(run_worker, payload)
    if out.get("ok"):
        out["backup"] = str(bak)
    return finish_doc(out, p, action)


def register(reg: "ToolRegistry") -> None:
    reg.register(
        "ppt",
        "读/改 .pptx 演示文稿。先 action=inspect 看总页数与每页概要（标题、形状/表格/图片数、"
        "有无备注），再 action=read 用 slide 读指定页或 pages 读页码范围（如 \"2-5\"）。"
        "改：replace_text 替换文字、set_notes 写备注、add_slide 加页、delete_slide 删页、"
        "move_slide 调顺序、add_textbox 加文本框、add_picture 插图。"
        "写操作会自动备份为 <文件名>.pptx.bak（已存在不覆盖）。"
        "不要用它读 PDF（pdf_convert）、不要读表格（table）。",
        {"action": {"type": "string", "enum": list(PPT_ACTIONS),
                    "description": "inspect/read 只读；其余为写操作"},
         "path": {"type": "string", "description": ".pptx 文件路径"},
         "slide": {"type": "integer", "description": "页码（1 基）；read/删/改 用"},
         "pages": {"type": "string", "description": "action=read：页码范围，如 2-5"},
         "old": {"type": "string", "description": "replace_text：被替换的原文"},
         "new": {"type": "string", "description": "replace_text：替换成的文字"},
         "text": {"type": "string", "description": "set_notes/add_textbox 的文本"},
         "to": {"type": "integer", "description": "move_slide：目标位置（1 基）"},
         "layout": {"type": "integer", "description": "add_slide：版式索引，留空用第二个"},
         "left": {"type": "integer", "description": "坐标（EMU，1 英寸=914400）"},
         "top": {"type": "integer", "description": "坐标（EMU）"},
         "width": {"type": "integer", "description": "尺寸（EMU）"},
         "height": {"type": "integer", "description": "尺寸（EMU）"},
         "picture": {"type": "string", "description": "add_picture：图片路径"}},
        ppt, ["action", "path"])
