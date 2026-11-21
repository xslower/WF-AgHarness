from __future__ import annotations

from types import SimpleNamespace

from app.agent.profile import SystemOverride
from app.api.routers.chat_session import SessionTurn


class _Installs:

    def __init__(self, table: dict) -> None:
        self.table = table


def _turn(sess: dict, installs=None) -> SessionTurn:
    c = SimpleNamespace(installs=installs)
    return SessionTurn(c=c, s=sess, sid="1", rt=None, emit=None)


def test_non_bot_session_has_no_override():
    t = _turn({"kind": "", "origin": "", "project": "/p"})
    assert t._bot_system_override() is None


def test_bot_session_without_config_uses_default(monkeypatch):
    from app.plugins import bot_prompt

    monkeypatch.setattr(bot_prompt, "current", lambda *a, **k: None)
    t = _turn({"kind": "bot", "origin": "qa", "project": "/p"}, _Installs({}))
    assert t._bot_system_override() is None


def test_bot_session_maps_mode_and_text(monkeypatch):
    from app.plugins import bot_prompt

    monkeypatch.setattr(bot_prompt, "current",
                        lambda *a, **k: {"name": "strict", "mode": "replace",
                                         "text": "只做条文检索"})
    t = _turn({"kind": "bot", "origin": "qa", "project": "/p"}, _Installs({}))
    got = t._bot_system_override()
    assert isinstance(got, SystemOverride)
    assert got.mode == "replace" and got.text == "只做条文检索"


def test_bot_prompt_read_failure_never_breaks_turn(monkeypatch):
    from app.plugins import bot_prompt

    def boom(*a, **k):
        raise OSError("盘掉了")

    monkeypatch.setattr(bot_prompt, "current", boom)
    t = _turn({"kind": "bot", "origin": "qa", "project": "/p"}, _Installs({}))
    assert t._bot_system_override() is None
