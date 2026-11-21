# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable


def resolve_doc(path: str, cwd: str, abs_path: Callable,
                fail: Callable, suffix_ok: Callable[[Path], str | None]
                ) -> tuple[Path | None, str | None]:
    if not path:
        return None, fail("bad_args", "path 必填")
    p = abs_path(path, cwd)
    if not p.is_file():
        return None, fail("not_found", f"文件不存在: {p}")
    msg = suffix_ok(p)
    if msg:
        return None, fail("unsupported", msg)
    return p, None


def finish_doc(out: dict, p: Path, action: str) -> str:
    out.setdefault("path", str(p))
    out.setdefault("action", action)
    return json.dumps(out, ensure_ascii=False)
