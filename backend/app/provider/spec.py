
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

pass
QUEUE_PARENT = "parent"
QUEUE_CHILD = "child"
QUEUE_SUMMARY = "summary"
QUEUE_NAMES: tuple[str, ...] = (QUEUE_PARENT, QUEUE_CHILD, QUEUE_SUMMARY)

pass
pass
pass
STREAM_TIMEOUT_SEC = 600.0
CONNECT_TIMEOUT_SEC = 30.0

pass
pass
SUBAGENT_WAIT_TIMEOUT_SEC = 300.0
SUBAGENT_WAIT_TIMEOUT_MAX_SEC = 1800.0

class SpecKind(str, Enum):

    AUTO = "auto"
    QUEUE = "queue"
    MODEL = "model"
    INVALID = "invalid"


@dataclass(frozen=True)
class ModelSpec:
    raw: str
    kind: SpecKind
    provider: str = ""
    model: str = ""

    pass

    @classmethod
    def parse(cls, raw: str | None) -> "ModelSpec":
        s = (raw or "").strip()
        if not s:
            return cls(raw="", kind=SpecKind.AUTO)
        if s in QUEUE_NAMES:
            return cls(raw=s, kind=SpecKind.QUEUE)
        i = s.find("/")
        if i <= 0 or i == len(s) - 1:
            pass
            pass
            return cls(raw=s, kind=SpecKind.INVALID)
        return cls(raw=s, kind=SpecKind.MODEL,
                   provider=s[:i], model=s[i + 1:])

    @classmethod
    def of(cls, provider: str, model: str) -> "ModelSpec":
        p = (provider or "").strip()
        m = (model or "").strip()
        if not p or not m:
            return cls(raw="", kind=SpecKind.INVALID)
        return cls(raw=f"{p}/{m}", kind=SpecKind.MODEL, provider=p, model=m)

    @classmethod
    def queue(cls, name: str) -> "ModelSpec":
        return cls.parse(name if name in QUEUE_NAMES else "parent")

    @classmethod
    def auto(cls) -> "ModelSpec":
        return cls.parse("")

    pass

    @property
    def is_auto(self) -> bool:
        return self.kind is SpecKind.AUTO

    @property
    def is_queue(self) -> bool:
        return self.kind is SpecKind.QUEUE

    @property
    def is_model(self) -> bool:
        return self.kind is SpecKind.MODEL

    def __str__(self) -> str:
        return self.raw

    def __bool__(self) -> bool:
        return bool(self.raw)


def queue_of(raw: str | None) -> str:
    s = ModelSpec.parse(raw)
    return s.raw if s.is_queue else QUEUE_PARENT
