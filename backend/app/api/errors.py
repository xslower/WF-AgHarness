from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException

from ..workflow.errors import ERROR_STATUS as _KIND_STATUS

logger = logging.getLogger("harness.api")


def _make(status: int, detail: Any) -> HTTPException:
    from ..store import vault
    clean = vault.redact_obj(detail)
    return HTTPException(status_code=status, detail=clean)


def bad_request(detail: Any) -> HTTPException:
    return _make(400, detail)


def forbidden(detail: Any) -> HTTPException:
    return _make(403, detail)


def not_found(detail: Any) -> HTTPException:
    return _make(404, detail)


def conflict(detail: Any) -> HTTPException:
    return _make(409, detail)


def server_error(detail: Any) -> HTTPException:
    return _make(500, detail)


def bad_gateway(detail: Any) -> HTTPException:
    return _make(502, detail)


_BY_STATUS = {
    400: bad_request,
    403: forbidden,
    404: not_found,
    409: conflict,
    500: server_error,
    502: bad_gateway,
}


def http_error(status: int, detail: Any) -> HTTPException:
    return _BY_STATUS.get(status, bad_request)(detail)


def from_error(e: Exception, *, prefix: str = "", status: int = 0) -> HTTPException:
    logger.warning("%s%s: %s", prefix, type(e).__name__, e, exc_info=True)
    if status:
        return _make(status, str(e))
    kind = getattr(e, "kind", "")
    return _make(_KIND_STATUS.get(kind, 400), str(e))
