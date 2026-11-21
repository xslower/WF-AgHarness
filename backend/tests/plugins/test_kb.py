from __future__ import annotations

import asyncio

import pytest

from app.plugins.plugin_sdk import kb_index
from app.plugins.plugin_sdk.kb import KBError, KnowledgeBase


@pytest.fixture()
def kb(tmp_dirs):
    db = KnowledgeBase(tmp_dirs / "kb" / "store.db", "")
    yield db
    db.close()


DOCS = [
    {"key": "a", "title": "请假制度", "body": "员工请假需提前三天提交，由直属主管审批。"},
    {"key": "b", "title": "报销制度", "body": "差旅报销需在行程结束后七个工作日内提交发票。"},
]


def test_add_and_lexical_search_returns_hit(kb):
    kb.add("policy", DOCS)
    r = kb.search("policy", "请假 审批")
    assert r["items"][0]["key"] == "a"
    assert r["degraded"] is True
    assert "向量" in r["reason"] or "vector" in r["reason"].lower()


def test_body_is_encrypted_on_disk_but_title_is_plain(tmp_dirs):
    kb = KnowledgeBase(tmp_dirs / "s.db", "")
    kb.add("c", [DOCS[0]])
    kb.close()
    blob = (tmp_dirs / "s.db").read_bytes()
    assert "员工请假需提前".encode() not in blob
    assert "请假".encode() in blob


def test_vectors_require_model_and_lock_it(kb):
    kb.add("v", [{"key": "x", "title": "x", "body": "x"}],
           model="bge-m3", vectors=[[1.0, 0.0, 0.0]])
    assert kb.info("v")["model"] == "bge-m3" and kb.info("v")["dim"] == 3
    with pytest.raises(KBError, match="bge-m3"):
        kb.add("v", [{"key": "y", "title": "y", "body": "y"}],
               model="other", vectors=[[1.0, 0.0, 0.0]])


def test_vector_collection_allows_plain_write_then_fills_gap(kb):
    kb.add("v", [{"key": "x", "title": "x", "body": "x"}],
           model="m", vectors=[[1.0, 0.0]])
    kb.add("v", [{"key": "z", "title": "z", "body": "z"}])
    info = kb.info("v")
    assert info["count"] == 2 and info["vectors"] == 1 and info["missing"] == 1
    pass
    assert kb.search("v", "z", vector=[1.0, 0.0])["missing_vectors"] == 1
    pass
    kb.set_vectors("v", "m", [(info_id(kb, "z"), [0.0, 1.0])])
    assert kb.info("v")["missing"] == 0


def info_id(kb, key: str) -> int:
    return kb.db.execute("SELECT id FROM kb_docs WHERE dkey=?", (key,)).fetchone()[0]


def test_semantic_hit_and_not_degraded(kb):
    kb.add("v", [
        {"key": "1", "title": "差旅", "body": "出差交通与住宿"},
        {"key": "2", "title": "采购", "body": "办公用品采购流程"},
    ], model="m", vectors=[[1.0, 0.0], [0.0, 1.0]])
    pass
    r = kb.search("v", "买东西", vector=[0.05, 1.0])
    assert r["degraded"] is False
    assert r["items"][0]["key"] == "2"


def test_dim_mismatch_degrades_with_reason(kb):
    kb.add("v", [{"key": "1", "title": "t", "body": "b"}],
           model="m", vectors=[[1.0, 0.0]])
    r = kb.search("v", "t", vector=[1.0, 0.0, 0.0])
    assert r["degraded"] is True and "维度" in r["reason"]


def test_add_is_idempotent_by_key(kb):
    kb.add("c", DOCS)
    kb.add("c", DOCS)
    assert kb.info("c")["count"] == 2


def test_delete_and_drop(kb):
    kb.add("c", DOCS)
    assert kb.delete("c", ["a"]) == 1
    assert kb.info("c")["count"] == 1
    assert kb.drop("c") == 1
    assert kb.info("c")["exists"] is False


def test_empty_key_and_empty_query_raise(kb):
    with pytest.raises(KBError, match="key"):
        kb.add("c", [{"key": "", "body": "x"}])
    kb.add("c", DOCS)
    with pytest.raises(KBError, match="query"):
        kb.search("c", "  ")


def test_vectors_count_must_match_docs(kb):
    with pytest.raises(KBError, match="条数"):
        kb.add("v", DOCS, model="m", vectors=[[1.0]])


def test_available_backends_always_has_fallback():
    names = kb_index.available_backends()
    assert "numpy_flat" in names
    assert all(n in {"faiss", "usearch", "numpy_flat"} for n in names)


def test_usearch_is_preferred_when_installed():
    names = kb_index.available_backends()
    if "usearch" in names:
        assert names[0] == "usearch"
        assert kb_index._make_index(4).name == "usearch"


def test_index_backends_agree_on_nearest(tmp_dirs):
    import numpy as np
    dim = 16
    rng = np.random.default_rng(0)
    vecs = (rng.random((50, dim))).tolist()
    ids = list(range(50))
    q = vecs[7]
    expect = 7
    for cls in (kb_index._NumpyIndex, kb_index._FaissIndex, kb_index._UsearchIndex):
        try:
            ix = cls(dim)
        except Exception:
            continue
        ix.add(ids, vecs)
        assert ix.search(q, 1)[0][0] == expect, cls.name


pass
class FakeEmbed:

    def __init__(self, model="bge-m3", dim=4, fail: str = "") -> None:
        self.model, self.dim, self.fail = model, dim, fail
        self.calls: list[tuple[int, str]] = []

    async def __call__(self, texts, model: str = ""):
        self.calls.append((len(texts), model))
        if self.fail:
            return {"ok": False, "error": self.fail}
        return {"ok": True, "model": model or self.model, "dim": self.dim,
                "vectors": [[float(len(t) % 7), 1.0, 2.0, 3.0][:self.dim]
                            for t in texts]}


def test_build_bm25_needs_no_model(kb):
    kb.add("c", DOCS)
    r = asyncio.run(kb.build("c"))
    assert r["engine"] == "bm25" and r["lexical"] == 2
    assert r["embedded"] == 0 and r["model"] == ""
    assert kb.info("c")["missing"] == 2


def test_build_vector_needs_embed_and_locks_model(kb):
    emb = FakeEmbed()
    kb.add("v", DOCS)
    r = asyncio.run(kb.build("v", engine="vector", embed=emb))
    assert r["engine"] == "vector" and r["embedded"] == 2
    assert r["model"] == "bge-m3" and r["dim"] == 4
    assert kb.info("v")["missing"] == 0
    pass
    assert kb.search("v", "请假", vector=[1.0, 1.0, 2.0, 3.0])["degraded"] is False


def test_build_vector_without_embed_raises(kb):
    kb.add("c", DOCS)
    with pytest.raises(KBError, match="embedding"):
        asyncio.run(kb.build("c", engine="vector"))


def test_build_rejects_unknown_engine(kb):
    kb.add("c", DOCS)
    with pytest.raises(KBError, match="engine"):
        asyncio.run(kb.build("c", engine="cosine"))


def test_build_on_missing_or_empty_collection_raises(kb):
    with pytest.raises(KBError, match="没有文档"):
        asyncio.run(kb.build("nope"))


def test_build_vector_is_incremental(kb):
    emb = FakeEmbed()
    kb.add("v", DOCS)
    asyncio.run(kb.build("v", engine="vector", embed=emb))
    assert emb.calls == [(2, "")]
    kb.add("v", [{"key": "c", "title": "加班", "body": "加班需审批"}])
    asyncio.run(kb.build("v", engine="vector", embed=emb))
    assert emb.calls[-1] == (1, "bge-m3")
    asyncio.run(kb.build("v", engine="hybrid", embed=emb))
    assert emb.calls[-1] == (3, "bge-m3")


def test_build_batches_large_collections(kb):
    emb = FakeEmbed()
    kb.add("big", [{"key": f"k{i}", "title": f"t{i}", "body": "正文"}
                   for i in range(150)])
    r = asyncio.run(kb.build("big", engine="vector", embed=emb, batch=64))
    assert [n for n, _ in emb.calls] == [64, 64, 22]
    assert r["embedded"] == 150


def test_build_aborts_when_model_changes_midway(kb):
    kb.add("big", [{"key": f"k{i}", "title": "t", "body": "正文"}
                   for i in range(3)])
    calls = {"n": 0}

    async def flip(texts, model=""):
        calls["n"] += 1
        return {"ok": True, "model": "m1" if calls["n"] == 1 else "m2",
                "dim": 4, "vectors": [[1.0, 0.0, 0.0, 0.0]] * len(texts)}

    with pytest.raises(KBError, match="中途变了"):
        asyncio.run(kb.build("big", engine="vector", embed=flip, batch=1))
    assert kb.info("big")["missing"] == 3


def test_build_surfaces_embed_failure(kb):
    kb.add("c", DOCS)
    with pytest.raises(KBError, match="向量化失败"):
        asyncio.run(kb.build("c", engine="vector",
                             embed=FakeEmbed(fail="上游 401")))


def test_set_vectors_refuses_other_model(kb):
    kb.add("v", DOCS, model="bge-m3",
           vectors=[[1.0, 0.0], [0.0, 1.0]])
    ids = [r[0] for r in kb.db.execute("SELECT id FROM kb_docs")]
    with pytest.raises(KBError, match="不能改用"):
        kb.set_vectors("v", "other", [(ids[0], [1.0, 0.0])])


def test_rebuild_lexical_recovers_dropped_index(kb):
    kb.add("c", DOCS)
    kb.db.execute("DELETE FROM kb_fts")
    kb.db.commit()
    assert kb.search("c", "请假")["lexical_hits"] == 0
    kb.rebuild_lexical("c")
    assert kb.search("c", "请假")["items"][0]["key"] == "a"
