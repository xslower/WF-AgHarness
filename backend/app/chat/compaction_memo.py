from __future__ import annotations

from .compaction_secondary import (
    CONDENSE_NEXT_SEGS, DROP_SECTIONS, KEEP_RECENT_SEGS, LEGACY_CHARS,
    RECOMPACT_LADDER, SHORT_SECTION_CHARS, SHORT_SECTIONS,
    SecondaryStrategy, _condense_text, condense_items, decide, plan_secondary,
    used_text)

__all__ = ["RECOMPACT_LADDER", "plan_secondary", "condense_items",
           "SecondaryStrategy", "decide", "used_text"]
