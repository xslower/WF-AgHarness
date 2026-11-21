from __future__ import annotations

import asyncio
from pathlib import Path

import pytest


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "proj"
    (root / "sub").mkdir(parents=True)
    (root / "a.txt").write_text("hello", "utf-8")
    (root / "sub" / "b.txt").write_text("world", "utf-8")
    return str(root)


def _trashed(root: str) -> list[str]:
    base = Path(root) / ".trash"
    if not base.is_dir():
        return []
    return sorted(str(p.relative_to(base)) for p in base.rglob("*")
                  if p.is_file() and p.name != ".index.json")


def test_delete_rejects_empty_path(client, project):
    r = client.post("/api/file/delete", json={"path": "", "project": project})
    assert r.status_code == 400
    assert (Path(project) / "a.txt").exists()


def test_delete_rejects_project_root(client, project):
    for bad in (project, ".", str(Path(project) / ".")):
        r = client.post("/api/file/delete", json={"path": bad, "project": project})
        assert r.status_code == 400, bad
    assert (Path(project) / "a.txt").exists()


def test_delete_rejects_path_outside_project(client, project, tmp_path):
    outside = tmp_path / "outside.txt"
    outside.write_text("keep me", "utf-8")
    r = client.post("/api/file/delete", json={"path": str(outside), "project": project})
    assert r.status_code == 400
    assert outside.exists()


def test_delete_rejects_parent_traversal(client, project, tmp_path):
    victim = tmp_path / "victim.txt"
    victim.write_text("keep me", "utf-8")
    r = client.post("/api/file/delete", json={"path": "../victim.txt", "project": project})
    assert r.status_code == 400
    assert victim.exists()


def test_delete_requires_project(client, project):
    r = client.post("/api/file/delete", json={"path": str(Path(project) / "a.txt")})
    assert r.status_code == 400


def test_delete_moves_file_to_trash(client, project):
    target = Path(project) / "a.txt"
    r = client.post("/api/file/delete", json={"path": str(target), "project": project})
    assert r.status_code == 200
    body = r.json()
    assert body["recoverable"] is True
    assert not target.exists()
    assert Path(body["trashed"]).is_file()
    assert str(Path(body["trashed"])).startswith(str(Path(project) / ".trash"))
    assert _trashed(project)[0].startswith("bin/a.txt.")
    assert Path(body["trashed"]).read_text("utf-8") == "hello"


def test_delete_moves_dir_to_trash(client, project):
    r = client.post("/api/file/delete",
                    json={"path": str(Path(project) / "sub"), "project": project})
    assert r.status_code == 200
    assert not (Path(project) / "sub").exists()
    assert any(p.startswith("bin/sub.") and p.endswith("b.txt")
               for p in _trashed(project))


def test_delete_twice_does_not_overwrite(client, project):
    target = str(Path(project) / "a.txt")
    first = client.post("/api/file/delete", json={"path": target, "project": project}).json()
    (Path(project) / "a.txt").write_text("second", "utf-8")
    second = client.post("/api/file/delete", json={"path": target, "project": project}).json()
    assert first["trashed"] != second["trashed"]
    assert Path(first["trashed"]).read_text("utf-8") == "hello"
    assert Path(second["trashed"]).read_text("utf-8") == "second"


def test_delete_in_trash_rejected(client, project):
    target = str(Path(project) / "a.txt")
    trashed = client.post("/api/file/delete", json={"path": target, "project": project}).json()
    r = client.post("/api/file/delete", json={"path": trashed["trashed"], "project": project})
    assert r.status_code == 400


def test_move_rejects_dest_outside(client, project, tmp_path):
    src = str(Path(project) / "a.txt")
    r = client.post("/api/file/move",
                    json={"path": src, "dest": str(tmp_path / "out.txt"), "project": project})
    assert r.status_code == 400
    assert Path(src).exists()


def test_save_rejects_path_outside(client, project, tmp_path):
    r = client.post("/api/file/save",
                    json={"path": str(tmp_path / "evil.txt"), "content": "x",
                          "project": project})
    assert r.status_code == 400
    assert not (tmp_path / "evil.txt").exists()


pass
pass
pass
pass


def _ctx_for(project_path, approvals=None):
    root = str(project_path)

    class _C:
        cwd = root
        project = root
        session_id = "ops-safety"
        path_check = None
        request_file_approval = approvals
        report_file = None

        def project_dir(self):
            return root

        @staticmethod
        async def auto_snapshot(*_a, **_k):
            return None

    return _C()


def test_move_rejects_project_root_as_source(tmp_path):
    from app.tools.builtin.fs.paths import move_file
    root = tmp_path / "proj"
    root.mkdir()
    (root / "a.txt").write_text("x", "utf-8")
    out = asyncio.run(move_file(".", str(tmp_path / "stolen"), _ctx_for(root)))
    assert "error" in out
    assert (root / "a.txt").exists()


def test_move_rejects_project_root_as_dest(tmp_path):
    from app.tools.builtin.fs.paths import move_file
    root = tmp_path / "proj"
    root.mkdir()
    (root / "a.txt").write_text("x", "utf-8")
    out = asyncio.run(move_file("a.txt", ".", _ctx_for(root)))
    assert "error" in out
    assert (root / "a.txt").exists()


def test_copy_outside_project_asks_for_approval(tmp_path, monkeypatch):
    from app.tools.builtin.fs import paths as paths_mod
    from app.tools.builtin.fs.paths import copy_file
    monkeypatch.setattr(paths_mod, "_outside_sandbox",
                        lambda *a, **k: True)
    root = tmp_path / "proj"
    root.mkdir()
    (root / "a.txt").write_text("x", "utf-8")
    asked: list[str] = []

    async def deny(title, *_a, **_k):
        asked.append(title)
        return False, None

    out = asyncio.run(copy_file("a.txt", "leak.txt", _ctx_for(root, deny)))
    assert asked, "判为出目录的复制必须走审批（旧版直接放行）"
    assert "error" in out
    assert not (root / "leak.txt").exists()


def test_copy_and_move_share_the_sandbox_predicate():
    import inspect

    from app.tools.builtin.fs import paths as paths_mod

    for fn in (paths_mod.move_file, paths_mod.copy_file):
        src = inspect.getsource(fn)
        assert "_outside_sandbox" in src, fn.__name__
        assert "request_file_approval" in src, fn.__name__


def test_copy_inside_project_needs_no_approval(tmp_path):
    from app.tools.builtin.fs.paths import copy_file
    root = tmp_path / "proj"
    root.mkdir()
    (root / "a.txt").write_text("x", "utf-8")
    asked: list[str] = []

    async def deny(title, *_a, **_k):
        asked.append(title)
        return False, None

    out = asyncio.run(copy_file("a.txt", "b.txt", _ctx_for(root, deny)))
    assert not asked and "error" not in out
    assert (root / "b.txt").read_text("utf-8") == "x"


pass
pass
pass
pass


def test_move_to_existing_dest_does_not_overwrite(client, project):
    (Path(project) / "b.txt").write_text("keep", "utf-8")
    r = client.post("/api/file/move", json={
        "path": "a.txt", "dest": "b.txt", "project": project})
    assert r.status_code == 409
    assert (Path(project) / "b.txt").read_text("utf-8") == "keep"
    assert (Path(project) / "a.txt").exists()


def test_copy_to_existing_dest_does_not_overwrite(client, project):
    (Path(project) / "b.txt").write_text("keep", "utf-8")
    r = client.post("/api/file/copy", json={
        "path": "a.txt", "dest": "b.txt", "project": project})
    assert r.status_code == 409
    assert (Path(project) / "b.txt").read_text("utf-8") == "keep"


def test_copy_same_path_is_400_not_500(client, project):
    r = client.post("/api/file/copy", json={
        "path": "a.txt", "dest": "a.txt", "project": project})
    assert r.status_code == 400
    assert (Path(project) / "a.txt").read_text("utf-8") == "hello"


def test_copy_dir_into_itself_rejected(client, project):
    r = client.post("/api/file/copy", json={
        "path": "sub", "dest": "sub/inner", "project": project})
    assert r.status_code == 400
    assert not (Path(project) / "sub" / "inner").exists()


def test_save_is_atomic_and_keeps_old_on_failure(client, project):
    from app.api.routers import artifacts as mod

    target = Path(project) / "a.txt"
    real = mod.write_text

    def boom(p, text, encoding="utf-8"):
        raise OSError("disk full")

    mod.write_text = boom
    try:
        r = client.post("/api/file/save", json={
            "path": "a.txt", "content": "new", "project": project})
    finally:
        mod.write_text = real
    assert r.status_code == 400
    assert target.read_text("utf-8") == "hello"


def test_preview_huge_image_is_not_inlined(client, project):
    from app.api.routers import artifacts as mod

    big = Path(project) / "big.png"
    big.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 10)
    old = mod.MAX_IMAGE_BYTES
    mod.MAX_IMAGE_BYTES = 8
    try:
        body = client.get("/api/file", params={"path": str(big)}).json()
    finally:
        mod.MAX_IMAGE_BYTES = old
    assert body["kind"] == "text" and "dataurl" not in body
