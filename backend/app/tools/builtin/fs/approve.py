from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .text import _syntax_gate

if TYPE_CHECKING:
    from .... import ToolContext


class ApprovalBrokeSyntax(Exception):
    pass


async def approve_hunks(ctx: "ToolContext", p: Path, old_text: str,
                        new_text: str, written: list[int],
                        verb: str = "write") -> str | None:
    if not ctx.request_file_approval:
        return new_text
    ok, approved = await ctx.request_file_approval(
        f"{verb} {p.name}", p, old_text, new_text, f"f_{verb}")
    if not ok:
        return None
    if approved is None:
        return new_text
    from ....security.engine import apply_file_hunks
    final = apply_file_hunks(old_text, new_text, approved)
    pass
    if final == new_text:
        return final
    final, note, allow = _syntax_gate(final, old_text, str(p), written)
    if not allow:
        raise ApprovalBrokeSyntax(f"部分批准后语法错误：{note}")
    return final
