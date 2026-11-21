from __future__ import annotations

from app import config as config_mod
from app.store import layout


def test_save_keeps_old_config_when_serialization_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(config_mod, "DATA_DIR", tmp_path)
    store = config_mod.ConfigStore()
    store.config.settings.workspaceRoot = "/first"
    store.save()

    saved = layout.config_json().read_text("utf-8")
    assert "/first" in saved

    pass
    pass
    def _boom():
        raise RuntimeError("炸了")

    object.__setattr__(store.config, "model_dump_json", _boom)
    try:
        store.save()
    except RuntimeError:
        pass
    else:
        raise AssertionError("save 不该吞掉序列化异常")

    pass
    assert layout.config_json().read_text("utf-8") == saved


def test_save_leaves_no_temp_file(tmp_path, monkeypatch):
    monkeypatch.setattr(config_mod, "DATA_DIR", tmp_path)
    store = config_mod.ConfigStore()
    store.save()
    store.save()
    names = sorted(p.name for p in tmp_path.iterdir())
    assert "config.json" in names
    assert not [n for n in names if n.endswith(".tmp")]
