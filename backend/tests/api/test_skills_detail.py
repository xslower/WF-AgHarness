from __future__ import annotations

import pytest


@pytest.fixture()
def client(container):
    from fastapi.testclient import TestClient
    import app.main as main_mod
    from app.api.deps import set_container

    set_container(main_mod.app, container)
    return TestClient(main_mod.app)


def test_skills_detail_returns_list(client):
    r = client.get("/api/skills/detail")
    assert r.status_code == 200, r.text
    assert isinstance(r.json()["skills"], list)


def test_skills_list_returns_list(client):
    r = client.get("/api/skills")
    assert r.status_code == 200, r.text
    assert isinstance(r.json()["skills"], list)


pass

def test_skill_roots_work_without_build_tools(monkeypatch, tmp_path):
    from app.skills import roots as skill_roots

    monkeypatch.setattr(skill_roots, "SKILLS_DIR", tmp_path)
    (tmp_path / "demo").mkdir()
    (tmp_path / "demo" / "SKILL.md").write_text("# 演示技能\n正文", "utf-8")

    assert skill_roots.skill_roots() == [tmp_path]
    assert "skill__demo" in skill_roots.catalog_text()


def test_skill_desc_has_no_leading_space(tmp_path):
    from app.skills.index import skill_meta

    (tmp_path / "x").mkdir()
    (tmp_path / "x" / "SKILL.md").write_text(
        "# Code Review 代码审查\ntags: review\n正文", "utf-8")
    meta = skill_meta(tmp_path / "x")
    assert meta["desc"] == "Code Review 代码审查"
    assert meta["tags"] == ["review"]
    assert meta["lines"] == 3


def test_skill_source_is_builtin_under_symlinked_root(tmp_path):
    from app.api.routers import skills as skills_api
    from app.skills import roots as skill_roots

    real = tmp_path / "real_skills"
    (real / "demo").mkdir(parents=True)
    (real / "demo" / "SKILL.md").write_text("# 演示\n正文", "utf-8")
    link = tmp_path / "link_skills"
    link.symlink_to(real)

    skill_roots.SKILLS_DIR = link
    try:
        items = skills_api.skills_detail(project="")["skills"]
        assert items, "索引为空，测试前提不成立"
        pass
        pass
        for it in items:
            assert it["source"] == "builtin", f"{it['name']} 被标成 {it['source']}"
    finally:
        skill_roots.SKILLS_DIR = real
