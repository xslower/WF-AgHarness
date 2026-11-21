from __future__ import annotations

import pytest

from app.regression import all_scenarios, by_id, core_scenarios, matrix, validate_scenario
from app.regression.dsl import substitute
from app.regression.model import BASELINE, CANDIDATE, Step

SCENARIOS = all_scenarios()


def test_all_15_scenarios_registered_and_valid():
    assert len(SCENARIOS) == 15
    assert [s.id for s in SCENARIOS] == [f"TC-{i:02d}" for i in range(1, 16)]
    assert all(not validate_scenario(s) for s in SCENARIOS)
    assert {s.id for s in core_scenarios()} == {
        "TC-01", "TC-02", "TC-03", "TC-04", "TC-05",
        "TC-06", "TC-07", "TC-08", "TC-09"}


def test_tc14_tc15_are_natural_baseline_scenarios():
    for sid in ("TC-14", "TC-15"):
        s = by_id(sid)
        assert s is not None and "FR-09" in s.fr
        assert "fingerprint_matches" in [c for st in s.steps for c in st.checks] or \
               "metrics_within_threshold" in [c for st in s.steps for c in st.checks]


def test_matrix_abab_and_counts():
    specs = matrix(SCENARIOS, "server", 3, "env1", "RUN")
    assert len(specs) == 2 * 15 * 3
    first = specs[0]
    assert first.version_role == BASELINE and specs[1].version_role == CANDIDATE
    assert [s.order for s in specs] == list(range(len(specs)))
    assert all(s.run_id.startswith("RUN-") for s in specs)
    assert all(s.data_seed.startswith("RUN-") for s in specs)


def test_validate_scenario_rejects_bad_steps():
    from app.regression.model import Scenario
    bad = Scenario("X", "bad", steps=(Step("explode"),))
    errors = validate_scenario(bad)
    assert any("trigger" in e for e in errors)
    assert any("explode" in e for e in errors)


def test_substitute_replaces_cfg_placeholders():
    step = Step("setup", "restore_snapshot", params={"ref": "${cfg.snapshot}"})
    out = substitute(step, {"snapshot": "snap_x"})
    assert out.params["ref"] == "snap_x"
    assert substitute(step, {}).params["ref"] == "${cfg.snapshot}"


@pytest.mark.parametrize("platform", ("server", "cli", "desktop", "mobile", "web", "queue"))
def test_all_documented_platforms_supported(platform):
    from app.regression import Adapter, SimulationBackend
    assert Adapter(platform, SimulationBackend()).platform == platform
