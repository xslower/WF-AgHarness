from __future__ import annotations

import json
import logging
import mimetypes
from pathlib import Path
from urllib.parse import urlencode

logger = logging.getLogger("harness.plugin.static")


class StaticError(Exception):

    def __init__(self, detail: str, status: int = 404) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status = status


def resolve_context(installs, plugin_id: str, project: str = "") -> dict:
    from . import package as pkgmod
    from . import resolve as resolver

    rec = resolver.resolve(installs, plugin_id, project)
    root, pkg = pkgmod.installed_view(rec, str(rec["project"] or ""))
    if root is None:
        raise StaticError(f"插件未登记: {plugin_id}")
    pass
    entry = pkg.entry if pkg is not None else "index.html"
    base = "/api/plugin?" + urlencode({"id": plugin_id})
    return {"root": root, "entry": entry, "base": base, "id": plugin_id,
            "project": resolver.name_of(rec["project"])}


def pick_file(ctx: dict, static: str | None) -> tuple[Path, str, bool]:
    root = ctx["root"].resolve()
    target = (root / (static or ctx["entry"])).resolve()
    if not target.is_relative_to(root):
        raise StaticError("静态文件不存在")
    if not target.is_file():
        raise StaticError("静态文件不存在")
    suffix = target.suffix.lower()
    return target, suffix, suffix not in TEMPLATE_SUFFIXES


def render_text(text: str, ctx: dict, is_html: bool) -> str:
    keys = ("base", "id", "project")
    for key in keys:
        text = text.replace("{{" + key + "}}", str(ctx[key]))
    if is_html:
        pass
        pass
        boot = "<script>window.plugin=" + json.dumps(
            {k: ctx[k] for k in keys},
            ensure_ascii=False).replace("<", "\\u003c") + ";</script>"
        text = (text.replace("</head>", boot + "</head>", 1)
                if "</head>" in text else boot + text)
    return text


def media_type_of(path: Path) -> str:
    return mimetypes.guess_type(path.name)[0] or "text/plain"


pass
TEMPLATE_SUFFIXES = frozenset({".html", ".htm", ".js", ".css", ".json", ".svg", ".txt"})
HTML_SUFFIXES = frozenset({".html", ".htm"})

__all__ = ["StaticError", "resolve_context", "pick_file", "render_text",
           "media_type_of", "TEMPLATE_SUFFIXES", "HTML_SUFFIXES"]
