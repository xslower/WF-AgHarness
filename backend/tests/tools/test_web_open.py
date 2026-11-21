from __future__ import annotations

import asyncio
import json

import pytest

import app.tools.builtin.web.open as O
from app.tools import ToolContext


class _Ctx:
    def __init__(self):
        self.cwd = "."
        self.report_file = None


def _run(coro):
    return asyncio.run(coro)


pass
def test_is_url_only_accepts_three_schemes():
    assert O.is_url("https://x.com") and O.is_url("http://x") and O.is_url("FILE:///a")
    for s in ("", "python 教程", "x.com/a", "ftp://x/y", "//x.com"):
        assert not O.is_url(s)


def test_looks_broken_triggers_browser_upgrade():
    assert O._looks_broken(404, "text/html", "anything")
    assert O._looks_broken(200, "text/html", "<html>x</html>")
    assert not O._looks_broken(200, "text/html", "正文" * 200)
    assert not O._looks_broken(200, "application/json", "{}")


pass
@pytest.mark.parametrize("v", [True, 1, "true", "debug", "{}", {"screen": "page"},
                              [{"selector": "#id"}], "10,20,100,50"])
def test_debug_various_forms_all_enable_capture(v):
    o = O._debug_opts(v)
    assert o is not None and o["screen"] in ("page", "viewport")
    assert isinstance(o["shots"], list)


@pytest.mark.parametrize("v", [None, False, 0, "", "false", "off", "none", "normal"])
def test_debug_falsy_forms_disable_capture(v):
    assert O._debug_opts(v) is None


def test_debug_aliases_and_units_and_shots_shapes():
    o = O._debug_opts({"mode": "viewport", "size": [800, 600],
                       "wait": "0.5s", "all": "yes",
                       "regions": ["10,20,30,40", {"selector": "#card"},
                                   {"x": 1, "y": 2, "width": 3, "height": 4}]})
    assert o["screen"] == "viewport"
    assert o["viewport"] == "800x600"
    assert o["wait_ms"] == 500
    assert o["all_requests"] is True
    assert o["shots"] == [{"at": "10,20,30,40"}, {"selector": "#card"},
                          {"at": "1,2,3,4"}]


def test_debug_unknown_fields_never_raise():
    o = O._debug_opts({"nonsense": object(), "screen": 123, "wait_ms": "bad"})
    assert o["screen"] == "page" and o["wait_ms"] == 0


def test_steps_tolerant_to_string_and_single_object():
    assert O._as_steps('[{"act":"click","selector":"#a"}]')[0]["act"] == "click"
    assert O._as_steps({"act": "wait"}) == [{"act": "wait"}]
    assert O._as_steps(42) == []


pass
def test_fast_path_returns_markdown_without_debug_fields(monkeypatch):
    async def fake_doc(url, timeout=20.0):
        return {"status": 200, "content_type": "text/html; charset=utf-8",
                "text": "<html><body><p>" + "正文内容" * 100 + "</p></body></html>",
                "final_url": url}
    monkeypatch.setattr(O, "fetch_doc", fake_doc)
    out = _run(O.open_page("https://x.com/a", _Ctx()))
    assert "正文内容" in out and "[200" in out
    for key in ("console", "network", "screens", "shot_dir"):
        assert key not in out


def test_final_url_only_when_redirected(monkeypatch):
    async def fake_doc(url, timeout=20.0):
        return {"status": 200, "content_type": "text/html",
                "text": "<p>" + "内容" * 200 + "</p>",
                "final_url": "https://real.com/page"}
    monkeypatch.setattr(O, "fetch_doc", fake_doc)
    assert "最终地址: https://real.com/page" in _run(
        O.open_page("https://x.com/go", _Ctx()))


def test_fast_failure_upgrades_to_browser_and_returns_content_only(monkeypatch):
    async def boom(url, timeout=20.0):
        raise RuntimeError("连不上")

    async def fake_interact(target, ctx, **kw):
        assert kw["steps"] == [] and kw["opts"]["want_content"] is True
        assert kw["opts"]["with_logs"] is False
        return json.dumps({"url": target, "final_url": target,
                           "content": "# 渲染后正文", "content_len": 6})
    monkeypatch.setattr(O, "fetch_doc", boom)
    monkeypatch.setattr(O, "interact_page", fake_interact)
    out = _run(O.open_page("https://x.com/a", _Ctx()))
    assert out == "# 渲染后正文"
    assert not out.startswith("{")


def test_debug_always_uses_browser_with_logs(monkeypatch):
    called = []

    async def fake_interact(target, ctx, **kw):
        called.append(kw)
        return json.dumps({"url": target, "content": "正文",
                           "screens": [{"path": "runs/w/screen_01.png"}],
                           "console": {"total": 0}, "network": {"total": 0}})
    monkeypatch.setattr(O, "interact_page", fake_interact)
    out = _run(O.open_page("https://x.com/a", _Ctx(), debug=True))
    assert json.loads(out)["screens"]
    assert called[0]["opts"]["with_logs"] is True
    assert called[0]["screenshot"] is True


def test_steps_uses_browser_and_keeps_full_json(monkeypatch):
    async def fake_interact(target, ctx, **kw):
        assert len(kw["steps"]) == 1
        return json.dumps({"url": target, "steps": [{"step": 1, "ok": True}]})
    monkeypatch.setattr(O, "interact_page", fake_interact)
    out = _run(O.open_page("https://x.com/a", _Ctx(),
                           steps=[{"act": "click", "selector": "#go"}]))
    assert json.loads(out)["steps"][0]["ok"] is True


def test_open_page_rejects_non_url_before_any_io():
    assert "http(s)" in _run(O.open_page("python 教程", _Ctx()))
