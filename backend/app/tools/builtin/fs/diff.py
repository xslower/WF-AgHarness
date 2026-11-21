from __future__ import annotations

from .text import Row

pass
ECHO_FULL_MAX = 5


def ctx_slice(rows: list[Row], lo: int, hi: int) -> list[tuple[int, str]]:
    return [(i + 1, rows[i].content[:120]) for i in range(lo, min(hi, len(rows)))]


def render_block(start: int, end: int, orig: list[str], new: list[str],
                 ctx_before: list[tuple[int, str]] | None = None,
                 ctx_after: list[tuple[int, str]] | None = None) -> str:
    out: list[str] = []
    for ln, txt in (ctx_before or []):
        out.append(f"  {ln}| {txt}")
    if orig:
        out.append(f"原第 {start}~{end} 行：")
        for i, line in enumerate(orig[:20]):
            out.append(f"  {start + i}| {line}")
        if len(orig) > 20:
            out.append(f"  …（原共 {len(orig)} 行）")
    out.append("改为：" if orig else "插入：")
    if len(new) < ECHO_FULL_MAX:
        for line in new:
            out.append(f"  | {line}")
    else:
        for line in new[:2]:
            out.append(f"  | {line}")
        out.append("  。。。")
        for line in new[-2:]:
            out.append(f"  | {line}")
    for ln, txt in (ctx_after or []):
        out.append(f"  {ln}| {txt}")
    return "\n".join(out)
