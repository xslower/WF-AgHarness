from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .fsx import ensure_parent

logger = logging.getLogger("harness.jsonx")


pass
pass
pass


def dumps(data: Any, *, indent: int | None = None) -> str:
    return json.dumps(data, ensure_ascii=False, indent=indent)


def err(message: Any, **extra: Any) -> str:
    payload: dict[str, Any] = {"error": message}
    payload.update(extra)
    return dumps(payload)


def ok(**fields: Any) -> str:
    return dumps({"ok": True, **fields})


def is_err(text: Any) -> bool:
    return isinstance(text, str) and text.lstrip().startswith('{"error"')


pass
pass
pass
pass

from .jsonfix import (
    ScenePolicy,
    RepairResult,
    close_open_structs,
    drop_incomplete_tail,
    json_error_detail,
    loads_lenient,
    parse_tool_args,
    parse_tool_args_report,
    repair,
    repair_long_value,
    scene_for_tool,
    stats as fix_stats,
    valid_tool_args,
)

pass
pass
pass


def write_json(path: Path | str, data: Any, *, indent: int | None = 2) -> None:
    p = ensure_parent(path)
    tmp = p.with_name(f".{p.name}.tmp")
    tmp.write_text(dumps(data, indent=indent), "utf-8")
    tmp.replace(p)


def read_json(path: Path | str, default: Any = None) -> Any:
    try:
        return json.loads(Path(path).read_text("utf-8"))
    except (OSError, ValueError):
        return default


def append_jsonl(path: Path | str, item: Any) -> bool:
    try:
        p = ensure_parent(path)
        with p.open("a", encoding="utf-8") as f:
            f.write(dumps(item) + "\n")
        return True
    except (OSError, TypeError, ValueError):
        return False


def append_text_line(path: Path | str, text: str) -> bool:
    try:
        p = ensure_parent(path)
        with p.open("a", encoding="utf-8") as f:
            f.write(text.rstrip("\n") + "\n")
        return True
    except OSError:
        return False


def write_jsonl(path: Path | str, items: list[Any]) -> bool:
    try:
        p = ensure_parent(path)
        text = "".join(dumps(x) + "\n" for x in items)
        tmp = p.with_name(f".{p.name}.tmp")
        tmp.write_text(text, "utf-8")
        tmp.replace(p)
        return True
    except (OSError, TypeError, ValueError):
        return False


def read_jsonl(path: Path | str) -> list[Any]:
    p = Path(path)
    if not p.is_file():
        return []
    out: list[Any] = []
    try:
        text = p.read_text("utf-8", errors="replace")
    except OSError:
        return []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out
