from __future__ import annotations

import ast
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2]
APP = BACKEND / "app"
ARTIFACTS_PY = APP / "api" / "routers" / "artifacts.py"

WRITE_ROUTES = ("/api/file/delete", "/api/file/move", "/api/file/copy", "/api/file/save")


pass


def test_no_bom_in_python_sources():
    bad = [str(p.relative_to(BACKEND)).replace("\\", "/")
           for p in APP.rglob("*.py")
           if p.read_bytes().startswith(b"\xef\xbb\xbf")]
    assert bad == [], f"这些文件带 BOM，请另存为「UTF-8 无 BOM」: {bad}"


def _route_functions(path: Path) -> dict[str, ast.FunctionDef]:
    pass
    pass
    tree = ast.parse(path.read_text("utf-8-sig"))
    out: dict[str, ast.FunctionDef] = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call) or not isinstance(dec.func, ast.Attribute):
                continue
            if not dec.args or not isinstance(dec.args[0], ast.Constant):
                continue
            route = str(dec.args[0].value)
            method = dec.func.attr.upper()
            out[f"{method} {route}"] = node
    return out


def _called_names(fn: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name):
                names.add(f.id)
            elif isinstance(f, ast.Attribute):
                names.add(f.attr)
    return names


@pytest.mark.parametrize("route", WRITE_ROUTES)
def test_every_file_write_route_resolves_inside_project(route):
    funcs = _route_functions(ARTIFACTS_PY)
    key = f"POST {route}"
    assert key in funcs, f"{route} 端点不见了（路由改名请同步本守卫）"
    assert "_resolve_in_project" in _called_names(funcs[key]), (
        f"{route} 没有经过 _resolve_in_project：路径可能越出项目目录")


def test_no_rmtree_in_api_layer():
    allowed = {"app/api/routers/skills.py"}
    offenders = []
    for p in (APP / "api").rglob("*.py"):
        rel = str(p.relative_to(BACKEND)).replace("\\", "/")
        if rel in allowed:
            continue
        tree = ast.parse(p.read_text("utf-8-sig"))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "rmtree"):
                offenders.append(rel)
                break
    assert offenders == [], f"API 层出现 rmtree: {offenders}"


def test_skill_delete_rejects_path_traversal(container):
    from fastapi import HTTPException

    from app.api.routers.skills import skills_delete

    for bad in ("../backend", "..", ".", "a/b", "a\\b", "", "C:/x"):
        with pytest.raises(HTTPException) as ei:
            skills_delete(bad, c=container)
        assert ei.value.status_code == 400, bad


def test_skill_install_rejects_path_traversal(client):
    for bad in ("../evil", "a/b", "a\\b", "C:/x", "..", "."):
        r = client.post("/api/skills/install",
                        json={"url": "http://127.0.0.1:1/SKILL.md", "name": bad})
        assert r.status_code == 400, bad


def test_skill_dir_is_absolute_not_cwd_relative():
    from app.api.routers import skills as skills_api

    from app.skills import roots as skill_roots

    assert skills_api._skill_dir().is_absolute()
    pass
    assert skills_api._skill_dir() == skill_roots.SKILLS_DIR


def test_workflow_execution_stays_in_executor():
    from app.workflow.engine import WorkflowEngine
    from app.workflow.executor import ExecutionMixin

    assert issubclass(WorkflowEngine, ExecutionMixin)
    for name in ("_execute", "_run_node", "_execute_dag", "_traverse", "_node_context"):
        assert name not in WorkflowEngine.__dict__, f"{name} 又写回 engine.py 了"


def test_agent_runner_keeps_only_main_loop():
    from app.agent.runner import AgentRunner
    from app.agent.guards import GuardsMixin
    from app.agent.subagent_spawn import SpawnMixin
    from app.agent.context import ContextMixin

    assert issubclass(AgentRunner, GuardsMixin)
    assert issubclass(AgentRunner, ContextMixin)
    assert issubclass(AgentRunner, SpawnMixin)
    for name in ("_check_plan_block", "_check_escalation",
                 "_publish_tool_event", "_build_context", "_wf_start", "_spawn"):
        assert name not in AgentRunner.__dict__, f"{name} 又写回 agent_runner 了"


def test_err_helper_never_shadowed():
    import re as _re

    bad = _re.compile(r"^\s*(?:[A-Za-z_][\w.]*\s*,\s*)*err\s*=")
    offenders = []
    for p in (APP / "plugins" / "builtin" / "tools").rglob("*.py"):
        for i, line in enumerate(p.read_text("utf-8").splitlines(), 1):
            if bad.match(line):
                offenders.append(f"{p.name}:{i}: {line.strip()}")
    assert not offenders, "err 被局部变量遮蔽了：\n" + "\n".join(offenders)


def test_trash_dir_excluded_from_listings():
    pass
    pass
    tools_dir = APP / "tools" / "builtin" / "fs"
    fs_files = sorted(tools_dir.glob("*.py"))
    assert fs_files, "fs 工具模块不见了"
    assert any("TRASH_NAME" in f.read_text("utf-8") for f in fs_files)
    assert "TRASH_NAME" in ARTIFACTS_PY.read_text("utf-8")
    pass
    pass
    visible_py = APP / "util" / "visible.py"
    assert "def is_hidden_name" in visible_py.read_text("utf-8")
    projects_py = (APP / "project" / "manager.py").read_text("utf-8")
    assert "visible" in projects_py, "projects.file_tree 必须经过 util/visible 过滤"
    assert "build_tree" in projects_py or "scan_level" in projects_py


def _flatten(routes):
    for r in routes:
        sub = getattr(r, "routes", None)
        if sub:
            yield from _flatten(sub)
            continue
        original = getattr(r, "original_router", None)
        if original is not None:
            yield from _flatten(original.routes)
            continue
        yield r

def test_ws_events_route_registered_before_session_route():
    from app.main import app

    paths = [getattr(r, "path", "") for r in _flatten(app.routes)]
    assert "/ws/events" in paths and "/ws/{sid}" in paths
    assert paths.index("/ws/events") < paths.index("/ws/{sid}")


def test_no_route_is_shadowed_by_earlier_wildcard():
    import re

    from app.main import app

    entries: list[tuple[str, str]] = []
    for r in _flatten(app.routes):
        path = getattr(r, "path", "")
        methods = getattr(r, "methods", None) or {"WEBSOCKET"}
        for m in methods:
            entries.append((m, path))

    def shape(p: str) -> str:
        return re.sub(r"\{[^}]*\}", "{}", p)

    shadowed: list[str] = []
    for i, (m, p) in enumerate(entries):
        if "{" not in p:
            continue
        for m2, p2 in entries[i + 1:]:
            if m2 == m and p2 != p and shape(p) == shape(p2):
                shadowed.append(f"{m} {p2} 被前面的 {p} 遮蔽")
    assert shadowed == [], "路由被前置通配路径遮蔽（永远不会命中）:\n" + "\n".join(shadowed)



pass


@pytest.fixture
def project_dir(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "keep.txt").write_text("重要文件", "utf-8")
    sub = root / "sub"
    sub.mkdir()
    (sub / "inner.txt").write_text("x", "utf-8")
    return root


@pytest.mark.parametrize("path", ["", "   "])
def test_delete_empty_path_rejected(client, project_dir, path):
    r = client.post("/api/file/delete", json={"path": path, "project": str(project_dir)})
    assert r.status_code == 400
    assert (project_dir / "keep.txt").exists()


@pytest.mark.parametrize("path", [".", "./", "sub/..", "sub/../"])
def test_delete_project_root_rejected(client, project_dir, path):
    r = client.post("/api/file/delete", json={"path": path, "project": str(project_dir)})
    assert r.status_code == 400
    assert (project_dir / "keep.txt").exists()
    assert (project_dir / "sub").is_dir()


def test_delete_missing_project_rejected(client, project_dir):
    r = client.post("/api/file/delete", json={"path": str(project_dir / "keep.txt")})
    assert r.status_code == 400
    assert (project_dir / "keep.txt").exists()


def test_delete_traversal_rejected(client, project_dir, tmp_path):
    outside = tmp_path / "outside.txt"
    outside.write_text("别动", "utf-8")
    r = client.post("/api/file/delete", json={
        "path": "../outside.txt", "project": str(project_dir)})
    assert r.status_code == 400
    assert outside.exists()


def test_delete_absolute_outside_rejected(client, project_dir, tmp_path):
    outside = tmp_path / "outside2.txt"
    outside.write_text("别动", "utf-8")
    r = client.post("/api/file/delete", json={"path": str(outside),
                                              "project": str(project_dir)})
    assert r.status_code == 400
    assert outside.exists()


def test_move_and_copy_outside_rejected(client, project_dir, tmp_path):
    outside = tmp_path / "out"
    outside.mkdir()
    r = client.post("/api/file/move", json={
        "path": "keep.txt", "dest": str(outside / "keep.txt"),
        "project": str(project_dir)})
    assert r.status_code == 400
    assert (project_dir / "keep.txt").exists()

    r = client.post("/api/file/copy", json={
        "path": "keep.txt", "dest": "../copied.txt", "project": str(project_dir)})
    assert r.status_code == 400
    assert not (tmp_path / "copied.txt").exists()


def test_save_outside_rejected(client, project_dir, tmp_path):
    outside = tmp_path / "evil.txt"
    r = client.post("/api/file/save", json={
        "path": str(outside), "content": "x", "project": str(project_dir)})
    assert r.status_code == 400
    assert not outside.exists()


def test_delete_inside_project_still_works_and_is_recoverable(client, project_dir):
    r = client.post("/api/file/delete", json={"path": "sub/inner.txt",
                                              "project": str(project_dir)})
    assert r.status_code == 200
    body = r.json()
    assert body["recoverable"] is True
    assert not (project_dir / "sub" / "inner.txt").exists()
    trashed = Path(body["trashed"])
    assert trashed.exists() and trashed.read_text("utf-8") == "x"
    assert (project_dir / ".trash") in trashed.parents


def test_delete_trash_itself_rejected(client, project_dir):
    (project_dir / ".trash" / "20260101-000000").mkdir(parents=True)
    (project_dir / ".trash" / "20260101-000000" / "a.txt").write_text("a")
    r = client.post("/api/file/delete", json={
        "path": ".trash/20260101-000000/a.txt", "project": str(project_dir)})
    assert r.status_code == 400
    assert (project_dir / ".trash" / "20260101-000000" / "a.txt").exists()


pass

def test_audit_call_policy_has_single_source():
    pass
    consumers = [
        APP / "security" / "audit" / "python_auditor.py",
        APP / "security" / "audit" / "funcs.py",
        APP / "security" / "audit" / "scanners" / "pkg_scanner.py",
    ]
    for f in consumers:
        assert f.is_file(), f"缺少 {f.name}"
        src = f.read_text("utf-8")
        assert "call_policy" in src, f"{f.name} 没有引用 call_policy（名单又抄了一份？）"
        pass
        assert '"shutil.rmtree"' not in src, f"{f.name} 里出现了内联名单字面量"
        assert '"pathlib.Path.write_text"' not in src, f"{f.name} 里出现了内联名单字面量"


def test_pkg_scan_names_is_subset_of_full_policy():
    from app.security.audit.call_policy import BLACKLIST_NAMES, PKG_SCAN_NAMES
    assert PKG_SCAN_NAMES <= BLACKLIST_NAMES
    assert "shutil.rmtree" in PKG_SCAN_NAMES
    assert "open" not in PKG_SCAN_NAMES


def test_routers_do_not_construct_http_exception_directly():
    offenders = []
    for f in (APP / "api").rglob("*.py"):
        if f.name == "errors.py":
            continue
        src = f.read_text("utf-8")
        if "HTTPException(" in src:
            offenders.append(f.relative_to(APP).as_posix())
    assert offenders == [], f"这些文件仍在直接构造 HTTPException: {offenders}"


def test_dupes_gate_is_wired_into_check_all():
    root = BACKEND.parent
    script = root / "scripts" / "check_dupes.py"
    assert script.is_file(), "缺少 scripts/check_dupes.py"
    assert (root / "scripts" / "dupes_baseline.txt").is_file(), "缺少重复代码基线"
    sh = (root / "scripts" / "check_all.sh").read_text("utf-8")
    assert "check_dupes.py" in sh, "check_all.sh 没有调用重复代码门禁"
