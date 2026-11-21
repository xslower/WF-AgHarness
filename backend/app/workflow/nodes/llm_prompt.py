from __future__ import annotations

import glob
from pathlib import Path
from typing import Any

pass
pass
pass
REF_MARK = "的输出已落盘"

pass
_DOC_SUFFIXES = (".md", ".txt", ".yaml", ".yml", ".json")

pass
_DOC_MAX_CHARS = 60000


def resolve_docs(entry: str, workspace: str) -> tuple[list[Path], Path]:
    base = Path(workspace) if workspace else Path.cwd()
    pat = Path(entry).expanduser()
    if not pat.is_absolute():
        pat = base / pat
    text = str(pat)
    if any(ch in text for ch in "*?["):
        hits = [Path(p) for p in sorted(glob.glob(text, recursive=True))
                if Path(p).is_file()]
        return hits, pat
    if pat.is_dir():
        hits = sorted(p for p in pat.iterdir()
                      if p.is_file() and p.suffix.lower() in _DOC_SUFFIXES)
        return hits, pat
    return ([pat] if pat.is_file() else []), pat


def load_docs_parts(entries, ctx: Any, workspace: str) -> list[str]:
    parts: list[str] = []
    for entry in (p.strip() for p in entries.splitlines()):
        if not entry:
            continue
        hits, resolved = resolve_docs(entry, workspace)
        if not hits:
            pass
            parts.append(f"[文档: {entry} → {resolved} 不存在]"
                         "（相对路径按工作目录解析）")
            continue
        for fp in hits:
            try:
                body = fp.read_text(encoding="utf-8", errors="replace")[:_DOC_MAX_CHARS]
                parts.append(f"[文档: {fp.name}]\n{body}")
            except Exception as e:
                parts.append(f"[文档: {fp} 读取失败: {e}]")
    return parts


def format_instruction(fmt: str, fields: str, fence_prompt) -> str:
    if fmt == "json":
        return ("\n\n[字段] " + (fields or "（自行合理设计）")
                + "\n顶层数组也接受（分镜列表这类直接用数组更自然）。"
                + fence_prompt("json"))
    if fmt == "yaml":
        return (f"\n\n[结构] {fields}" if fields else "") + fence_prompt("yaml")
    if fmt == "list":
        return "\n\n[输出要求] 只输出列表，每行一项，不要编号、不要多余文字。"
    return ""


def ref_warning_for(prompt: str, tools_cfg: str) -> str:
    if REF_MARK in prompt and tools_cfg in ("off", "none"):
        return ("[警告] 上文含落盘引用（长输出已写成文件），但本节点 tools=off，"
                "无法读取全文；只能基于预览作答。需要全文请给本节点开 tools。\n")
    return ""


def build_prompt(node: dict, ctx: Any, vars: dict, *, fence_prompt) -> tuple[str, str]:
    fmt = node.get("format", "text")
    fields = ctx.sub(node.get("jsonFields", ""), vars) if fmt in ("json", "yaml") else ""
    pass
    prompt = ctx.sub(node["prompt"], vars, long_ref=True)

    tools_cfg = str(node.get("tools", "auto") or "auto").strip()
    warning = ref_warning_for(prompt, tools_cfg)

    docs_raw = node.get("docs", "")
    if docs_raw:
        workspace = getattr(ctx, "workspace", "") or ""
        parts = load_docs_parts(ctx.sub(docs_raw, vars), ctx, workspace)
        if parts:
            prompt = "\n\n".join(parts) + "\n\n---\n\n" + prompt

    prompt += format_instruction(fmt, fields, fence_prompt)
    return prompt, warning
