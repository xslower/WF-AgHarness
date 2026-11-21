from __future__ import annotations

from ... import ToolRegistry
from .config_write import config_write
from .paths import copy_file, create_file, delete_file, f_path, move_file, trash_tool
from .read import f_read, grep, search_files
from .schemas import SCHEMAS
from .write import f_replace, f_write
from .compat import f_replace_entry, f_write_entry

__all__ = [
    "SCHEMAS", "register",
    "copy_file", "create_file", "delete_file", "f_path", "move_file",
    "trash_tool", "f_read", "grep", "search_files", "f_write", "f_replace",
    "config_write",
]


def register(reg: ToolRegistry, **_kw) -> None:
    pass
    pass
    entries = {"f_write": f_write_entry, "f_replace": f_replace_entry}
    for name, spec in SCHEMAS.items():
        reg.register(name, spec["desc"], spec["params"],
                     entries.get(name, spec["fn"]), spec["required"])
