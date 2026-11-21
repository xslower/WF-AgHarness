
import os
from urllib.parse import quote, urlsplit, urlunsplit


def redis_auth_from_config(config: dict) -> tuple[str, str]:
    rc = config.get("redis", {})
    username = os.environ.get("REDIS_USERNAME", rc.get("username", "default")) or "default"
    password = os.environ.get("REDIS_PASSWORD", rc.get("password", "")) or ""
    return str(username), str(password)


def redis_auth_netloc(username: str, password: str) -> str:
    if not password:
        return ""
    return f"{quote(username, safe='')}:{quote(password, safe='')}@"


def build_redis_url(config: dict) -> str:
    rc = config.get("redis", {})
    host = os.environ.get("REDIS_HOST", rc.get("host", "localhost"))
    port = os.environ.get("REDIS_PORT", rc.get("port", 6379))
    username, password = redis_auth_from_config(config)
    db = rc.get("db", 0)
    scheme = "rediss" if rc.get("ssl", False) else "redis"
    auth = redis_auth_netloc(username, password)
    return f"{scheme}://{auth}{host}:{port}/{db}"


def build_rate_limit_storage_uri(config: dict) -> str:
    storage_uri = config.get("rate_limiting", {}).get("storage_uri", "memory://")
    if not isinstance(storage_uri, str):
        return "memory://"
    parsed = urlsplit(storage_uri)
    if parsed.scheme not in {"redis", "rediss", "redis+sentinel"}:
        return storage_uri
    if parsed.username or parsed.password:
        return storage_uri

    username, password = redis_auth_from_config(config)
    if not password:
        return storage_uri

    auth = redis_auth_netloc(username, password)
    return urlunsplit((
        parsed.scheme,
        f"{auth}{parsed.netloc}",
        parsed.path,
        parsed.query,
        parsed.fragment,
    ))
