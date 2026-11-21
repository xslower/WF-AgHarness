from __future__ import annotations

from typing import Callable, TypeVar

H = TypeVar("H", bound=Callable)


def unsubscribe_in(subs: dict, topic: str, handler: H | None,
                    key: str) -> None:
    bucket = subs.get(topic)
    if not bucket:
        return
    unsubscribe(bucket, subs, topic, handler, key)


def unsubscribe(bucket: list[tuple[str, H]], subs: dict,
                topic: str, handler: H | None, key: str) -> None:
    if handler is None and not key:
        subs.pop(topic, None)
        return
    if key:
        bucket[:] = [(k, h) for k, h in bucket if k != key]
    else:
        bucket[:] = [(k, h) for k, h in bucket if h is not handler]
    if not bucket:
        subs.pop(topic, None)
