import pytest

from app import config as config_mod


@pytest.fixture(autouse=True)
def _isolate_event_bus():
    from app.event.bus import HUB
    from app.event.fanout import fanout

    HUB.clear()
    fanout.reset()
    yield
    HUB.clear()
    fanout.reset()


@pytest.fixture(autouse=True)
def _isolate_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config_mod, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config_mod, "RUNTIME_DIR", None, raising=False)
    from app.store import layout as layout_mod
    _reload_workflow_dirs(tmp_path)
    # 事件库已并入会话库：event_log(L0) 不自己建 store，测试这里注入一个**惰性工厂**
    # （真正用到事件时才实例化 SessionStore），避免给不碰事件的用例凭空建 agent.db。
    #
    # ⚠ 惰性工厂只能当「占位」用：它新建的实例与容器的 `c.sessions` **不是同一个**，
    # 两个实例各自持独立 SQLite 连接指向同一个 `chat.<sid>.db`，WAL 下写-写会报
    # `database is locked`（事件写线程持未提交事务时，`save()` 的全量重写被锁）。
    # 生产 `factory.build_container` 注入的是**同一个** sessions 实例（一份连接），
    # 所以 `container` fixture 建好容器后必须把这里的占位换成容器自己的实例（见下）。
    from app.store import event_log
    from app.chat.sessions import SessionStore
    event_log.reset_caches()
    event_log.set_store(lambda: SessionStore())
    return tmp_path





@pytest.fixture(autouse=True)
def _legacy_marker_projects(monkeypatch):
    from pathlib import Path

    from app.store import layout
    from app.store.kv import RegistryStore
    from app.util import pathx

    real = layout.is_project
    marker = f"/{layout.AGENT_DIR_NAME}/{layout.PLUGINS_DIR_NAME}/"

    def fake(path) -> bool:
        try:
            if real(path):
                return True
            p = pathx.project_dir(path)
            if not p.is_absolute() or marker in str(p):
                return False
            if not (Path(p) / layout.AGENT_DIR_NAME).is_dir():
                return False
            key = pathx.project_path(str(p))
            parent = ""
            for cand in layout.registered_projects():
                if cand != key and key.startswith(cand + "/") and len(cand) > len(parent):
                    parent = cand
            RegistryStore().add(key, parent)
            return True
        except (OSError, TypeError, ValueError):
            return False

    monkeypatch.setattr(layout, "is_project", fake)


def _reload_workflow_dirs(tmp_path) -> None:
    from app import workflow as workflow_mod
    workflow_mod.WORKFLOWS_DIR = tmp_path / "workflows"
    from app.store import layout as layout_mod
    assert layout_mod.data_dir() == tmp_path


@pytest.fixture
def tmp_dirs(tmp_path, monkeypatch):
    _reload_workflow_dirs(tmp_path)
    return tmp_path


@pytest.fixture
def container(tmp_dirs, monkeypatch):
    from app.agent.runner import AgentRunner
    from app.factory import build_container
    from app.tools.builtin.memory import MemoryStore
    from app.project.manager import ProjectManager

    c = build_container()
    c.projects = ProjectManager(str(tmp_dirs / "projects"))


    c.memory = MemoryStore(c.projects)
    # 重建 runner 时也要把工作流路由接上，否则与真实装配不一致：
    # 生产里 build_container 会把 wf_router 交给 runner（workflow 工具的 run/编辑都靠它）。
    c.runner = AgentRunner(c.gateway, c.registry, mcp=c.mcp, policy=c.policy,
                           approvals=c.approvals, envs=c.envs, memory=c.memory,
                           wf_engine=c.wf_router)
    return c


@pytest.fixture
def client(container):
    from fastapi.testclient import TestClient
    import app.main as main_mod
    from app.api.deps import set_container

    # 事件落盘必须与会话落盘**共用同一个 SessionStore 实例**（一份 SQLite 连接）。
    #
    # 生产 `factory.build_container` 里就是这样（`event_log.set_store(sessions)`，
    # 同一个 sessions 也进了 Container），但测试环境有两个额外步骤会把它拆开：
    # ① `_isolate_data_dir`（autouse）注入惰性工厂 `lambda: SessionStore()`；
    # ② 该工厂被任何一次 `_require_store()` 调用就会**实例化并缓存**。
    # 于是 event_log 可能拿着一个与 `container.sessions` 不同的实例，两个连接
    # 写同一个 `chat.<sid>.db`，WAL 下报 `database is locked`：事件写线程把事务
    # 攒到 64 条才 commit，期间 `save()` 的全量重写（`DELETE FROM messages`）
    # 直接撞锁 —— 表现为**整轮对话报错**，且只在测试里出现（生产一份连接没事）。
    #
    # 所以在这里最后钉一次（此时 container 已建好、autouse 也已跑完）。
    from app.store import event_log
    event_log.set_store(container.sessions)
    event_log.reset_caches()

    set_container(main_mod.app, container)
    return TestClient(main_mod.app)



def pytest_configure(config):
    args = [str(a) for a in config.invocation_params.args]
    targets = [a for a in args if a.startswith("tests")]
    full = any(a in ("tests", "tests/") for a in targets) or not targets
    if not full:
        config.option.cov_fail_under = 0


@pytest.fixture(autouse=True)
# 定时调度器是进程级线程：用例里若间接跑了 `_on_startup`，线程会活到进程退出。
# 每个用例后停一次（`stop()` 幂等，没启动就是空操作）。
def _stop_timers():
    yield
    from app.event.schedule import TIMERS
    TIMERS.stop()
