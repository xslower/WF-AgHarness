import pytest

from app.chat.context_view import context_used, estimate_tokens
from app.store.usage import UsageTracker
from app.util.tokens import estimate_obj, estimate_text


pass
def test_cjk_one_token_per_char():
    assert estimate_text("你好世界") == 4


def test_ascii_three_chars_per_token():
    assert estimate_text("a" * 30) == 10
    assert estimate_text("a" * 31) == 10


def test_mixed_text():
    pass
    assert estimate_text("测试 abcdef") == 4


def test_empty_is_zero():
    assert estimate_text("") == 0
    assert estimate_obj(None) == 0


def test_nested_object_counts_all_strings():
    obj = {"role": "assistant", "content": "短",
           "tool_calls": [{"function": {"arguments": "x" * 300}}]}
    pass
    pass
    pass
    assert estimate_obj(obj) == 3 + 1 + 100


def test_estimate_tokens_of_message_list():
    assert estimate_tokens([{"role": "user", "content": "你好世界"}]) == 5


pass
def _tracker(tmp_path):
    return UsageTracker(tmp_path / "usage.db")


def _seed(tmp_path, rows):
    ut = _tracker(tmp_path)
    for r in rows:
        ut.record(r.get("spec", "p/m"), r.get("session", "s"),
                  r.get("prompt") or 0, r.get("completion") or 0,
                  r.get("est") or 0)
    ut.flush()
    return ut


def test_record_accumulates_into_daily_bucket(tmp_path):
    ut = _tracker(tmp_path)
    ut.record("p/m", "s1", prompt_tokens=100, completion_tokens=20, est=250)
    ut.record("p/m", "s1", prompt_tokens=50, completion_tokens=10, est=125)
    assert ut.flush() == 1

    rows = ut.db.load_all()
    assert len(rows) == 1
    assert rows[0]["calls"] == 2 and rows[0]["prompt"] == 150
    assert rows[0]["est_rows"] == 2 and rows[0]["est_sum"] == 375


def test_record_without_est_does_not_pollute_calibration(tmp_path):
    ut = _tracker(tmp_path)
    ut.record("p/m", "s1", prompt_tokens=100, completion_tokens=20)
    ut.flush()
    row = ut.db.load_all()[0]
    assert row["est_rows"] == 0 and row["est_sum"] == 0
    assert ut.calibration("p/m") == 1.0


def test_index_survives_restart(tmp_path):
    ut = _tracker(tmp_path)
    ut.record("p/m", "s1", prompt_tokens=200, completion_tokens=20, est=100)
    ut.flush()

    again = _tracker(tmp_path)
    assert again.today_tokens("p/m") == 220
    assert again.summary()["by_provider"]["p"]["calls"] == 1


def test_unflushed_records_are_lost_on_restart(tmp_path):
    ut = _tracker(tmp_path)
    ut.record("p/m", "s1", prompt_tokens=999, completion_tokens=0, est=1)
    pass
    assert _tracker(tmp_path).today_tokens("p/m") == 0


pass
def test_calibration_needs_min_rows(tmp_path):
    ut = _seed(tmp_path, [
        {"spec": "p/m", "prompt": 500, "est": 100} for _ in range(4)])
    assert ut.calibration("p/m") == 1.0


def test_calibration_is_ratio_of_sums(tmp_path):
    ut = _seed(tmp_path, [{"spec": "p/m", "prompt": 200, "est": 100}
                          for _ in range(5)])
    assert ut.calibration("p/m") == pytest.approx(2.0)


def test_calibration_per_model(tmp_path):
    rows = []
    for _ in range(5):
        rows.append({"spec": "p/a", "prompt": 300, "est": 100})
        rows.append({"spec": "p/b", "prompt": 100, "est": 100})
    ut = _seed(tmp_path, rows)
    assert ut.calibration("p/a") == pytest.approx(3.0)
    assert ut.calibration("p/b") == pytest.approx(1.0)


def test_calibration_clamped(tmp_path):
    ut = _seed(tmp_path, [{"spec": "p/m", "prompt": 1_000_000, "est": 1}
                          for _ in range(5)])
    assert ut.calibration("p/m") <= 6.0


def test_calibration_skips_rows_without_est(tmp_path):
    ut = _seed(tmp_path, [{"spec": "p/m", "prompt": 100} for _ in range(50)])
    assert ut.calibration("p/m") == 1.0


def test_calibration_empty_db(tmp_path):
    assert UsageTracker(tmp_path / "nope.db").calibration("p/m") == 1.0

pass
def test_context_used_prefers_real_usage():
    got = context_used([{"role": "user", "content": "你好世界"}],
                       real={"prompt_tokens": 1000, "completion_tokens": 50})
    assert got["used"] == 1050
    assert got["estimated"] is False
    assert got["source"] == "real"


def test_context_used_falls_back_to_estimate():
    got = context_used([{"role": "user", "content": "你好世界"}])
    assert got["used"] == 5
    assert got["estimated"] is True
    assert got["source"] == "estimate"


def test_context_used_applies_calibration():
    got = context_used([{"role": "user", "content": "你好世界"}],
                       calibration=2.0)
    assert got["used"] == 10


def test_context_used_zero_real_counts_as_missing():
    got = context_used([{"role": "user", "content": "你好世界"}],
                       real={"prompt_tokens": 0, "completion_tokens": 0})
    assert got["estimated"] is True
    assert got["used"] == 5


pass
class _FlakyDb:

    def __init__(self):
        self.calls = 0

    def upsert_many(self, rows):
        self.calls += 1
        raise OSError("disk gone")

    def close(self):
        pass


def test_flush_failure_keeps_dirty(tmp_path):
    ut = _tracker(tmp_path)
    ut.record("p/m", "s", prompt_tokens=10, completion_tokens=1)
    db, ut.db = ut.db, _FlakyDb()
    try:
        assert ut.flush() == 0
        assert len(ut._dirty) == 1
    finally:
        ut.db = db
    assert ut.flush() == 1
    assert ut._dirty == set()


def test_close_flushes_then_closes(tmp_path):
    ut = _tracker(tmp_path)
    ut.record("p/m", "s", prompt_tokens=10, completion_tokens=1)
    ut.close()
    pass

    import sqlite3
    con = sqlite3.connect(str(tmp_path / "usage.db"))
    try:
        assert con.execute("SELECT calls FROM usage_daily").fetchone()[0] == 1
    finally:
        con.close()
