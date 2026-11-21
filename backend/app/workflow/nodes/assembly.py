from __future__ import annotations

from .registry import NodeRegistry


def build_default_nodes() -> NodeRegistry:
    from . import (exec as exec_nodes, flow, human, io, llm, mcp, op, subagent,
                   tool, web, workflow)
    reg = NodeRegistry()
    for module in (llm, io, exec_nodes, web, mcp, subagent, flow, human,
                   workflow, tool, op):
        module.register(reg)
    return reg


__all__ = ["build_default_nodes"]
