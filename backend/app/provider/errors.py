from __future__ import annotations


class RateLimitedError(Exception):
    pass


class EmptyResponseError(Exception):
    pass


class StreamFrameError(Exception):

    def __init__(self, detail: str, raw: str = "", frame_bytes: int = 0) -> None:
        super().__init__(detail)
        self.detail = detail
        self.raw = raw
        self.frame_bytes = frame_bytes
