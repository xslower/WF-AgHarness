
import hmac
import logging
import os
import secrets as _secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import jwt
from fastapi import HTTPException, Request
from pydantic import BaseModel, EmailStr

ACCESS_TOKEN_EXPIRE_MINUTES = 60
ALGORITHM = "HS256"
_ALGORITHMS = [ALGORITHM]

_WEAK_SECRETS = {"mysecret", "secret", "password", "changeme", "test", "12345678"}
_MIN_SECRET_LEN = 32

_log = logging.getLogger("crawl4ai.security")


def resolve_secret_key(*, required: bool) -> str:
    key = os.environ.get("SECRET_KEY", "")
    if key:
        if key.lower() in _WEAK_SECRETS:
            raise RuntimeError(
                "FATAL: SECRET_KEY is a known weak value. Generate a strong one: "
                'python3 -c "import secrets; print(secrets.token_hex(32))"'
            )
        if len(key) < _MIN_SECRET_LEN:
            raise RuntimeError(
                f"FATAL: SECRET_KEY must be at least {_MIN_SECRET_LEN} characters. "
                'Generate one: python3 -c "import secrets; print(secrets.token_hex(32))"'
            )
        return key

    if required:
        raise RuntimeError(
            "FATAL: authentication is enabled but SECRET_KEY is not set. "
            'Set it: SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")'
        )

    generated = _secrets.token_hex(32)
    _log.warning(
        "No SECRET_KEY set. Auto-generated an ephemeral key (changes on restart, "
        "invalidating issued tokens). Set SECRET_KEY for any real deployment."
    )
    return generated


pass
pass
pass
SECRET_KEY = resolve_secret_key(required=False)


def create_access_token(
    data: dict,
    *,
    scope: str = "data",
    expires_delta: Optional[timedelta] = None,
) -> str:
    to_encode = dict(data)
    to_encode["scope"] = scope
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Dict:
    return jwt.decode(token, SECRET_KEY, algorithms=_ALGORITHMS)


def constant_time_eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def get_principal(request: Request) -> Optional[Dict]:
    return getattr(request.state, "principal", None)


def get_token_dependency(config: Dict):

    def _principal(request: Request) -> Optional[Dict]:
        return get_principal(request)

    return _principal


def require_admin(request: Request) -> Dict:
    principal = get_principal(request)
    if not principal or principal.get("scope") != "admin":
        raise HTTPException(status_code=403, detail="Admin scope required")
    return principal


class TokenRequest(BaseModel):
    email: EmailStr
    api_token: Optional[str] = None
