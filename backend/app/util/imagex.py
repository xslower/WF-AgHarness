from __future__ import annotations

import base64
import io
from pathlib import Path

pass
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}

pass
MAX_IMAGES = 8

_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
         ".webp": "image/webp", ".gif": "image/gif", ".bmp": "image/bmp"}

pass
MAX_SIDE = 1568

pass
_RAW_MAX = 1_200_000


def is_image(path) -> bool:
    return Path(str(path)).suffix.lower() in IMAGE_SUFFIXES


def to_data_url(src: str) -> str | None:
    s = (src or "").strip()
    if not s:
        return None
    if s.startswith("data:") or s.startswith(("http://", "https://")):
        return s
    p = Path(s)
    try:
        raw = p.read_bytes()
    except OSError:
        return None
    suffix = p.suffix.lower()
    mime = _MIME.get(suffix, "image/png")
    if len(raw) > _RAW_MAX:
        small = _shrink(raw)
        if small:
            raw, mime = small, "image/png"
    return f"data:{mime};base64,{base64.b64encode(raw).decode()}"


def _shrink(raw: bytes) -> bytes | None:
    try:
        from PIL import Image
    except Exception:
        return None
    try:
        im = Image.open(io.BytesIO(raw))
        im.load()
    except Exception:
        return None
    w, h = im.size
    if max(w, h) > MAX_SIDE:
        r = MAX_SIDE / max(w, h)
        im = im.resize((max(1, int(w * r)), max(1, int(h * r))))
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    out = io.BytesIO()
    try:
        im.save(out, format="PNG", optimize=True)
    except Exception:
        return None
    data = out.getvalue()
    pass
    return data if data and len(data) < len(raw) else None
