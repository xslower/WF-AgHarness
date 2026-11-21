from __future__ import annotations

import os
import stat

import pytest

from app.store import layout, vault


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    monkeypatch.delenv(vault.MASTER_KEY_ENV, raising=False)
    vault._plaintexts.clear()
    yield
    vault._plaintexts.clear()


def test_seal_unseal_roundtrip():
    sealed = vault.seal("sk-super-secret-123")
    assert sealed.startswith(vault.PREFIX)
    assert "sk-super-secret-123" not in sealed
    assert vault.unseal(sealed) == "sk-super-secret-123"


def test_seal_is_idempotent():
    once = vault.seal("abc-secret")
    assert vault.seal(once) == once


def test_unseal_leaves_plain_untouched():
    assert vault.unseal("legacy-plain") == "legacy-plain"
    assert vault.unseal("") == ""
    assert vault.unseal(None) is None


def test_empty_and_non_string_pass_through():
    assert vault.seal("") == ""
    assert vault.seal(None) is None
    assert vault.seal(42) == 42


def test_master_key_file_is_private_and_outside_db_dir():
    p = vault.master_key_path()
    assert p.name == "master.key"
    assert p.parent != layout.agent_db().parent
    assert p.parent.parent == layout.data_dir()
    vault.seal("trigger")
    assert p.is_file()
    mode = stat.S_IMODE(os.stat(p).st_mode)
    assert mode & 0o077 == 0, f"主密钥必须 0600，实际 {oct(mode)}"


def test_env_master_key_overrides_file(monkeypatch):
    monkeypatch.setenv(vault.MASTER_KEY_ENV, "my-passphrase")
    sealed = vault.seal("env-value")
    assert not vault.master_key_path().is_file()
    assert vault.unseal(sealed) == "env-value"


def test_status_contains_no_plaintext():
    s = vault.status()
    assert "sk-super-secret-123" not in str(s)
    assert s["master_key_source"] in ("env", "file", "not_created")


def test_redact_covers_current_and_replaced_values():
    old = vault.seal("old-key-value")
    vault.unseal(old)
    new = vault.seal("new-key-value")
    assert vault.redact("boom old-key-value / new-key-value") == "boom *** / ***"


def test_redact_obj_recurses():
    vault.seal("sk-nested-secret")
    clean = vault.redact_obj({"a": ["x sk-nested-secret y"], "b": {"c": "sk-nested-secret"}})
    assert clean == {"a": ["x *** y"], "b": {"c": "***"}}


def test_bad_cipher_error_has_no_secret():
    sealed = vault.seal("sk-do-not-leak")
    tampered = vault.PREFIX + sealed[len(vault.PREFIX):-4] + "AAAA"
    with pytest.raises(RuntimeError) as e:
        vault.unseal(tampered)
    assert "sk-do-not-leak" not in str(e.value)
    assert vault.PREFIX not in str(e.value)


def test_mask_only_marks_nonempty():
    assert vault.mask("x") == vault.MASKED
    assert vault.mask("") == ""
    assert vault.mask(None) == ""
