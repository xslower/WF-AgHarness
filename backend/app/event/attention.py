from __future__ import annotations

import logging

logger = logging.getLogger("harness.attention")

TOPIC = "session.attention"


def notify(sid: str = "", reason: str = "", **extra) -> None:
    try:
        from .bus import HUB
        HUB.publish(TOPIC, {"sid": sid, "reason": reason, **extra})
    except Exception:
        logger.debug("发布 %s 失败: sid=%s reason=%s", TOPIC, sid, reason, exc_info=True)
