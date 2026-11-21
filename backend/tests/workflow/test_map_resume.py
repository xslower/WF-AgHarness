from __future__ import annotations

import json

from app.store.runs import RunStore


def test_progress_roundtrip(tmp_path):
    store = RunStore(str(tmp_path / "p"))
    store.prepare("r1", "wf")
    store.append_progress("r1", "m1", {"i": 0, "item_digest": "d0", "result": "A"})
    store.append_progress("r1", "m1", {"i": 1, "item_digest": "d1", "result": "B"})
    assert store.read_progress("r1", "m1") == {"d0": "A", "d1": "B"}


def test_progress_tolerates_partial_line(tmp_path):
    store = RunStore(str(tmp_path / "p"))
    store.prepare("r1", "wf")
    store.append_progress("r1", "m1", {"i": 0, "item_digest": "d0", "result": "A"})
    p = store.progress_path("r1", "m1")
    with p.open("a", encoding="utf-8") as f:
        f.write('{"i": 1, "item_digest": "d1", "resu')
    assert store.read_progress("r1", "m1") == {"d0": "A"}


def test_progress_missing_file(tmp_path):
    store = RunStore(str(tmp_path / "p"))
    store.prepare("r1", "wf")
    assert store.read_progress("r1", "nope") == {}


def test_carry_progress_to_new_run(tmp_path):
    store = RunStore(str(tmp_path / "p"))
    store.prepare("old", "wf")
    store.prepare("new", "wf")
    store.append_progress("old", "m1", {"i": 0, "item_digest": "d0", "result": "A"})
    assert store.carry_progress("old", "new") == 1
    assert store.read_progress("new", "m1") == {"d0": "A"}
    assert store.carry_progress("new", "new") == 0
    assert store.carry_progress("missing", "new") == 0


def test_digest_is_content_based():
    from app.workflow.nodes.flow import _item_digest
    assert _item_digest("第2镜") == _item_digest("第2镜")
    assert _item_digest("第2镜") != _item_digest("第3镜")


async def test_map_skips_completed_items(tmp_path):
    from app.workflow import WorkflowEngine
    from app.workflow.nodes.flow import _item_digest

    store = RunStore(str(tmp_path))

    class Gw:
        config = None

    eng = WorkflowEngine(gateway=Gw(), workspace=str(tmp_path),
                         workflows_dir=tmp_path / "wf")
    wf = {"name": "t", "nodes": [
        {"id": "m1", "type": "map", "items": "a\nb\nc",
         "body": "b1", "collect": "b1", "output": "json"},
        {"id": "b1", "type": "write", "path": "o-${__i__}.txt",
         "content": "ran-${__item__}", "next": ""},
    ]}
    rec, _mode = eng._prepare_run(wf, {}, "ask", None, "", None, "")
    store.append_progress(rec.id, "m1",
                          {"i": 1, "item_digest": _item_digest("b"),
                           "result": '"CACHED-B"'})
    await eng._execute(wf, {}, rec, None)
    assert rec.status == "done", rec.error
    out = json.loads(rec.final)
    assert out["results"][1] == "CACHED-B", out["results"]
    pass
    assert not (tmp_path / "o-1.txt").exists()
    assert (tmp_path / "o-0.txt").exists() and (tmp_path / "o-2.txt").exists()
