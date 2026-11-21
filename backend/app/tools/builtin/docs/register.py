from __future__ import annotations

from ... import ToolRegistry
import app.tools.builtin.docs.docfile as docfile
import app.tools.builtin.docs.ppt as ppt
import app.tools.builtin.docs.table as table

__all__ = ["register", "docfile", "ppt", "table"]


def register(reg: ToolRegistry) -> None:
    table.register(reg)
    ppt.register(reg)
