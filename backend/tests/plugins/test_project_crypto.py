from __future__ import annotations

import pytest

from app.store import project_crypto as pc
from app.store import vault


@pytest.fixture(autouse=True)
def _clear():
    pc.forget_cache()
    yield
    pc.forget_cache()


def test_roundtrip_in_project():
    sealed = pc.seal_in("", "token-abc")
    assert sealed.startswith(pc.PREFIX) and "token-abc" not in sealed
    assert pc.unseal_in("", sealed) == "token-abc"


def test_plain_passes_through():
    assert pc.unseal_in("", "plain-text") == "plain-text"


def test_seal_is_idempotent():
    once = pc.seal_in("", "x")
    assert pc.seal_in("", once) == once


def test_project_key_is_sealed_by_master_key():
    from app.store.project_crypto import _ProjectKeys
    from app.store import layout
    import sqlite3

    pc.fernet("")
    con = sqlite3.connect(str(layout.agent_db()))
    try:
        row = con.execute("SELECT key FROM project_keys WHERE project=''").fetchone()
    finally:
        con.close()
    assert row and vault.is_sealed(row[0])


def test_different_projects_have_different_keys():
    a = pc.seal_in("/tmp/proj-a", "same-plain")
    b = pc.seal_in("/tmp/proj-b", "same-plain")
    assert a != b
    assert not pc.is_sealed(a.replace(pc.PREFIX, vault.PREFIX))


def test_cannot_unseal_other_projects_ciphertext():
    sealed = pc.seal_in("/tmp/proj-a", "secret")
    with pytest.raises(RuntimeError, match="项目密钥解不开"):
        pc.unseal_in("/tmp/proj-b", sealed)


def test_seal_obj_walks_containers():
    out = pc.seal_obj("", {"a": "v1", "b": ["v2", 3]})
    assert pc.is_sealed(out["a"]) and pc.is_sealed(out["b"][0])
    assert out["b"][1] == 3
