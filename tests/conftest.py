import os
import pytest
from cryptography.fernet import Fernet


@pytest.fixture(autouse=True)
def test_env(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("API_KEY", "test-api-key-1234567890abcdef")
    monkeypatch.setenv("FERNET_KEY", Fernet.generate_key().decode())

    import services.config as config_module
    config_module.reset_config()

    import services.db as db_module
    db_module._engine = None

    from services.db import init_db
    init_db()

    yield

    config_module.reset_config()
    db_module._engine = None
