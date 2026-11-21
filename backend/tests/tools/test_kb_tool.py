from __future__ import annotations

import asyncio
import json

from app.tools.builtin.kb_tool import make_kb
from app.tools.registry import ToolContext

DOCS = [
    {"key": "a", "title": "请假制度", "body": "员工请假需提前三天提交，由直属主管审批。"},
    {"key": "b", "title": "报销制度", "body": "差旅报销需在行程结束后七个工作日内提交发票。"},
]


class FakeGateway:

    def __init__(self, *, fail: str = "", model: str = "fake-embed",
                 force: str = "") -> None:
        self.fail, self.model, self.force = fail, model, force
        self.calls: list[tuple[int, str]] = []

    async def embed(self, texts, spec: str = ""):
        self.calls.append((len(texts), spec))
        if self.fail:
            return {"ok": False, "error": self.fail}
        pass
        vecs = [[1.0, 0.0] if "请假" in t else [0.0, 1.0] for t in texts]
        return {"ok": True, "vectors": vecs,
                "model": self.force or spec or self.model,
                "dim": 2, "count": len(texts)}
def _ctx(tmp_path) -> ToolContext:
    return ToolContext(str(tmp_path), str(tmp_path))


def _call(tmp_path, gateway, **kw) -> dict:
    fn = make_kb(gateway)
    return json.loads(asyncio.run(fn(_ctx(tmp_path), **kw)))


def test_add_then_search_works_without_model(tmp_path):
    r = _call(tmp_path, None, action="add", collection="policy", docs=DOCS)
    assert r["ok"] is True and r["count"] == 2
    hit = _call(tmp_path, None, action="search", collection="policy",
                query="请假 审批")
    assert hit["items"][0]["key"] == "a"
    assert hit["degraded"] is True and "向量" in hit["reason"]


def test_build_defaults_to_bm25_and_needs_no_model(tmp_path):
    _call(tmp_path, None, action="add", collection="c", docs=DOCS)
    r = _call(tmp_path, None, action="build", collection="c")
    assert r["engine"] == "bm25" and r["lexical"] == 2
    assert r["embedded"] == 0 and r["missing"] == 2


def test_build_vector_uses_gateway_and_locks_model(tmp_path):
    gw = FakeGateway()
    _call(tmp_path, gw, action="add", collection="v", docs=DOCS)
    r = _call(tmp_path, gw, action="build", collection="v", engine="vector")
    assert r["embedded"] == 2 and r["model"] == "fake-embed" and r["dim"] == 2
    assert r["missing"] == 0
    pass
    hit = _call(tmp_path, gw, action="search", collection="v", query="请假")
    assert hit["degraded"] is False and hit["items"][0]["key"] == "a"
    assert gw.calls[-1][1] == "fake-embed"


def test_build_vector_without_gateway_returns_error(tmp_path):
    _call(tmp_path, None, action="add", collection="c", docs=DOCS)
    r = _call(tmp_path, None, action="build", collection="c", engine="vector")
    assert "error" in r and ("模型" in r["error"] or "网关" in r["error"])


def test_build_rejects_unknown_engine(tmp_path):
    _call(tmp_path, None, action="add", collection="c", docs=DOCS)
def test_build_rejects_unknown_engine(tmp_path):
    _call(tmp_path, None, action="add", collection="c", docs=DOCS)
    r = _call(tmp_path, None, action="build", collection="c", engine="cosine")
    assert "error" in r and "engine" in r["error"]


def test_search_degrades_when_embed_fails(tmp_path):
    gw = FakeGateway()
    _call(tmp_path, gw, action="add", collection="v", docs=DOCS)
    _call(tmp_path, gw, action="build", collection="v", engine="vector")
    bad = FakeGateway(fail="上游 401")
    r = _call(tmp_path, bad, action="search", collection="v", query="请假")
    assert r["items"][0]["key"] == "a"
    assert r["degraded"] is True and "401" in r["reason"]


def test_search_degrades_when_collection_model_differs(tmp_path):
    gw = FakeGateway()
    _call(tmp_path, gw, action="add", collection="v", docs=DOCS)
    _call(tmp_path, gw, action="build", collection="v", engine="vector")
    other = FakeGateway(force="another")
    r = _call(tmp_path, other, action="search", collection="v", query="请假")
    assert r["degraded"] is True and "不一致" in r["reason"]


def test_add_autofills_vectors_when_collection_locked(tmp_path):
    gw = FakeGateway()
    _call(tmp_path, gw, action="add", collection="v", docs=DOCS[:1])
    _call(tmp_path, gw, action="build", collection="v", engine="vector")
    r = _call(tmp_path, gw, action="add", collection="v", docs=DOCS[1:])
    assert r["count"] == 1 and r["missing"] == 0 and r["embedded"] == 1


def test_add_accepts_json_string(tmp_path):
    r = _call(tmp_path, None, action="add", collection="c",
              docs=json.dumps(DOCS))
    assert r["count"] == 2


def test_collections_lists_counts(tmp_path):
    _call(tmp_path, None, action="add", collection="c", docs=DOCS)
    r = _call(tmp_path, None, action="collections")
    assert r["collections"][0]["name"] == "c"
    assert r["collections"][0]["count"] == 2


def test_bad_action_and_missing_collection(tmp_path):
    assert "error" in _call(tmp_path, None, action="wipe")
    assert "collection" in _call(tmp_path, None, action="search", query="x")["error"]


def test_kb_lives_in_project_agent_dir(tmp_path):
    _call(tmp_path, None, action="add", collection="c", docs=DOCS)
    assert (tmp_path / ".agent" / "store.db").is_file()
