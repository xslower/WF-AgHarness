from __future__ import annotations

import asyncio
import json

import pytest

from app.tools.builtin import build_tools as build_registry
from app.tools.builtin.web.interact import _compile_steps, interact_page
from app.tools import ToolContext


class _FakeCtx:
    def __init__(self, cwd):
        self.cwd = str(cwd)
        self.report_file = None


_FORM_HTML = """<!doctype html><html><head><meta charset="utf-8">
<title>交互测试</title></head><body>
<h1 id="h">表单页</h1>
<input id="user" placeholder="用户名">
<input id="pass" type="password">
<select id="city"><option value="">选择</option>
<option value="bj">北京</option><option value="sh">上海</option></select>
<input id="agree" type="checkbox">
<button id="go" type="button">提交</button>
<div id="out"></div>
<script>
document.getElementById('go').addEventListener('click', function () {
  var u = document.getElementById('user').value;
  var p = document.getElementById('pass').value;
  var c = document.getElementById('city').value;
  var a = document.getElementById('agree').checked;
  var m = [];
  if (!u) m.push('用户名必填');
  if (!p) m.push('密码必填');
  if (!c) m.push('城市必选');
  if (!a) m.push('需同意');
  document.getElementById('out').textContent =
    m.length ? ('错误:' + m.join(',')) : ('OK ' + u + '/' + c + '/已同意');
});
</script></body></html>"""

_ENTER_HTML = """<!doctype html><html><head><meta charset="utf-8">
<title>回车提交</title></head><body>
<form id="f"><input id="q"></form>
<div id="out"></div>
<script>
document.getElementById('f').addEventListener('submit', function (e) {
  e.preventDefault();
  document.getElementById('out').textContent =
    'searched:' + document.getElementById('q').value;
});
</script></body></html>"""


def _run(tmp_path, uri, steps, **kw):
    pytest.importorskip("playwright.async_api")
    ctx = _FakeCtx(tmp_path)
    try:
        out = asyncio.run(interact_page(uri, ctx, steps=steps, **kw))
    except Exception as e:
        pytest.skip(f"playwright 浏览器不可用: {e}")
    if out.startswith('{"error"') and "浏览器" in out and "失败" in out:
        pytest.skip(f"playwright 浏览器不可用: {out}")
    return json.loads(out)


pass
def test_schema_exposes_steps_and_no_action():
    reg = build_registry()
    props = next(s["function"]["parameters"] for s in reg.schemas
                 if s["function"]["name"] == "web")["properties"]
    assert "steps" in props and "debug" in props
    assert "action" not in props and "respect_robots" not in props
    assert "steps" in next(s["function"]["description"] for s in reg.schemas
                           if s["function"]["name"] == "web")


def test_interact_requires_url_valid_scheme_and_steps(tmp_path):
    ctx = _FakeCtx(tmp_path)
    assert "需要 url" in asyncio.run(interact_page("", ctx, steps=[]))
    assert "http(s)" in asyncio.run(interact_page("example.com", ctx, steps=[]))
    uri = (tmp_path / "x.html").as_uri()
    pass
    assert _compile_steps([]) == []
    assert "steps 无效" in asyncio.run(
        interact_page(uri, ctx, steps=[{"act": "bogus"}]))
    assert "需要 selector" in asyncio.run(
        interact_page(uri, ctx, steps=[{"act": "click"}]))
    assert "goto 需要 url" in asyncio.run(
        interact_page(uri, ctx, steps=[{"act": "goto"}]))
    assert "press 需要 key" in asyncio.run(
        interact_page(uri, ctx, steps=[{"act": "press"}]))
    assert "attr 需要 name" in asyncio.run(
        interact_page(uri, ctx, steps=[{"act": "attr", "selector": "#a"}]))
    assert "最多 40 步" in asyncio.run(
        interact_page(uri, ctx, steps=[{"act": "wait", "value": 1}] * 41))


def test_compile_steps_normalizes_and_keeps_optional():
    plan = _compile_steps([{"action": "CLICK", "selector": " #a "},
                           {"act": "press", "key": "Enter", "optional": True}])
    assert plan[0]["act"] == "click" and plan[0]["selector"] == "#a"
    assert plan[0]["_no"] == 1 and plan[1]["optional"] is True


def test_query_empty_is_rejected_before_any_network(tmp_path):
    reg = build_registry()
    out = asyncio.run(reg.execute("web", {}, ToolContext(str(tmp_path))))
    assert "query 必填" in out


def test_dispatch_passes_steps_to_interact(tmp_path):
    reg = build_registry()
    out = asyncio.run(reg.execute(
        "web", {"query": "file:///x.html",
                "steps": [{"act": "bogus"}]}, ToolContext(str(tmp_path))))
    assert "steps 无效" in out


pass
def test_form_fill_select_check_click_and_read(tmp_path):
    page = tmp_path / "form.html"
    page.write_text(_FORM_HTML, encoding="utf-8")
    data = _run(tmp_path, page.as_uri(), [
        {"act": "fill", "selector": "#user", "value": "alice"},
        {"act": "fill", "selector": "#pass", "value": "secret"},
        {"act": "select", "selector": "#city", "value": "bj"},
        {"act": "check", "selector": "#agree"},
        {"act": "click", "selector": "#go"},
        {"act": "text", "selector": "#out"},
    ], screenshot=False)
    assert data.get("error") is None, data
    assert [s["ok"] for s in data["steps"]] == [True] * 6
    assert data["steps"][-1]["text"] == "OK alice/bj/已同意"
    assert data["title"] == "交互测试"
    assert data["final_url"].startswith("file://")


def test_failed_step_stops_and_marks_rest_skipped(tmp_path):
    page = tmp_path / "form2.html"
    page.write_text(_FORM_HTML, encoding="utf-8")
    data = _run(tmp_path, page.as_uri(), [
        {"act": "click", "selector": "#go"},
        {"act": "text", "selector": "#out"},
        {"act": "click", "selector": "#nonexistent"},
        {"act": "text", "selector": "#out"},
    ], screenshot=False)
    assert "失败" in data.get("error", "")
    steps = data["steps"]
    assert steps[0]["ok"] and "错误:" in steps[1]["text"]
    assert not steps[2]["ok"] and steps[2]["step"] == 3
    assert steps[3].get("skipped") is True


def test_optional_step_failure_does_not_stop_flow(tmp_path):
    page = tmp_path / "form3.html"
    page.write_text(_FORM_HTML, encoding="utf-8")
    data = _run(tmp_path, page.as_uri(), [
        {"act": "click", "selector": "#nonexistent", "optional": True},
        {"act": "fill", "selector": "#user", "value": "bob"},
        {"act": "fill", "selector": "#pass", "value": "pw"},
        {"act": "select", "selector": "#city", "value": "sh"},
        {"act": "check", "selector": "#agree"},
        {"act": "click", "selector": "#go"},
        {"act": "text", "selector": "#out"},
    ], screenshot=False)
    assert data.get("error") is None, data
    assert "warning" in data["steps"][0] and not data["steps"][0]["ok"]
    assert data["steps"][-1]["text"] == "OK bob/sh/已同意"


def test_press_enter_submits_form_via_trusted_event(tmp_path):
    page = tmp_path / "enter.html"
    page.write_text(_ENTER_HTML, encoding="utf-8")
    data = _run(tmp_path, page.as_uri(), [
        {"act": "type", "selector": "#q", "value": "hello", "delay": 5},
        {"act": "press", "selector": "#q", "key": "Enter"},
        {"act": "text", "selector": "#out"},
    ], screenshot=False)
    assert data.get("error") is None, data
    assert data["steps"][-1]["text"] == "searched:hello"


def test_value_scroll_wait_and_screenshot_step(tmp_path):
    page = tmp_path / "form4.html"
    page.write_text(_FORM_HTML, encoding="utf-8")
    data = _run(tmp_path, page.as_uri(), [
        {"act": "fill", "selector": "#user", "value": "carol"},
        {"act": "value", "selector": "#user"},
        {"act": "scroll", "value": "bottom"},
        {"act": "wait", "selector": "#go"},
        {"act": "screenshot", "selector": "#h"},
    ], screenshot=True, wait_ms=100)
    assert data.get("error") is None, data
    assert data["steps"][1]["value"] == "carol"
    shot = tmp_path / data["steps"][4]["screenshot"]
    assert shot.is_file() and shot.stat().st_size > 0
    assert data["shot_dir"].startswith("runs/web_interact_")
    assert len(data["screens"]) >= 1
    assert (tmp_path / data["screens"][0]["path"]).is_file()


def test_scroll_rejects_bad_value_without_browser(tmp_path):
    page = tmp_path / "form5.html"
    page.write_text(_FORM_HTML, encoding="utf-8")
    data = _run(tmp_path, page.as_uri(), [
        {"act": "scroll", "value": "sideways"},
    ], screenshot=False)
    assert "scroll 的 value" in data.get("error", "")
