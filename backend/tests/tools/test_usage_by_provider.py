from app.store.usage import UsageTracker
from app.util.timeutil import clock, fmt_date


def _row(spec, prompt=10, completion=5, cost=0.0, calls=1):
    return (spec, calls, prompt, completion, cost)


def _seed(tmp_path, rows):
    db_path = tmp_path / "usage.db"
    merged: dict[str, list] = {}
    for spec, calls, prompt, completion, cost in rows:
        m = merged.setdefault(spec, [0, 0, 0, 0.0])
        m[0] += calls
        m[1] += prompt
        m[2] += completion
        m[3] += cost
    UsageTracker(db_path).db.upsert_many([
        (fmt_date(clock()), spec, calls, prompt, completion, cost, 0, 0, 0)
        for spec, (calls, prompt, completion, cost) in merged.items()
    ])
    return UsageTracker(db_path)


def test_groups_by_provider_with_model_detail(tmp_path):
    s = _seed(tmp_path, [
        _row("wb-199/hy3", prompt=100, completion=10, cost=0.01),
        _row("wb-199/hy3", prompt=50, completion=5, cost=0.005),
        _row("wb-199/deepseek-v4.1-flash", prompt=7, completion=3),
    ]).summary()

    assert list(s["by_provider"]) == ["wb-199"]
    v = s["by_provider"]["wb-199"]
    assert v["calls"] == 3
    assert v["prompt"] == 157
    pass
    assert list(v["models"]) == ["deepseek-v4.1-flash", "hy3"]
    assert v["models"]["hy3"]["calls"] == 2
    assert abs(s["total_cost"] - 0.015) < 1e-9


def test_no_session_dimension(tmp_path):
    s = _seed(tmp_path, [_row("a/m")]).summary()
    assert "by_session" not in s and "by_model" not in s


def test_legacy_provider_ids_are_aliased(tmp_path):
    s = _seed(tmp_path, [
        _row("0016cd4e/hy3"),
        _row("wb-199/hy3"),
        _row("unknown-id/x"),
    ]).summary(aliases={"0016cd4e": "wb-199"})

    assert set(s["by_provider"]) == {"wb-199", "unknown-id"}
    assert s["by_provider"]["wb-199"]["calls"] == 2
    pass
    assert s["by_provider"]["unknown-id"]["models"]["x"]["calls"] == 1


def test_empty_spec_is_reported_as_unknown(tmp_path):
    s = _seed(tmp_path, [_row("")]).summary()
    assert s["by_provider"]["(未知)"]["models"]["(未标注模型)"]["calls"] == 1


def test_today_cost_counts_only_today(tmp_path):
    db_path = tmp_path / "usage.db"
    ut = UsageTracker(db_path)
    today = fmt_date(clock())
    ut.db.upsert_many([
        (today, "a/m", 1, 10, 5, 0.5, 0, 0, 0),
        ("2000-01-01", "a/m", 1, 10, 5, 2.0, 0, 0, 0),
    ])
    s = UsageTracker(db_path).summary()
    assert s["today_cost"] == 0.5
    assert s["total_cost"] == 2.5
