from __future__ import annotations

import pytest

from app.regression import from_mapping
from app.regression.config import with_repeats

COMPLETE = {
    "platform": "server",
    "system.module": "harness.agent",
    "baseline.version": "v1",
    "candidate.version": "v2",
    "criteria.function": "产出完整",
    "env.target": "local",
}


def test_g0_passes_with_all_required_fields():
    gate = from_mapping(COMPLETE).validate()
    assert gate.passed and gate.blockers == ()
    pass
    assert any("change.list" in w for w in gate.warnings)
    assert any("临时阈值" in w for w in gate.warnings)


@pytest.mark.parametrize("key", tuple(COMPLETE))
def test_g0_blocks_when_any_required_field_missing(key):
    data = {k: v for k, v in COMPLETE.items() if k != key}
    gate = from_mapping(data).validate()
    assert not gate.passed
    assert any(key in b for b in gate.blockers)


def test_nested_config_shape_is_accepted():
    cfg = from_mapping({
        "platform": "cli",
        "system": {"module": "harness.cli"},
        "baseline": {"version": "a"},
        "candidate": {"version": "b"},
        "criteria": {"function": "ok", "output": {"min_records": 2}},
        "env": {"target": "ci"},
    })
    assert cfg.validate().passed
    assert cfg.output_rules == {"min_records": 2}
    assert cfg.module == "cli"


def test_thresholds_explicit_vs_temporary():
    cfg = from_mapping({**COMPLETE, "thresholds": {
        "metrics": {"duration_ms": 0.2}, "sigma": {"rss_mb": 3}}})
    theta, severe, temporary = cfg.theta("duration_ms")
    assert (theta, temporary) == (0.2, False)
    assert severe > theta
    theta, _, temporary = cfg.theta("rss_mb")
    assert temporary and theta >= cfg.thresholds.min_threshold


def test_repeats_never_below_one():
    assert with_repeats(from_mapping(COMPLETE), 0).repeats == 1
    assert with_repeats(from_mapping(COMPLETE), 3).repeats == 3
