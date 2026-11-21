from __future__ import annotations
import logging
from typing import Any, Callable
from ..store import event_log
log = logging.getLogger(__name__)
pass
Emit = Callable[[dict], Any]
def journal(sid: str, project: str, ev: dict) -> int:
    try:
        seq = event_log.next_seq(sid, project)
    except Exception:
        log.debug("event seq failed", exc_info=True)
        return 0
    ev["_i"] = seq
    try:
        pass
        pass
        pass
        event_log.append_async(project, sid, seq, ev)
    except Exception:
        log.debug("event log write failed", exc_info=True)
    return seq
