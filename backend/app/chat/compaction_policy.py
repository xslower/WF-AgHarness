from __future__ import annotations

import logging
from typing import Awaitable, Callable

from .compaction_kit import (FALLBACK_UNFINISHED_TURNS, get_strategy,
                             is_complete_assistant, unfinished_turns)
from .compaction_secondary import (RECOMPACT_LADDER, decide as _decide,
                                   save_state as _save_state)

logger = logging.getLogger("harness.compact.policy")

Emit = Callable[[dict], Awaitable[None]]

pass
COMPACT_LADDER = RECOMPACT_LADDER


def turn_interrupted(session: dict) -> bool:
    msgs = session.get("messages") or []
    last_user = -1
    for i in range(len(msgs) - 1, -1, -1):
        if isinstance(msgs[i], dict) and msgs[i].get("role") == "user":
            last_user = i
            break
    if last_user < 0:
        return False
    return not any(is_complete_assistant(m) for m in msgs[last_user + 1:])


async def maybe_compact(c, session: dict, model: str, emit: Emit) -> None:
    pass
    pass
    pass
    pass
    pass
    if (turn_interrupted(session)
            and unfinished_turns(session.get("messages") or [])
            < FALLBACK_UNFINISHED_TURNS):
        return
    sid = session["id"]
    names = getattr(c.store.config.settings, "compactStrategies", None)
    if not names:
        names = ["memo", "secondary"]
    for name in names:
        strategy = get_strategy(name)
        await strategy.compact(c, sid, emit, session=session, model=model)
