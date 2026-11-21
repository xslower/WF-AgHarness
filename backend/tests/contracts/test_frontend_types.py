from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
TYPES_DIR = REPO / "frontend" / "src" / "kernel" / "api" / "types"


def _all_ts_src() -> str:
    files = sorted(TYPES_DIR.glob("*.ts"))
    assert files, f"{TYPES_DIR} 下没有类型文件"
    return "\n".join(p.read_text("utf-8") for p in files)


def _py_fields(class_name: str) -> set[str]:
    from app import config as cfg_mod
    import inspect
    import pydantic
    cls = getattr(cfg_mod, class_name, None)
    if cls is None:
        return set()
    assert issubclass(cls, pydantic.BaseModel)
    return set(cls.model_fields)


def _ts_fields(interface: str) -> set[str]:
    m = re.search(rf"export interface {interface} \{{\n(.*?)^\}}",
                  _all_ts_src(), re.S | re.M)
    assert m, f"types/ 下找不到 interface {interface}"
    return set(re.findall(r"^\s{2}(\w+)\??:", m.group(1), re.M))


@pytest.mark.parametrize("name", ["Provider", "Settings", "ModelInfo", "ModelQueues",
                                  "UtilityModels", "ModelSchedule"])
def test_ts_interface_covers_py_model(name):
    py, ts = _py_fields(name), _ts_fields(name)
    missing = sorted(py - ts)
    assert not missing, (
        f"frontend/src/kernel/api/types/ 的 {name} 缺少字段 {missing}；"
        f"设置页保存会把它们静默清空")


def test_types_ts_has_no_extra_required_fields():
    pass
    allowed_extra = {"description"}
    for name in ("Provider", "Settings", "ModelInfo"):
        extra = sorted(_ts_fields(name) - _py_fields(name) - allowed_extra)
        assert not extra, f"types/ 的 {name} 声明了后端不存在的字段 {extra}"


def test_types_barrel_reexports_every_domain():
    barrel = (REPO / "frontend" / "src" / "kernel" / "api" / "types.ts").read_text("utf-8")
    for f in sorted(TYPES_DIR.glob("*.ts")):
        assert f.stem in barrel, f"types.ts 没有 re-export ./types/{f.stem}"


def test_plugin_secret_mask_placeholder_matches():
    from app.plugins import config as cfg

    ts = (REPO / "frontend" / "src" / "kernel" / "api" / "types" / "plugin.ts").read_text("utf-8")
    m = re.search(r'export const MASKED_PLUGIN_SECRET = "([^"]*)"', ts)
    assert m, "types/plugin.ts 缺少 MASKED_PLUGIN_SECRET"
    assert m.group(1) == cfg.MASKED


def test_plugin_config_types_cover_backend_config_types():
    from app.plugins import package as pkgmod

    ts = (REPO / "frontend" / "src" / "kernel" / "api" / "types" / "plugin.ts").read_text("utf-8")
    m = re.search(r"export type PluginConfigType\s*=\s*([^;]+);", ts)
    assert m, "types/plugin.ts 缺少 PluginConfigType"
    declared = set(re.findall(r'"(\w+)"', m.group(1)))
    missing = sorted(set(pkgmod._CONFIG_TYPES) - declared)
    assert not missing, f"前端 PluginConfigType 缺少 {missing}（会渲染不出对应控件）"
