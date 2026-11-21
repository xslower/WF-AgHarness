from __future__ import annotations

from pathlib import Path

import pytest

from app.event.bus import HUB
import app.tools.builtin.fs as fs
from app.tools import ToolContext


@pytest.fixture
def ctx(tmp_path):
    return ToolContext(str(tmp_path))


@pytest.fixture
def events():
    got: list[dict] = []
    HUB.on("file.changed", got.append)
    return got


def _payloads(events):
    return [ev["payload"] for ev in events]


async def test_write_emits_created_then_modified(ctx, events):
    await fs.f_write("a.txt", ctx, content="hello")
    assert _payloads(events)[-1]["op"] == "created"
    assert _payloads(events)[-1]["rel"] == "a.txt"

    await fs.f_write("a.txt", ctx, content="hello again")
    assert _payloads(events)[-1]["op"] == "modified"
    assert len(events) == 2


async def test_edit_emits_modified(ctx, events):
    await fs.f_write("a.txt", ctx, content="one two")
    events.clear()
    await fs.f_replace("a.txt", ctx, old="two", new="three")
    assert _payloads(events)[-1]["op"] == "modified"


async def test_create_file_emits(ctx, events):
    await fs.create_file("new/dir", ctx, is_dir=True)
    assert _payloads(events)[-1]["kind"] == "dir"
    await fs.create_file("new/dir/x.md", ctx, content="# hi")
    last = _payloads(events)[-1]
    assert last["op"] == "created" and last["rel"] == "new/dir/x.md"


async def test_delete_emits(ctx, events):
    (Path(ctx.cwd) / "gone.txt").write_text("x", "utf-8")
    await fs.delete_file("gone.txt", ctx)
    assert _payloads(events)[-1]["op"] == "deleted"
    assert _payloads(events)[-1]["kind"] == "file"


async def test_move_emits_two_events(ctx, events):
    (Path(ctx.cwd) / "src.txt").write_text("x", "utf-8")
    await fs.move_file("src.txt", "dst.txt", ctx)
    ops = [p["op"] for p in _payloads(events)]
    assert ops == ["moved_from", "moved_to"]
    assert _payloads(events)[-1]["rel"] == "dst.txt"


async def test_copy_emits_copied(ctx, events):
    (Path(ctx.cwd) / "a.txt").write_text("x", "utf-8")
    await fs.copy_file("a.txt", "b.txt", ctx)
    assert _payloads(events)[-1]["op"] == "copied"
    assert _payloads(events)[-1]["name"] == "b.txt"


async def test_event_failure_does_not_break_write(ctx, monkeypatch):
    def boom(*a, **kw):
        raise RuntimeError("bus down")

    monkeypatch.setattr(HUB, "publish", boom)
    msg = await fs.f_write("still.txt", ctx, content="ok")
    assert (Path(ctx.cwd) / "still.txt").read_text("utf-8") == "ok"
    assert "still.txt" in msg