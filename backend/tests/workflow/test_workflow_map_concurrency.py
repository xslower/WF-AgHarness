from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from app.provider.gateway import Chunk
from app.workflow import WorkflowEngine
from app.workflow.engine import CONTROL_TYPES


class FakeGw:
    def __init__(self):
        self.config = SimpleNamespace(providers=[], settings=SimpleNamespace(policy="yolo"))

    async def chat_stream(self, messages, **kw):
        yield Chunk(type="text", text="ok")


class SlowRegistry:

    schemas: list = []

    def __init__(self, delay: float = 0.05):
        self.delay = delay
        self.active = 0
        self.peak = 0
        self.calls: list[dict] = []

    async def execute(self, name, args, ctx):
        self.active += 1
        self.peak = max(self.peak, self.active)
        self.calls.append(dict(args))
        try:
            await asyncio.sleep(self.delay)
            return f"done:{args.get('path', '')}"
        finally:
            self.active -= 1


def build(tmp_path, max_concurrency=3, reg=None):
    return WorkflowEngine(gateway=FakeGw(), registry=reg or SlowRegistry(),
                          workspace=str(tmp_path), workflows_dir=tmp_path / "wf",
                          max_concurrency=max_concurrency)


MAP_WF = [
    {"id": "m1", "type": "map", "items": '["a", "b", "c", "d"]', "body": "b1",
     "collect": "b1", "next": ""},
    {"id": "b1", "type": "tool", "tool": "f_read",
     "argsJson": '{"path": "${__item__}"}'},
]


async def test_sequential_mode_forces_serial(tmp_path):
    reg = SlowRegistry()
    eng = build(tmp_path, reg=reg)
    nodes = [dict(MAP_WF[0], concurrency=4), MAP_WF[1]]
    rec = await eng.execute_definition({"name": "t", "nodes": nodes},
                                       parallel_mode="sequential")
    assert rec.status == "done", rec.error
    assert reg.peak == 1


async def test_agent_mode_respects_node_concurrency(tmp_path):
    reg = SlowRegistry()
    eng = build(tmp_path, max_concurrency=8, reg=reg)
    nodes = [dict(MAP_WF[0], concurrency=3), MAP_WF[1]]
    rec = await eng.execute_definition({"name": "t", "nodes": nodes},
                                       parallel_mode="agent")
    assert rec.status == "done", rec.error
    assert reg.peak == 3


async def test_global_cap_limits_node_request(tmp_path):
    reg = SlowRegistry()
    eng = build(tmp_path, max_concurrency=2, reg=reg)
    nodes = [dict(MAP_WF[0], concurrency=8), MAP_WF[1]]
    rec = await eng.execute_definition({"name": "t", "nodes": nodes},
                                       parallel_mode="agent")
    assert rec.status == "done", rec.error
    assert reg.peak == 2


async def test_global_setting_can_go_above_four(tmp_path):
    reg = SlowRegistry(delay=0.03)
    eng = build(tmp_path, max_concurrency=5, reg=reg)
    nodes = [dict(MAP_WF[0], items='["a","b","c","d","e"]'), MAP_WF[1]]
    rec = await eng.execute_definition({"name": "t", "nodes": nodes},
                                       parallel_mode="agent")
    assert rec.status == "done", rec.error
    assert reg.peak == 5


async def test_map_concurrency_defaults_to_global(tmp_path):
    reg = SlowRegistry()
    eng = build(tmp_path, max_concurrency=3, reg=reg)
    rec = await eng.execute_definition({"name": "t", "nodes": MAP_WF},
                                       parallel_mode="agent")
    assert rec.status == "done", rec.error
    assert reg.peak == 3


async def test_collect_order_is_stable(tmp_path):
    eng = build(tmp_path, max_concurrency=3)
    nodes = [{"id": "m1", "type": "map", "items": '["1", "2", "3"]', "body": "b1",
              "collect": "b1", "next": ""},
             {"id": "b1", "type": "llm", "prompt": "say ${__item__}",
              "tools": "off"}]
    pass
    class Echo:
        schemas: list = []

        async def execute(self, *a, **k):
            return "x"
    eng.gateway = SimpleNamespace(
        config=SimpleNamespace(providers=[], settings=SimpleNamespace(policy="yolo")),
        chat_stream=lambda *a, **k: _echo(a[0][0]["content"]))
    rec = await eng.execute_definition({"name": "t", "nodes": nodes},
                                       parallel_mode="agent")
    assert rec.status == "done", rec.error
    out = rec.final.split("\n\n")
    assert [x.strip() for x in out] == ["say 1", "say 2", "say 3"]


async def _echo(prompt):
    yield Chunk(type="text", text=prompt)


async def test_item_vars_do_not_cross_talk(tmp_path):
    reg = SlowRegistry()
    eng = build(tmp_path, max_concurrency=3, reg=reg)
    rec = await eng.execute_definition({"name": "t", "nodes": MAP_WF},
                                       parallel_mode="agent")
    assert rec.status == "done", rec.error
    paths = [c["path"] for c in reg.calls]
    assert sorted(paths) == ["a", "b", "c", "d"]


async def test_parallel_state_keys_are_suffixed(tmp_path):
    eng = build(tmp_path, max_concurrency=3)
    rec = await eng.execute_definition({"name": "t", "nodes": MAP_WF},
                                       parallel_mode="agent")
    assert rec.status == "done", rec.error
    keys = set(rec.node_states)
    assert {"b1@0", "b1@1", "b1@2", "b1@3"} <= keys

    eng2 = build(tmp_path, max_concurrency=3)
    rec2 = await eng2.execute_definition({"name": "t", "nodes": MAP_WF},
                                         parallel_mode="sequential")
    assert "b1" in rec2.node_states and "b1@0" not in rec2.node_states


async def test_parallel_failure_propagates(tmp_path):
    class Boom(SlowRegistry):
        async def execute(self, name, args, ctx):
            await asyncio.sleep(0.02)
            if args.get("path") == "c":
                raise RuntimeError("boom")
            return "ok"

    eng = build(tmp_path, max_concurrency=2, reg=Boom())
    rec = await eng.execute_definition({"name": "t", "nodes": MAP_WF},
                                       parallel_mode="agent")
    assert rec.status == "failed"
    assert "boom" in rec.error


async def test_max_concurrency_falls_back_to_at_least_one(tmp_path):
    eng = build(tmp_path, max_concurrency=0)
    assert eng.max_concurrency() == 1
    eng2 = build(tmp_path, max_concurrency="bad")
    assert eng2.max_concurrency() == 3


def test_parallel_slots_pure_logic(tmp_path):
    eng = build(tmp_path, max_concurrency=4)
    assert eng.parallel_slots({}, "sequential") == 1
    assert eng.parallel_slots({"concurrency": 2}, "sequential") == 1
    assert eng.parallel_slots({}, "agent") == 4
    assert eng.parallel_slots({"concurrency": 9}, "agent") == 4
    assert eng.parallel_slots({"concurrency": 2}, "agent") == 2
