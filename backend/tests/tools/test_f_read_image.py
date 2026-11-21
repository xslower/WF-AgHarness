from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.agent.stream_tools import _image_message, execute_tools
from app.chat.media_msg import (ImageUnavailable, image_parts, supports_images,
                                vision_spec)
from app.tools import ToolContext
from app.tools.builtin.fs.read_file import _read_one
from app.util import imagex
from app.util.tokens import IMAGE_TOKENS, estimate_obj

pass
_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082")


def _run(coro):
    return asyncio.run(coro)


class _Model:
    def __init__(self, supports_images: bool):
        self.supportsImages = supports_images


class _Entry:
    def __init__(self, spec, supports_images=True):
        self.spec = spec
        self.model = _Model(supports_images)


class _Registry:
    def __init__(self, models=None, fallback=None):
        self._models = models or {}
        self._fallback = fallback

    def model_of(self, spec):
        return self._models.get(spec)

    def get(self, spec):
        m = self._models.get(spec)
        return _Entry(spec, m.supportsImages) if m else None

    def first_with_images(self, **kw):
        return self._fallback


class _Gateway:

    def __init__(self, models=None, fallback=None, described="一张登录表单"):
        self.registry = _Registry(models, fallback)
        self._described = described
        self.calls: list[dict] = []

    async def describe_image(self, src, prompt="", spec=""):
        self.calls.append({"src": src, "prompt": prompt, "spec": spec})
        if self._described is None:
            return {"ok": False, "error": "视觉模型挂了"}
        return {"ok": True, "text": self._described, "model": spec}


@pytest.fixture()

def png(tmp_path: Path) -> Path:
    p = tmp_path / "shot.png"
    p.write_bytes(_PNG)
    return p


pass


def test_supports_images_reads_config_only():
    gw = _Gateway({"p/see": _Model(True), "p/blind": _Model(False)})
    assert supports_images(gw, "p/see") is True
    assert supports_images(gw, "p/blind") is False
    assert supports_images(gw, "p/unknown") is False
    assert supports_images(gw, "") is False
    assert supports_images(None, "p/see") is False


def test_vision_spec_prefers_current_then_configured():
    gw = _Gateway({"p/see": _Model(True)}, fallback=_Entry("p/other"))
    assert vision_spec(gw, "p/see") == "p/see"
    assert vision_spec(gw, "p/blind") == "p/other"
    assert vision_spec(_Gateway({}), "") == ""


pass


def test_image_parts_sends_urls_when_visible(png: Path):
    gw = _Gateway({"p/see": _Model(True)})
    parts = _run(image_parts([str(png)], gateway=gw, spec="p/see"))
    assert len(parts) == 1
    assert parts[0]["type"] == "image_url"
    assert parts[0]["image_url"]["url"].startswith("data:image/png;base64,")
    assert gw.calls == []


def test_image_parts_describes_when_blind(png: Path):
    gw = _Gateway({"p/see": _Model(True), "p/blind": _Model(False)},
                  fallback=_Entry("p/see"))
    parts = _run(image_parts([str(png)], gateway=gw, spec="p/blind"))
    assert len(parts) == 1
    assert parts[0]["type"] == "text"
    assert "一张登录表单" in parts[0]["text"]
    assert gw.calls[0]["spec"] == "p/see"
    assert "看不见图" in gw.calls[0]["prompt"]


def test_image_parts_raises_without_any_vision_model(png: Path):
    gw = _Gateway({})
    with pytest.raises(ImageUnavailable):
        _run(image_parts([str(png)], gateway=gw, spec="p/blind"))


def test_image_parts_describe_failure_is_per_image(png: Path, tmp_path: Path):
    gw = _Gateway({}, fallback=_Entry("p/see"), described=None)
    parts = _run(image_parts([str(png)], gateway=gw, spec=""))
    assert parts[0]["type"] == "text"
    assert "转述失败" in parts[0]["text"] and "视觉模型挂了" in parts[0]["text"]


def test_image_parts_caps_at_max_images(png: Path):
    gw = _Gateway({"p/see": _Model(True)})
    parts = _run(image_parts([str(png)] * 20, gateway=gw, spec="p/see"))
    assert len(parts) == imagex.MAX_IMAGES


def test_image_parts_empty_is_noop():
    gw = _Gateway({"p/see": _Model(True)})
    assert _run(image_parts([], gateway=gw, spec="p/see")) == []


pass


def test_f_read_registers_image_instead_of_garbling(png: Path):
    ctx = ToolContext(str(png.parent))
    ctx.images_channel = True
    out = _read_one(str(png), ctx, None, False, False)
    assert "�" not in out
    assert "图片" in out and png.name in out
    assert len(ctx.pending_images) == 1
    assert ctx.pending_images[0].startswith("data:image/png;base64,")


def test_f_read_image_without_channel_reports_error(png: Path):
    ctx = ToolContext(str(png.parent))
    out = _read_one(str(png), ctx, None, False, False)
    assert "不支持读图" in out and "ocr" in out
    assert ctx.pending_images == []


def test_f_read_text_file_untouched(tmp_path: Path):
    p = tmp_path / "a.py"
    p.write_text("x = 1\n", encoding="utf-8")
    ctx = ToolContext(str(tmp_path))
    out = _read_one(str(p), ctx, None, False, False)
    assert out.strip() == "x = 1"
    assert ctx.pending_images == []


def test_f_read_refuses_beyond_image_cap(tmp_path: Path):
    ctx = ToolContext(str(tmp_path))
    ctx.images_channel = True
    ctx.pending_images = ["data:image/png;base64,AA"] * imagex.MAX_IMAGES
    p = tmp_path / "x.png"
    p.write_bytes(_PNG)
    out = _read_one(str(p), ctx, None, False, False)
    assert "最多" in out
    assert len(ctx.pending_images) == imagex.MAX_IMAGES


pass


def test_image_message_is_user_multimodal_after_tools(png: Path):
    ctx = ToolContext(str(png.parent))
    ctx.images_channel = True
    _read_one(str(png), ctx, None, False, False)
    gw = _Gateway({"p/see": _Model(True)})
    msgs = _run(_image_message(ctx, gw, "p/see"))
    assert len(msgs) == 1
    m = msgs[0]
    assert m["role"] == "user"
    assert m["_sys"] == "image"
    assert isinstance(m["content"], list)
    assert m["content"][1]["type"] == "image_url"
    assert ctx.pending_images == []


def test_image_message_empty_when_nothing_read():
    ctx = ToolContext("/tmp")
    assert _run(_image_message(ctx, _Gateway({}), "p/x")) == []


def test_image_message_reports_when_no_vision_model(png: Path):
    ctx = ToolContext(str(png.parent))
    ctx.images_channel = True
    _read_one(str(png), ctx, None, False, False)
    msgs = _run(_image_message(ctx, _Gateway({}), "p/blind"))
    assert "发图失败" in str(msgs[0]["content"])
    assert ctx.pending_images == []


class _FakeRunner:

    mcp = None

    def __init__(self, gateway, image_source: str):
        self.gateway = gateway
        self._image_source = image_source

    def _budget_note(self, depth, left, total):
        return ""

    def _parse_args(self, tc):
        return {}, "", ""

    def _last_model_spec(self):
        return "p/see"

    async def _execute_one(self, tc, args, arg_err, ctx, messages, depth, emit,
                           fix_note=""):
        ctx.pending_images.append(self._image_source)
        return "[图片已读取]"


def test_execute_tools_appends_image_after_all_tool_msgs(png: Path):
    ctx = ToolContext(str(png.parent))
    ctx.pending_images = [imagex.to_data_url(str(png))]
    runner = _FakeRunner(_Gateway({"p/see": _Model(True)}), ctx.pending_images[0])
    ctx.pending_images = []
    calls = [{"id": "c1", "function": {"name": "f_read"}},
             {"id": "c2", "function": {"name": "f_read"}}]
    messages: list[dict] = []
    events: list[dict] = []

    async def emit(ev):
        events.append(ev)

    out = _run(_collect(execute_tools(runner, calls, ctx, messages, 0, emit)))
    roles = [m["role"] for m in out]
    assert roles == ["tool", "tool", "user"], roles
    assert out[-1]["_sys"] == "image"
    assert out[-1]["content"][1]["type"] == "image_url"
    pass
    assert [m["role"] for m in messages] == roles


def test_execute_tools_no_image_no_extra_msg(png: Path):
    ctx = ToolContext(str(png.parent))
    runner = _FakeRunner(_Gateway({"p/see": _Model(True)}), "")
    calls = [{"id": "c1", "function": {"name": "f_read"}}]
    messages: list[dict] = []

    async def emit(ev):
        return None

    out = _run(_collect(execute_tools(runner, calls, ctx, messages, 0, emit)))
    assert [m["role"] for m in out] == ["tool"]


async def _collect(agen):
    return [m async for m in agen]


pass


def test_image_data_url_counts_fixed_tokens():
    big = "data:image/png;base64," + "A" * 400_000
    pass
    assert estimate_obj([{"type": "image_url", "image_url": {"url": big}}]) \
        == IMAGE_TOKENS + estimate_obj("image_url")


def test_plain_long_text_still_counted():
    assert estimate_obj("a" * 300) == 100
