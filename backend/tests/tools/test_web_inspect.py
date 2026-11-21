from __future__ import annotations

import asyncio
import json

import pytest

from app.tools.builtin import build_tools as build_registry
from app.tools.builtin.web.inspect import (
    Recorder, _clip, _clip_json, _parse_at, _parse_viewport,
)
from app.tools.builtin.web.open import open_page
from app.tools import ToolContext


class _FakeCtx:
    def __init__(self, cwd):
        self.cwd = str(cwd)
        self.report_file = None


def _debug_run(tmp_path, page_uri, debug):
    pytest.importorskip("playwright.async_api")
    ctx = _FakeCtx(tmp_path)
    try:
        out = asyncio.run(open_page(page_uri, ctx, debug=debug))
    except Exception as e:
        pytest.skip(f"playwright 浏览器不可用: {e}")
    if out.startswith('{"error"') and ("浏览器" in out and "失败" in out):
        pytest.skip(f"playwright 浏览器不可用: {out}")
    return json.loads(out)


pass
def test_schema_exposes_debug_instead_of_inspect_action():
    reg = build_registry()
    props = next(s["function"]["parameters"] for s in reg.schemas
                 if s["function"]["name"] == "web")["properties"]
    assert "debug" in props and "steps" in props
    assert "action" not in props and "screenshot" not in props
    assert "inspect" not in next(s["function"]["description"] for s in reg.schemas
                                 if s["function"]["name"] == "web")


def test_open_page_requires_url_and_valid_scheme(tmp_path):
    ctx = _FakeCtx(tmp_path)
    assert "http(s)" in asyncio.run(open_page("example.com", ctx))
    out = asyncio.run(build_registry().tools["web"](
        ToolContext(str(tmp_path)), query=""))
    assert "query 必填" in out


pass
def test_clip_viewport_and_at():
    assert _clip("a\nb" * 200).endswith("…")
    assert _parse_viewport("") is None
    assert _parse_viewport("1920x1080") == {"width": 1920, "height": 1080}
    assert _parse_viewport("garbage") is None
    assert _parse_viewport("10x10") == {"width": 320, "height": 240}
    assert _parse_at("10,20,100,50") == {"x": 10.0, "y": 20.0,
                                        "width": 100.0, "height": 50.0}
    assert _parse_at("1,2") is None and _parse_at("1,2,0,5") is None


def test_recorder_filters_noise_by_default():
    rec = Recorder()
    rec._log("log", "普通日志")
    rec._log("error", "boom")
    rec._log("warning", "deprecated")
    rec._on_request(_Req("GET", "https://x/a.js", "script"))
    rec._problem({"method": "GET", "url": "https://x/miss", "status": 404})
    out = rec.result(all_requests=False)
    assert out["console"]["total"] == 3 and out["console"]["errors"] == 2
    assert [m["text"] for m in out["console"]["messages"]] == ["boom", "deprecated"]
    assert out["network"]["total"] == 1 and out["network"]["failed"] == 1
    assert out["network"]["requests"][0]["status"] == 404
    assert len(rec.result(all_requests=True)["network"]["requests"]) == 1


class _Req:
    def __init__(self, method, url, resource_type="document"):
        self.method = method
        self.url = url
        self.resource_type = resource_type
        self.failure = ""


def test_clip_json_keeps_screens():
    big = {"screens": [{"path": "runs/w/screen_01.png"}],
           "network": {"requests": [{"url": "u" * 290} for _ in range(300)]}}
    out = json.loads(_clip_json(big))
    assert out["screens"][0]["path"] == "runs/w/screen_01.png"
    assert len(out["network"]["requests"]) <= 10
    assert out["network"].get("truncated") is True


pass
def test_debug_captures_console_and_network(tmp_path):
    page = tmp_path / "debug.html"
    page.write_text(
        "<html><head><title>调试页</title></head><body><h1>hello</h1>"
        "<script>console.log('正常'); console.error('前端报错 boom');"
        "fetch('https://127.0.0.1:1/nope').catch(()=>{})</script>"
        "</body></html>", encoding="utf-8")
    data = _debug_run(tmp_path, page.as_uri(), {"wait_ms": 200})
    assert data["title"] == "调试页"
    assert data["console"]["total"] >= 2
    assert data["console"]["errors"] >= 1
    assert any("boom" in m["text"] for m in data["console"]["messages"])
    assert len(data["screens"]) >= 1
    assert data["shot_dir"].startswith("runs/web_interact_")
    shot = tmp_path / data["screens"][0]["path"]
    assert shot.is_file() and shot.stat().st_size > 0
    assert data["network"]["total"] >= 1 or data["network"]["failed"] >= 1
    assert data.get("content")


def test_lightweight_open_returns_markdown_only(tmp_path):
    pytest.importorskip("playwright.async_api")
    page = tmp_path / "plain.html"
    page.write_text(
        "<html><title>x</title><body>这是一段足够长的正文，用于确认轻量路径"
        "只返回可读文本而不带任何调试字段。</body></html>", encoding="utf-8")
    ctx = _FakeCtx(tmp_path)
    try:
        out = asyncio.run(open_page(page.as_uri(), ctx))
    except Exception as e:
        pytest.skip(f"playwright 浏览器不可用: {e}")
    if out.startswith('{"error"') and "浏览器" in out:
        pytest.skip(f"playwright 浏览器不可用: {out}")
    assert not out.startswith("{")
    for key in ("console", "network", "screens", "shot_dir"):
        assert key not in out
    assert "足够长的正文" in out


def test_long_page_sliced_into_screens_and_located_shots(tmp_path):
    from PIL import Image
    page = tmp_path / "tall.html"
    rows = "".join(
        f'<div id="r{i}" style="height:200px">ROW {i}</div>' for i in range(8))
    page.write_text(
        '<html><body style="margin:0">'
        '<div class="box" style="position:absolute;top:900px;left:50px;'
        'width:120px;height:80px;background:red">TARGET</div>'
        + rows + "</body></html>", encoding="utf-8")
    data = _debug_run(tmp_path, page.as_uri(), {
        "wait_ms": 100, "viewport": "400x300",
        "shots": [{"at": "40,890,160,100"}, {"selector": ".box"}]})
    assert data["page_size"][0] == 400
    assert data["page_size"][1] > 900
    assert len(data["screens"]) >= 3
    assert data["screens"][0]["page_y"] == [0, 300]
    for s in data["screens"]:
        with Image.open(tmp_path / s["path"]) as im:
            assert im.width == 400 and im.height <= 300
    shots = data["shots"]
    assert len(shots) == 2 and all(s["ok"] for s in shots)
    assert shots[0]["bbox"]["y"] == 890.0
    assert shots[1]["bbox"]["y"] == 900.0
    with Image.open(tmp_path / shots[0]["path"]) as im:
        assert im.size == (160, 100)
    with Image.open(tmp_path / shots[1]["path"]) as im:
        assert im.size == (120, 80)


def test_viewport_screen_and_bad_locator(tmp_path):
    page = tmp_path / "x.html"
    page.write_text("<html><body>ok</body></html>", encoding="utf-8")
    data = _debug_run(tmp_path, page.as_uri(), {
        "screen": "viewport",
        "shots": [{"at": "bad"}, {"selector": "#none"}]})
    assert len(data["screens"]) == 1 and data["screens"][0]["mode"] == "viewport"
    assert (tmp_path / data["screens"][0]["path"]).is_file()
    assert len(data["shots"]) == 2
    assert not data["shots"][0]["ok"] and data["shots"][0]["path"] is None
    assert not data["shots"][1]["ok"]
