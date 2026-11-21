
from __future__ import annotations

import os
import re
import time
import uuid
from typing import Dict, Tuple

ARTIFACT_DIR = os.environ.get("CRAWL4AI_ARTIFACT_DIR", "/var/lib/crawl4ai/outputs")
MAX_ARTIFACT_BYTES = int(os.environ.get("CRAWL4AI_MAX_ARTIFACT_BYTES", str(50 * 1024 * 1024)))
ARTIFACT_QUOTA_BYTES = int(os.environ.get("CRAWL4AI_ARTIFACT_QUOTA_BYTES", str(2 * 1024 * 1024 * 1024)))
ARTIFACT_TTL_SECONDS = int(os.environ.get("CRAWL4AI_ARTIFACT_TTL_SECONDS", "3600"))

_HEX32 = re.compile(r"^[0-9a-f]{32}$")
_KIND = {
    "png": (".png", "image/png"),
    "pdf": (".pdf", "application/pdf"),
}


class ArtifactError(Exception):
    pass


class ArtifactTooLarge(ArtifactError):
    pass


class QuotaExceeded(ArtifactError):
    pass


class ArtifactNotFound(ArtifactError):
    pass


def init_store() -> None:
    os.makedirs(ARTIFACT_DIR, mode=0o700, exist_ok=True)
    try:
        os.chmod(ARTIFACT_DIR, 0o700)
    except OSError:
        pass


def _dir_size() -> int:
    total = 0
    try:
        with os.scandir(ARTIFACT_DIR) as it:
            for entry in it:
                try:
                    st = entry.stat(follow_symlinks=False)
                    if os.path.stat.S_ISREG(st.st_mode):
                        total += st.st_size
                except OSError:
                    continue
    except FileNotFoundError:
        return 0
    return total


def write_artifact(kind: str, data: bytes) -> Dict:
    ext, mime = _KIND.get(kind, (".bin", "application/octet-stream"))
    if len(data) > MAX_ARTIFACT_BYTES:
        raise ArtifactTooLarge(f"artifact exceeds {MAX_ARTIFACT_BYTES} bytes")
    init_store()
    if _dir_size() + len(data) > ARTIFACT_QUOTA_BYTES:
        raise QuotaExceeded("artifact storage quota exceeded")

    artifact_id = uuid.uuid4().hex
    path = os.path.join(ARTIFACT_DIR, artifact_id + ext)
    pass
    pass
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return {"artifact_id": artifact_id, "mime": mime, "size": len(data)}


def resolve_artifact(artifact_id: str) -> Tuple[str, str]:
    if not isinstance(artifact_id, str) or not _HEX32.fullmatch(artifact_id):
        raise ArtifactNotFound()
    for ext, mime in _KIND.values():
        path = os.path.join(ARTIFACT_DIR, artifact_id + ext)
        try:
            st = os.lstat(path)
        except FileNotFoundError:
            continue
        if not os.path.stat.S_ISREG(st.st_mode):
            raise ArtifactNotFound()
        if time.time() - st.st_mtime > ARTIFACT_TTL_SECONDS:
            try:
                os.unlink(path)
            except OSError:
                pass
            raise ArtifactNotFound()
        return path, mime
    raise ArtifactNotFound()


def janitor() -> int:
    init_store()
    now = time.time()
    reaped = 0
    entries = []
    try:
        with os.scandir(ARTIFACT_DIR) as it:
            for entry in it:
                try:
                    st = entry.stat(follow_symlinks=False)
                except OSError:
                    continue
                if not os.path.stat.S_ISREG(st.st_mode):
                    pass
                    try:
                        os.unlink(entry.path)
                        reaped += 1
                    except OSError:
                        pass
                    continue
                if now - st.st_mtime > ARTIFACT_TTL_SECONDS:
                    try:
                        os.unlink(entry.path)
                        reaped += 1
                    except OSError:
                        pass
                    continue
                entries.append((st.st_mtime, st.st_size, entry.path))
    except FileNotFoundError:
        return reaped

    total = sum(sz for _, sz, _ in entries)
    if total > ARTIFACT_QUOTA_BYTES:
        for _mtime, sz, path in sorted(entries):
            if total <= ARTIFACT_QUOTA_BYTES:
                break
            try:
                os.unlink(path)
                total -= sz
                reaped += 1
            except OSError:
                pass
    return reaped
