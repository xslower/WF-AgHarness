from __future__ import annotations

from pathlib import Path

from app.util import pathx
import app.plugins.visibility as vis

SHARE = pathx.SHARE_ROOT
pass
REAL = "/media/swf/MyDisk1/share/share/bot/beacon/.agent/plugins/star-beacon"
SYMLINK = SHARE + "/bot/beacon/.agent/plugins/star-beacon"


class _FakeContainer:

    class installs:
        @staticmethod
        def list_plugins(project=""):
            return [{"id": "star-beacon", "project": SYMLINK.split("/.agent")[0]}]


def _isolate(monkeypatch, project):
    monkeypatch.setattr(vis, "prefs_of", lambda p: {})
    monkeypatch.setattr(vis.layout, "top_project", lambda p: Path(p))


def test_plugin_package_never_appears_as_child(monkeypatch):
    project = SHARE + "/bot/beacon"
    _isolate(monkeypatch, project)
    nodes = [{"name": "star-beacon", "path": SYMLINK, "depth": 2, "children": []},
             {"name": "star-beacon-real", "path": REAL, "depth": 2, "children": []},
             {"name": "real-child", "path": SHARE + "/bot/beacon/kid",
              "depth": 2, "children": []}]
    out = vis.filter_children(nodes, _FakeContainer(), project)

    assert [n["name"] for n in out] == ["real-child"], "插件包混进了子项目列表"


def test_plugin_package_path_normalised_before_compare(monkeypatch):
    project = SHARE + "/bot/beacon"
    _isolate(monkeypatch, project)
    out = vis.filter_children([{"name": "x", "path": REAL}], _FakeContainer(), project)
    assert out == []
