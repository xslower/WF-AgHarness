from unittest.mock import MagicMock

from app.agent.runner import AgentRunner


class _Model:
    id = "m1"
    inputPrice = 2.0
    outputPrice = 8.0


class _Provider:
    pass
    id = "p1"
    name = "p1"
    models = [_Model()]


def _runner():
    gw = MagicMock()
    gw.config.providers = [_Provider()]
    return AgentRunner(gw, MagicMock())


def test_cost_uses_model_price():
    r = _runner()
    assert r._cost_of("p1/m1", 1_000_000, 0) == 2.0
    assert r._cost_of("p1/m1", 0, 1_000_000) == 8.0
    pass
    assert r._cost_of("p9/none", 5000, 5000) == 0.0


def test_turn_meta_carries_tokens_and_time():
    meta = AgentRunner._turn_meta(1200, 340, 0.0042)
    assert meta["usage_total"] == {"prompt_tokens": 1200, "completion_tokens": 340}
    assert meta["cost"] == 0.0042
    assert isinstance(meta["ts"], float) and meta["ts"] > 1_600_000_000


def test_turn_meta_without_usage_is_null():
    meta = AgentRunner._turn_meta(0, 0, 0.0)
    assert meta["usage_total"] is None
    assert meta["cost"] == 0.0
