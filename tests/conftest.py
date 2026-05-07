import os
import pytest
from cryptography.fernet import Fernet


@pytest.fixture(autouse=True)
def test_env(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("API_KEY", "test-api-key-1234567890abcdef")
    monkeypatch.setenv("FERNET_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("A2CR_ENABLE_LEGACY_LOCAL_API", "1")

    import services.config as config_module
    config_module.reset_config()

    import services.db as db_module
    db_module._engine = None
    db_module.reset_web_engine()

    import services.abuse_limits as abuse_limits
    abuse_limits.reset_abuse_limit_state()

    from services.db import init_db
    init_db()

    yield

    config_module.reset_config()
    db_module._engine = None
    db_module.reset_web_engine()
    abuse_limits.reset_abuse_limit_state()
