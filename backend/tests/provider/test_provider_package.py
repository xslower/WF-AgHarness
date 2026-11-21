from __future__ import annotations


def test_provider_package_exports_are_same_objects():
    from app.provider import ModelSpec, Provider
    from app.provider.models import Provider as FromModels

    assert Provider is FromModels
    assert ModelSpec.__module__.startswith("app.provider")


def test_legacy_shims_are_gone():
    import importlib.util

    for old in ("app.model_spec", "app.model_ids", "app.model_registry",
                "app.model_availability", "app.provider_store",
                "app.models_meta", "app.gateway", "app.mcpman"):
        assert importlib.util.find_spec(old) is None, f"{old} 仍存在（应为已删的兼容壳）"


def test_submodule_and_package_agree():
    from app.provider import ModelRegistry as PkgRegistry
    from app.provider.availability import AvailabilityChecker as SubChecker
    from app.provider.availability import AvailabilityChecker as PkgChecker
    from app.provider.ids import normalize_model_id as SubNorm
    from app.provider.ids import normalize_model_id as PkgNorm
    from app.provider.meta import classify_model
    from app.provider.registry import ModelRegistry as SubRegistry
    from app.provider.spec import ModelSpec as SubSpec
    from app.provider.spec import ModelSpec as PkgSpec
    from app.provider.store import ProviderStore as SubStore
    from app.provider.store import ProviderStore as PkgStore

    assert PkgRegistry is SubRegistry
    assert PkgChecker is SubChecker
    assert PkgNorm is SubNorm
    assert PkgSpec is SubSpec
    assert PkgStore is SubStore
    assert callable(classify_model)


def test_config_alone_imports_without_cycle():
    import importlib

    import app.config as cfg

    importlib.reload(cfg)
    assert cfg.Provider.__module__ == "app.provider.models"


def test_lazy_attr_raises_for_unknown():
    import pytest

    import app.provider as pkg

    with pytest.raises(AttributeError):
        _ = pkg.NotAThing


def test_queue_names_match_spec_kind():
    from app.provider.spec import QUEUE_CHILD, QUEUE_NAMES, QUEUE_PARENT, QUEUE_SUMMARY

    assert QUEUE_NAMES == (QUEUE_PARENT, QUEUE_CHILD, QUEUE_SUMMARY)


def test_availability_reasons_are_stable_strings():
    from app.provider import REASON_COOLING, REASON_DISABLED, REASON_OK, REASON_QUOTA, REASON_SCHEDULE

    assert (REASON_OK, REASON_DISABLED, REASON_SCHEDULE,
            REASON_COOLING, REASON_QUOTA) == (
        "", "disabled", "schedule", "cooling", "quota")
