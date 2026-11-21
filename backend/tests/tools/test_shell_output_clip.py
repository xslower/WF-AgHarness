from __future__ import annotations

from app.tools.text_limit import MAX_OUTPUT, truncate_both, truncate


def test_short_output_untouched():
    s = "[exit 0]\nall good"
    assert truncate_both(s, MAX_OUTPUT, "marker") == s


def test_tail_survives_clipping():
    text = "[exit 1]\n" + "." * 60_000 + "\nshort test summary info\n" \
           "FAILED tests/session/test_a.py::test_one\nFAILED tests/session/test_b.py::test_two\n"
    out = truncate_both(text, 1000, "marker")
    assert out.startswith("[exit 1]")
    assert "FAILED tests/session/test_a.py::test_one" in out
    assert "FAILED tests/session/test_b.py::test_two" in out
    assert "marker" in out
    assert len(out) < 1400


def test_old_truncate_keeps_head_only_for_structured_output():
    out = truncate("HEAD" + "x" * 1000 + "TAIL", 100)
    assert out.startswith("HEAD")
    assert "TAIL" not in out


def test_clip_both_clean_has_no_marker_and_keeps_tail():
    from app.tools.text_limit import clip_both_clean
    text = "HEAD" + "x" * 50_000 + "FAILED tests/a.py::test_x"
    body, original = clip_both_clean(text, 1000)
    assert original == len(text)
    assert "截断" not in body and "省略" not in body and "[" not in body
    assert body.startswith("HEAD")
    assert body.endswith("FAILED tests/a.py::test_x")
    assert len(body) == 1000
