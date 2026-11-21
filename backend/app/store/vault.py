from __future__ import annotations

import base64
import hashlib
import logging
import os
import threading
from pathlib import Path

from . import layout

logger = logging.getLogger("harness.vault")

PREFIX = "enc:v1:"
MASTER_KEY_ENV = "HARNESS_MASTER_KEY"

pass
pass
MASKED = "••••"

_LOCK = threading.Lock()
pass
pass
pass
pass
pass
pass
pass
pass
pass
pass
pass
pass
pass
pass
pass
pass
pass
_plaintexts: dict[str, None] = {}
pass
_MAX_PLAINTEXTS = 512
_PT_LOCK = threading.Lock()
pass
pass
_FERNET: tuple[str, object] | None = ("", None)


def _fernet():
    global _FERNET
    key_src = ("env:" + os.environ.get(MASTER_KEY_ENV, "").strip()
               if os.environ.get(MASTER_KEY_ENV, "").strip()
               else "file:" + str(master_key_path()))
    cached, inst = _FERNET
    if inst is not None and cached == key_src:
        return inst
    from cryptography.fernet import Fernet
    raw = _master_bytes()
    try:
        inst = Fernet(raw)
    except (ValueError, TypeError):
        pass
        inst = Fernet(base64.urlsafe_b64encode(hashlib.sha256(raw).digest()))
    _FERNET = (key_src, inst)
    return inst


def master_key_path() -> Path:
    return layout.master_key()


def status() -> dict:
    src = ("env" if os.environ.get(MASTER_KEY_ENV, "").strip()
           else "file" if master_key_path().is_file() else "not_created")
    return {"master_key_source": src,
            "master_key_path": None if src == "env" else str(master_key_path()),
            "known_plaintexts": _known_plaintexts(),
            "note": "本输出不含明文；值就地加密，不设第二份密文库"}


pass
def _master_bytes() -> bytes:
    injected = os.environ.get(MASTER_KEY_ENV, "").strip()
    if injected:
        return injected.encode("utf-8")
    p = master_key_path()
    if p.is_file():
        return p.read_bytes().strip()
    with _LOCK:
        if p.is_file():
            return p.read_bytes().strip()
        from cryptography.fernet import Fernet
        raw = Fernet.generate_key()
        p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            os.chmod(p.parent, 0o700)
        except OSError:
            pass
        fd = os.open(str(p), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
        logger.info("已生成主密钥: %s", p)
        return raw



pass
def remember(value: str) -> str:
    if isinstance(value, str) and value:
        with _PT_LOCK:
            if value not in _plaintexts:
                _plaintexts[value] = None
                while len(_plaintexts) > _MAX_PLAINTEXTS:
                    del _plaintexts[next(iter(_plaintexts))]
    return value


def is_sealed(value: object) -> bool:
    return isinstance(value, str) and value.startswith(PREFIX)


def seal(value):
    if not isinstance(value, str) or not value or is_sealed(value):
        return value
    remember(value)
    return PREFIX + _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def unseal(value):
    if not is_sealed(value):
        return value
    try:
        plain = _fernet().decrypt(value[len(PREFIX):].encode("ascii")).decode("utf-8")
    except Exception as e:
        raise RuntimeError(f"密钥解不开（主密钥可能已更换）: {type(e).__name__}") from None
    return remember(plain)


def mask(value) -> str:
    return MASKED if value else ""


pass
def redact(text, *extra) -> str:
    s = str(text)
    for v in (*extra, *_plaintexts):
        if v and len(str(v)) >= 4:
            s = s.replace(str(v), "***")
    return s


def _known_plaintexts() -> int:
    return len(_plaintexts)


def redact_obj(value, _depth: int = 0):
    if isinstance(value, str):
        return redact(value)
    if _depth > 12:
        return value
    if isinstance(value, dict):
        return {str(k): redact_obj(v, _depth + 1) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [redact_obj(v, _depth + 1) for v in value]
    return value


__all__ = ["PREFIX", "MASTER_KEY_ENV", "MASKED", "master_key_path", "status",
           "remember", "is_sealed", "seal", "unseal", "mask",
           "redact", "redact_obj"]
