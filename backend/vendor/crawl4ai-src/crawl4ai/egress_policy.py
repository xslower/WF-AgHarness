
from typing import Optional

_proxy_url: Optional[str] = None


def set_egress_proxy(url: Optional[str]) -> None:
    global _proxy_url
    _proxy_url = url


def proxy_url() -> Optional[str]:
    return _proxy_url
