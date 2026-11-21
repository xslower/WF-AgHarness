import asyncio
import json

from app.config import AppConfig

from app.provider.models import ModelInfo, Provider
from app.envs import EnvManager
from app.store.usage import UsageTracker


pass

def test_rewrite_python_pip():
    em = EnvManager({"python": "D:/envs/myvenv"})
    c = em.rewrite("python script.py")
    assert "myvenv" in c and "script.py" in c and not c.startswith("python ")
    c = em.rewrite("pip install requests")
    assert "myvenv" in c and "-m pip" in c
    pass
    c = em.rewrite("echo python_version node_modules")
    assert c == "echo python_version node_modules"


def test_rewrite_node_npm():
    em = EnvManager({"node": "D:/Env/node"})
    c = em.rewrite("node app.js && npm run build")
    assert "Env/node" in c and "app.js" in c and "npm.cmd" in c or "npm" in c


def test_rewrite_no_bindings_noop():
    em = EnvManager()
    assert em.rewrite("python x.py") == "python x.py"


def test_rewrite_path_with_spaces():
    em = EnvManager({"python": "C:/Program Files/venv"})
    c = em.rewrite("python x.py")
    pass
    assert c.startswith('"C:\\Program Files\\venv') or c.startswith('"C:/Program Files/venv')


def test_scan_finds_conda_and_local(tmp_path):
    pass
    import os as _os
    ws = tmp_path / "proj"
    if _os.name == "nt":
        py = ws / ".venv" / "Scripts" / "python.exe"
    else:
        py = ws / ".venv" / "bin" / "python"
    py.parent.mkdir(parents=True)
    py.write_text("", "utf-8")
    em = EnvManager()
    found = em._scan_local_venvs(str(ws))
    assert any(".venv" in e["path"] for e in found)


def test_envs_api(client, tmp_path):
    r = client.get("/api/envs")
    assert r.status_code == 200
    assert "bindings" in r.json() and isinstance(r.json()["found"], list)
    r = client.put("/api/envs", json={"python": "D:/envs/x", "node": ""})
    assert r.status_code == 200
    assert client.get("/api/config").json()["settings"]["envPython"] == "D:/envs/x"


pass

def test_usage_record_and_summary(tmp_path):
    from app.provider.registry import ModelRegistry
    cfg = AppConfig()
    cfg.providers = [Provider(id="p", name="p", baseUrl="https://x/v1", apiKey="k",
                              models=[ModelInfo(id="m", inputPrice=2.0, outputPrice=8.0)])]
    t = UsageTracker(tmp_path / "u.jsonl",
                     unit_price=ModelRegistry(cfg).unit_price)
    t.record("p/m", "s1", 1000, 500)
    t.record("p/m", "s2", 1000, 0)
    s = t.summary()
    pass
    assert s["by_provider"]["p"]["calls"] == 2
    assert s["by_provider"]["p"]["prompt"] == 2000
    assert s["by_provider"]["p"]["models"]["m"]["calls"] == 2
    pass
    assert abs(s["total_cost"] - 0.008) < 1e-6
    assert "by_session" not in s



def test_usage_via_gateway_sink(tmp_path):
    import httpx
    from app.provider.gateway import ModelGateway

    cfg = AppConfig()
    cfg.providers = [Provider(id="p", name="p", baseUrl="https://p/v1", apiKey="k",
                              models=[ModelInfo(id="m")])]
    cfg.queues.parent = ["p/m"]

    def handler(req):
        return httpx.Response(200, text=(
            'data: {"choices":[{"delta":{"content":"ok"}}]}\n'
            'data: {"usage":{"prompt_tokens":11,"completion_tokens":7}}\n'
            'data: [DONE]\n'))

    from app.provider.registry import ModelRegistry as _MR
    gw = ModelGateway(cfg, transport=httpx.MockTransport(handler))
    ut = UsageTracker(tmp_path / "u.db",
                      unit_price=_MR(cfg).unit_price)
    gw.usage_sink = ut.record

    async def go():
        async for _ in gw.chat_stream([{"role": "user", "content": "hi"}],
                                      session_id="sess9"):
            pass
    asyncio.run(go())
    pass
    pass
    assert ut.flush() == 1
    rec = ut.db.load_all()[0]
    assert rec["spec"] == "p/m"
    assert rec["prompt"] == 11 and rec["completion"] == 7

def test_usage_api(client):
    r = client.get("/api/usage")
    assert r.status_code == 200
    body = r.json()
    assert "by_provider" in body
    assert "by_session" not in body



pass

class FakeGw:
    def __init__(self, fail=False):
        self.fail = fail
        self.calls = []

    async def chat_stream(self, messages, tools=None, effort="medium",
                          spec="", session_id=""):
        self.calls.append((spec, messages[-1]["content"]))
        if self.fail:
            raise RuntimeError("down")
        from app.provider.gateway import Chunk
        yield Chunk(type="text", text="任务: 修bug。已改 app.py:10。未完: 测试。")


def _msgs(n=12):
    return [{"role": "user" if i % 2 == 0 else "assistant", "content": f"msg{i}"}
            for i in range(n)]


def test_summarize_batch_renders_batch_and_uses_summary_queue():
    from app.chat.compaction import ContextCompactor
    gw = FakeGw()
    batch = [{"_seq": i, "role": "user" if i % 2 == 0 else "assistant",
              "content": f"msg{i}"} for i in range(6)]
    out = asyncio.run(ContextCompactor(gw).summarize_batch(batch))
    assert gw.calls[0][0] == "summary"
    for i in range(6):
        assert f"msg#{i}" in gw.calls[0][1] and f"msg{i}" in gw.calls[0][1]
    assert out == {}


def test_summarize_batch_failure_returns_empty():
    from app.chat.compaction import ContextCompactor
    batch = [{"_seq": 0, "role": "user", "content": "x"}]
    out = asyncio.run(ContextCompactor(FakeGw(fail=True)).summarize_batch(batch))
    assert out == {}


def test_merge_falls_back_to_folded_without_summaries():
    from app.chat.compaction import ContextCompactor
    folded = [{"_seq": 0, "role": "user", "content": "长文" * 50}]
    assert ContextCompactor.merge(folded, {}) == folded


def test_summarize_batch_empty_batch_noop():
    from app.chat.compaction import ContextCompactor
    gw = FakeGw()
    out = asyncio.run(ContextCompactor(gw).summarize_batch([]))
    assert out == {} and gw.calls == []
