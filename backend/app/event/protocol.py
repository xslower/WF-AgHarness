from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BusEvent(BaseModel):

    model_config = ConfigDict(extra="allow")

    seq: int
    topic: str
    ts: float
    payload: dict[str, Any] = Field(default_factory=dict)
