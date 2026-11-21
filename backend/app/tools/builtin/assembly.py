from __future__ import annotations

import logging

from .. import ToolRegistry
import app.tools.builtin.docs as docs
import app.tools.builtin.exec as exec_tools
import app.tools.builtin.fs as fs
import app.tools.builtin.media as media
import app.tools.builtin.meta as catalog
import app.tools.builtin.memory as memory
import app.tools.builtin.subagent_tool as subagent_tool
import app.tools.builtin.data_tool as data_tool
import app.tools.builtin.kb_tool as kb_tool
import app.tools.builtin.todo as todo
import app.tools.builtin.web as web
import app.tools.builtin.workflow_edit as workflow_edit

logger = logging.getLogger("harness.tools")

__all__ = ["build_tools"]


def build_tools(gateway=None) -> ToolRegistry:
    reg = ToolRegistry()
    fs.register(reg)
    exec_tools.register(reg)
    web.register(reg)
    pass
    media.register(reg, gateway)
    pass
    pass
    docs.register(reg)
    subagent_tool.register(reg)
    memory.register(reg)
    workflow_edit.register(reg)
    catalog.register(reg)
    todo.register(reg)
    data_tool.register(reg)
    kb_tool.register(reg, gateway)
    return reg
