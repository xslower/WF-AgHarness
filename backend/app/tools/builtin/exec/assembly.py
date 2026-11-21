from __future__ import annotations

from ... import ToolRegistry
from .shell import run_command, register as _register

__all__ = ["run_command", "register"]


def register(reg: ToolRegistry) -> None:
    _register(reg)
