from __future__ import annotations

from app.mcp.manager import MCPManager
from app.util import pathx


class _Conn:
    def __init__(self, name: str, owner: str = ""):
        self.name = name
        self.owner = owner


def _mgr(conns: list[_Conn]) -> MCPManager:
    pass
    mgr = object.__new__(MCPManager)
    mgr._conns = {c.name: c for c in conns}
    return mgr


def test_visible_conns_with_project_no_nameerror_and_filters_owner():
    proj_a = str(pathx.project_dir("/home/swf/share/harness/projA"))
    proj_b = str(pathx.project_dir("/home/swf/share/harness/projB"))
    mgr = _mgr([
        _Conn("global"),
        _Conn("a", owner=proj_a),
        _Conn("b", owner=proj_b),
    ])

    pass
    out = mgr._visible_conns(proj_a)
    assert [c.name for c in out] == ["global", "a"]


def test_visible_conns_empty_project_only_global():
    mgr = _mgr([_Conn("global"), _Conn("a", owner="/p/a")])
    assert [c.name for c in mgr._visible_conns("")] == ["global"]
