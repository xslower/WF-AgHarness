# -*- coding: utf-8 -*-
from __future__ import annotations

import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from ....util.jsonx import err

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

# Word 内置样式名 → markdown 标题级别
_HEAD = {"title": 1, "subtitle": 2,
         "heading1": 1, "heading2": 2, "heading3": 3,
         "heading4": 4, "heading5": 5, "heading6": 6}


def _text_of(el: ET.Element) -> str:
    buf: list[str] = []
    for node in el.iter():
        tag = node.tag
        if tag == f"{W}t":
            buf.append(node.text or "")
        elif tag == f"{W}tab":
            buf.append("\t")
        elif tag in (f"{W}br", f"{W}cr"):
            buf.append("\n")
    return "".join(buf)


def _style_level(p: ET.Element) -> int:
    ppr = p.find(f"{W}pPr")
    if ppr is None:
        return 0
    st = ppr.find(f"{W}pStyle")
    if st is None:
        return 0
    val = (st.get(f"{W}val") or "").strip().lower()
    if val in _HEAD:
        return _HEAD[val]
    # 有些模板用 "1"/"2" 或 "Heading1Char" 这类变体
    if val.endswith("char"):
        val = val[:-4]
    if val in _HEAD:
        return _HEAD[val]
    for k, lv in _HEAD.items():
        if val.startswith(k):
            return lv
    return 0


def _table_md(tbl: ET.Element) -> list[str]:
    rows: list[list[str]] = []
    for tr in tbl.findall(f"{W}tr"):
        cells = []
        for tc in tr.findall(f"{W}tc"):
            cells.append(" ".join(_text_of(tc).split()))
        rows.append(cells)
    if not rows:
        return []
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    out = ["| " + " | ".join(rows[0]) + " |",
           "| " + " | ".join(["---"] * width) + " |"]
    out += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return out


def docx_to_text(p: Path) -> str:
    try:
        with zipfile.ZipFile(p) as z:
            xml = z.read("word/document.xml")
    except KeyError:
        raise ValueError("不是有效的 .docx（缺 word/document.xml）")
    except zipfile.BadZipFile:
        raise ValueError("不是有效的 .docx（zip 结构损坏）")

    root = ET.fromstring(xml)
    body = root.find(f"{W}body")
    if body is None:
        return ""

    lines: list[str] = []
    for child in body:
        if child.tag == f"{W}p":
            txt = _text_of(child).strip()
            lv = _style_level(child)
            if not txt:
                continue
            lines.append(f"{'#' * lv} {txt}" if lv else txt)
        elif child.tag == f"{W}tbl":
            md = _table_md(child)
            if md:
                if lines and lines[-1] != "":
                    lines.append("")
                lines.extend(md)
                lines.append("")
    return "\n".join(lines)


def read_docx(p: Path, offset: int = 0, limit: int = 2000) -> str:
    import json
    try:
        text = docx_to_text(p)
    except ValueError as e:
        return err(str(e))
    rows = text.splitlines()
    sel = rows[offset: offset + limit]
    body = "\n".join(f"{i + offset + 1}\t{l}" for i, l in enumerate(sel))
    if not body:
        return "(空文档)"
    head = (f"<!-- docx 共 {len(rows)} 行，本次 offset={offset} limit={limit} -->\n")
    return head + body


def docx_info(p: Path) -> dict:
    try:
        text = docx_to_text(p)
    except ValueError as e:
        return {"error": str(e)}
    rows = text.splitlines()
    return {
        "lines": len(rows),
        "chars": len(text),
        "headings": sum(1 for r in rows if r.startswith("#")),
        "tables": sum(1 for r in rows if r.startswith("| ")),
    }
