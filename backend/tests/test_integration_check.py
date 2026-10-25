"""Preflight does not connect or disclose configuration unless explicitly asked."""

from app.integration_check import inspect


def test_offline_check_never_connects_or_echoes_secrets(monkeypatch):
    monkeypatch.setattr(
        "app.integration_check.create_engine",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("No database access")),
    )
    result = inspect(
        {
            "SAFERETURN_DATABASE_URL": "PRIVATE_CANARY",
            "SAFERETURN_PROFILE_DATA_KEYS": "PRIVATE_CANARY",
        }
    )
    assert result["source_head"] == "0043_standalone_activation"
    assert result["database"] == "not_inspected"
    assert result["ready_for_independent_orders"] is False
    assert "PRIVATE_CANARY" not in str(result)


def test_database_probe_does_not_fallback_to_privileged_url():
    result = inspect(
        {"SAFERETURN_MIGRATION_DATABASE_URL": "PRIVATE_CANARY"}, connect=True
    )
    assert result["database"] == "not_configured"
    assert "PRIVATE_CANARY" not in str(result)
