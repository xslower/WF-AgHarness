from __future__ import annotations

import tempfile
import time

from app.provider.gateway import ModelGateway
from .test_gateway import make_config


pass


def test_reset_throttle_state_clears_everything():
    gw = ModelGateway(make_config(["p1/m1", "p2/m2"]))
    gw._demoted.add("p1/m1")
    gw._rate_hits["p1/m1"] = 3
    gw._checker.cool_down("p1/m1", time.time() + 600)
    gw.reset_throttle_state()
    assert gw._demoted == set()
    assert gw._rate_hits == {}
    assert gw._checker.cooldowns == {}


def test_reset_throttle_state_restores_config_order():
    cfg = make_config(["p1/m1", "p2/m2"])
    gw = ModelGateway(cfg)
    gw._demoted.add("p1/m1")
    assert gw._ordered_specs("parent") == ["p2/m2", "p1/m1"]

    gw.reset_throttle_state()
    assert gw._ordered_specs("parent") == ["p1/m1", "p2/m2"]


def _container_for(c):
    return c.sync_config


def test_sync_config_queue_reason_resets_throttle(tmp_dirs):
    from app.api.deps import _THROTTLE_RESET_REASONS

    assert "queue" in _THROTTLE_RESET_REASONS
    pass
    for r in ("provider-add", "provider-update", "provider-delete",
              "model-remove", "fetch-models", "provider-refresh"):
        assert r in _THROTTLE_RESET_REASONS
    pass
    for r in ("settings", "envs", "utility", "env-import"):
        assert r not in _THROTTLE_RESET_REASONS


def test_sync_config_actually_calls_reset(tmp_dirs):
    from app.api.deps import Container

    calls: list[str] = []
    fake = type("G", (), {
        "config": None,
        "reset_throttle_state": lambda self: calls.append("reset"),
    })()
    c = Container.__new__(Container)
    c.__dict__.update({
        "gateway": fake,
        "store": type("S", (), {"config": type("Cfg", (), {
            "settings": type("X", (), {
                "envPython": "", "envNode": "", "projectsRoot": "",
            })(),
            "queues": type("Q", (), {"parent": [], "child": [], "summary": []})(),
        })()})(),
        "search": type("A", (), {"provider": "", "api_key": ""})(),
        "envs": type("E", (), {"bindings": {}})(),
        "projects": type("P", (), {"root": tempfile.gettempdir()})(),
        "hub": None,
    })
    c.sync_config("queue")
    assert calls == ["reset"]
    c.sync_config("settings")
    assert calls == ["reset"]
