import importlib
import sys

import pytest


def test_production_settings_reject_incomplete_security_configuration(monkeypatch):
    original_base = sys.modules.get("config.settings.base")
    monkeypatch.setenv("SECRET_KEY", "production-secret-for-test")
    monkeypatch.setenv("DEBUG", "False")
    monkeypatch.setenv("ALLOWED_HOSTS", "supportflow.example.com")
    monkeypatch.delenv("CSRF_TRUSTED_ORIGINS", raising=False)
    sys.modules.pop("config.settings.base", None)
    sys.modules.pop("config.settings.production", None)

    try:
        with pytest.raises(RuntimeError, match="CSRF_TRUSTED_ORIGINS"):
            importlib.import_module("config.settings.production")
    finally:
        sys.modules.pop("config.settings.production", None)
        sys.modules.pop("config.settings.base", None)
        if original_base is not None:
            sys.modules["config.settings.base"] = original_base
