import os
import pytest
from cryptography.fernet import Fernet


@pytest.fixture(autouse=True)
def test_env(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("API_KEY", "test-api-key-1234567890abcdef")
    monkeypatch.setenv("FERNET_KEY", Fernet.generate_key().decode())

    # Reset module-level engine singleton between tests
    import services.db as db_module
    db_module._engine = None

    from services.db import init_db
    init_db()

    yield

    db_module._engine = None
