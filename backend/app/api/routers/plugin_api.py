from __future__ import annotations

import json

from fastapi import APIRouter, Query, Request
from fastapi.responses import (FileResponse, JSONResponse, Response,
                               StreamingResponse)

from ...plugins import static_host

router = APIRouter()

_NO_STORE = {"Cache-Control": "no-store"}

pass
pass
pass
_ROUTE_QUERY_KEYS = frozenset({"id", "project", "path", "static"})


def _error(plugin_id: str, detail: str, status: int) -> JSONResponse:
    return JSONResponse({"error": {"plugin": plugin_id, "detail": detail}},
                        status_code=status, headers=_NO_STORE)


@router.api_route("/api/plugin", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def plugin_entry(request: Request,
                       plugin_id: str = Query("", alias="id"),
                       project: str = "",
                       static: str | None = None,
                       path: str = ""):
    from ..deps import get_container

    c = get_container(request)
    if path:
        return await _call_handler(c, plugin_id, project, path, request)
    return _serve_static(c, plugin_id, project, static)


async def _call_handler(c, plugin_id: str, project: str, path: str,
                        request: Request) -> Response:
    from ...plugins import resolve as resolver

    api_router = getattr(c, "plugin_api", None)
    if api_router is None:
        return _error(plugin_id, "未就绪", 503)
    try:
        pass
        pass
        resolver.resolve(c.installs, plugin_id, project)
    except resolver.PluginScopeError as e:
        return _error(plugin_id, e.detail, e.status)

    req = await _build_request(request, path)
    status, payload, is_stream = await api_router.invoke(plugin_id, project, req, c)
    if is_stream:
        return StreamingResponse(payload, media_type="text/event-stream")
    if isinstance(payload, (dict, list)) or payload is None:
        return JSONResponse(payload, status_code=status)
    return Response(payload if isinstance(payload, (str, bytes)) else str(payload),
                    status_code=status)


def _serve_static(c, plugin_id: str, project: str, static: str | None) -> Response:
    from ...plugins import resolve as resolver

    try:
        ctx = static_host.resolve_context(c.installs, plugin_id, project)
        target, suffix, is_binary = static_host.pick_file(ctx, static)
    except (static_host.StaticError, resolver.PluginScopeError) as e:
        return _error(plugin_id, e.detail, e.status)

    if is_binary:
        return FileResponse(target, headers=_NO_STORE)
    text = target.read_text("utf-8", errors="replace")
    return Response(
        static_host.render_text(text, ctx, suffix in static_host.HTML_SUFFIXES),
        media_type=static_host.media_type_of(target), headers=_NO_STORE)


async def _build_request(request: Request, rest: str) -> dict:
    body = await request.body()
    parsed_json = None
    if body:
        try:
            parsed_json = json.loads(body)
        except ValueError:
            parsed_json = None
    return {
        "method": request.method,
        "path": "/" + rest.lstrip("/"),
        "query": {k: v for k, v in request.query_params.items()
                  if k not in _ROUTE_QUERY_KEYS},
        "headers": dict(request.headers),
        "body": body,
        "json": parsed_json,
    }
