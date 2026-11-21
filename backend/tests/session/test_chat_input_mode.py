from __future__ import annotations

import asyncio

import pytest

from app.api.routers.chat_input import MAX_ATTACHMENTS, normalize_input, resume_message
from app.api.routers.chat_mode import resolve_cwd, resolve_plan_mode


pass

class _FakeAsr:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def transcribe_audio(self, raw, spec=""):
        self.calls.append({"raw": raw, "spec": spec})
        return self.result


class _FakeRegistry:
    def __init__(self, asr_entry, images_entry=None, vision_model=None):
        self._entry = asr_entry
        self._images = images_entry
        self._vision = vision_model

    def first_of_kind(self, kind, **kw):
        return self._entry if kind == "asr" else None

    def first_with_images(self, **kw):
        return self._images

    def model_of(self, spec):
        return self._vision


class _Entry:
    def __init__(self, spec):
        self.spec = spec


class _FakeModel:
    def __init__(self, supports_images: bool):
        self.supportsImages = supports_images


class _FakeGateway:
    def __init__(self, asr=None, asr_entry=None, images_entry=None,
                 vision_model=None, described="一张登录表单"):
        self.registry = _FakeRegistry(asr_entry, images_entry, vision_model)
        self._described = described
        self.image_calls = []
        if asr is not None:
            self.transcribe_audio = asr

    async def describe_image(self, src, prompt="", spec=""):
        self.image_calls.append({"src": src, "prompt": prompt, "spec": spec})
        if self._described is None:
            return {"ok": False, "error": "模型挂了"}
        return {"ok": True, "text": self._described, "model": spec}


def _run(coro):
    return asyncio.run(coro)


def test_plain_text_passes_through():
    out = _run(normalize_input({"content": "你好"}, gateway=_FakeGateway(),
                               history=[]))
    assert out.model_content is not None
    assert "你好" in str(out.model_content)
    assert out.raw_text == "你好"


def test_attachments_are_appended_with_name():
    gw = _FakeGateway()
    out = _run(normalize_input(
        {"content": "看下", "attachments": [{"name": "a.md", "text": "正文"}]},
        gateway=gw, history=[]))
    body = str(out.model_content)
    assert "[附件 a.md]" in body and "正文" in body
    assert "看下" in body


def test_attachments_are_capped():
    gw = _FakeGateway()
    many = [{"name": f"f{i}.md", "text": "x"} for i in range(MAX_ATTACHMENTS + 5)]
    out = _run(normalize_input({"content": "c", "attachments": many},
                               gateway=gw, history=[]))
    assert str(out.model_content).count("[附件") == MAX_ATTACHMENTS


def test_non_dict_attachment_is_skipped():
    gw = _FakeGateway()
    out = _run(normalize_input(
        {"content": "c", "attachments": [None, "x", {"name": "ok.md", "text": "t"}]},
        gateway=gw, history=[]))
    assert str(out.model_content).count("[附件") == 1


def test_audio_transcribed_via_dict_contract():
    gw = _FakeGateway(asr=_FakeAsr({"ok": True, "text": "转写", "model": "p/asr"}),
                      asr_entry=_Entry("p/asr"))
    out = _run(normalize_input({"content": "听", "audio": "data:audio/webm;base64,YWJj"},
                               gateway=gw, history=[]))
    assert "转写" in str(out.model_content)


def test_audio_without_asr_model_says_so():
    gw = _FakeGateway(asr_entry=None)
    out = _run(normalize_input({"content": "", "audio": "data:audio/webm;base64,YWJj"},
                               gateway=gw, history=[]))
    assert "未配置 kind=asr" in str(out.model_content)


def test_audio_failure_is_reported_not_raised():
    class _Boom:
        async def transcribe_audio(self, raw, spec=""):
            raise RuntimeError("接口 500")

    gw = _FakeGateway(asr=_Boom(), asr_entry=_Entry("p/asr"))
    out = _run(normalize_input({"content": "x", "audio": "data:audio/webm;base64,YWJj"},
                               gateway=gw, history=[]))
    assert "语音转写失败" in str(out.model_content)


def test_non_data_url_audio_is_ignored():
    gw = _FakeGateway(asr_entry=_Entry("p/asr"))
    out = _run(normalize_input({"content": "x", "audio": "http://cdn/a.webm"},
                               gateway=gw, history=[]))
    assert "语音" not in str(out.model_content)


def _vision_gw(*, current_can_see: bool, fallback=None, described="一张登录表单"):
    return _FakeGateway(images_entry=fallback,
                        vision_model=_FakeModel(current_can_see),
                        described=described)


def test_images_become_multimodal_list():
    gw = _vision_gw(current_can_see=True)
    out = _run(normalize_input({"content": "看图", "images": ["http://i/1.png"]},
                               gateway=gw, history=[], spec="p/vision"))
    assert isinstance(out.model_content, list)
    assert out.model_content[0]["type"] == "text"
    assert out.model_content[1]["image_url"]["url"] == "http://i/1.png"
    assert gw.image_calls == []


def test_images_described_when_model_cannot_see():
    gw = _vision_gw(current_can_see=False, fallback=_Entry("p/vision"))
    out = _run(normalize_input({"content": "看图", "images": ["http://i/1.png"]},
                               gateway=gw, history=[], spec="p/noimg"))
    body = str(out.model_content)
    assert "image_url" not in body
    assert "一张登录表单" in body
    assert "看图" in body
    assert gw.image_calls[0]["spec"] == "p/vision"


def test_images_refused_when_no_vision_model():
    gw = _vision_gw(current_can_see=False, fallback=None)
    out = _run(normalize_input({"content": "看图", "images": ["http://i/1.png"]},
                               gateway=gw, history=[], spec="p/noimg"))
    body = str(out.model_content)
    assert "image_url" not in body
    assert "支持图像输入" in body


def test_resume_message_default_text():
    assert "请按上面的计划开始执行" in resume_message()["content"]
    assert resume_message("自定义")["content"] == "自定义"


pass

class _Sess:
    def __init__(self, prefs=None):
        self.prefs = prefs or {}

    def get(self, k, d=None):
        return getattr(self, k, d)


def test_resume_message_role_is_user():
    assert resume_message()["role"] == "user"


def test_resume_message_is_marked_system():
    assert resume_message()["_sys"] == "resume"
    assert resume_message("自定义")["_sys"] == "resume"



class _PC:
    def __init__(self, state=None, write_allowed=False):
        self.state = state
        self.is_write_allowed = write_allowed
        self.reset_called = False
        self.enter_called = False

    def reset(self):
        self.reset_called = True
        self.state = None
        self.is_write_allowed = False

    def enter_planning(self, sid):
        self.enter_called = True


class _FakeC:
    def __init__(self, pc=None, plan_mode_default=True, workspace="", project=None):
        self._pc = pc or _PC()
        self.store = type("S", (), {"config": type("C", (), {
            "settings": type("S2", (), {
                "planMode": plan_mode_default,
                "workspaceRoot": workspace,
            })()})()})()
        self.runner = type("R", (), {"plan_for": lambda _self, sid: self._pc})()

    def plan_of(self, sid):
        return self.runner.plan_for(sid)


    def sessions_factory(self):
        return None


def test_plan_mode_from_queue_keeps_executing():
    pc = _PC(write_allowed=True)
    c = _FakeC(pc)
    mode = resolve_plan_mode(sess={}, sid="s", c=c, req={"plan": False},
                             from_queue=True, resume=False)
    assert mode == "executing"


def test_plan_mode_from_queue_ignores_request_plan_flag():
    from app.agent.plan import PlanState
    pc = _PC(state=PlanState.awaiting_approval)
    c = _FakeC(pc)
    mode = resolve_plan_mode(sess={}, sid="s", c=c, req={"plan": False},
                             from_queue=True, resume=False)
    assert mode == "on"


def test_plan_mode_resume_uses_write_allowed():
    pc = _PC(write_allowed=False)
    c = _FakeC(pc)
    assert resolve_plan_mode(sess={}, sid="s", c=c, req={},
                             from_queue=False, resume=True) == "on"


def test_plan_mode_defaults_off_when_not_passed():
    c = _FakeC(plan_mode_default=True)
    assert resolve_plan_mode(sess={}, sid="s", c=c, req={},
                             from_queue=False, resume=False) == "off"
    c2 = _FakeC(plan_mode_default=False)
    assert resolve_plan_mode(sess={}, sid="s", c=c2, req={},
                             from_queue=False, resume=False) == "off"


def test_plan_mode_explicit_flag_wins():
    c = _FakeC(plan_mode_default=True)
    assert resolve_plan_mode(sess={}, sid="s", c=c, req={"plan": False},
                             from_queue=False, resume=False) == "off"


def test_plan_mode_off_resets_controller():
    pc = _PC()
    c = _FakeC(pc)
    resolve_plan_mode(sess={}, sid="s", c=c, req={"plan": False},
                      from_queue=False, resume=False)
    assert pc.reset_called



pass
def test_yolo_mode_disables_plan_mode():
    c = _FakeC(plan_mode_default=True, workspace="/ws")
    c.store.config.settings.policyExtraSafePaths = []
    from app.security import project_mode as pp
    from app.api.routers.chat_mode import resolve_plan_mode
    old = pp.get_mode
    try:
        pp.get_mode = lambda p: "yolo"
        mode = resolve_plan_mode(sess={}, sid="s", c=c, req={},
                                 from_queue=False, resume=False)
        assert mode == "off"
    finally:
        pp.get_mode = old


def test_yolo_does_not_override_explicit_plan_flag():
    c = _FakeC(plan_mode_default=False, workspace="/ws")
    from app.security import project_mode as pp
    from app.api.routers.chat_mode import resolve_plan_mode
    old = pp.get_mode
    try:
        pp.get_mode = lambda p: "yolo"
        mode = resolve_plan_mode(sess={}, sid="s", c=c, req={"plan": True},
                                 from_queue=False, resume=False)
        assert mode == "on"
    finally:
        pp.get_mode = old


def test_workspace_mode_keeps_plan_mode_default():
    c = _FakeC(plan_mode_default=True, workspace="/ws")
    from app.security import project_mode as pp
    from app.api.routers.chat_mode import resolve_plan_mode
    old = pp.get_mode
    try:
        pp.get_mode = lambda p: "workspace"
        mode = resolve_plan_mode(sess={}, sid="s", c=c, req={},
                                 from_queue=False, resume=False)
        assert mode == "off"
    finally:
        pp.get_mode = old

def test_cwd_priority():
    c = _FakeC(workspace="/ws")
    assert resolve_cwd({"cwd": "/req"}, {"project": "/proj"}, c) == "/req"
    assert resolve_cwd({}, {"project": "/proj"}, c) == "/proj"
    assert resolve_cwd({}, {}, c) == "/ws"
