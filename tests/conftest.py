import pytest
from cryptography.fernet import Fernet


@pytest.fixture(autouse=True)
def test_env(monkeypatch):
    monkeypatch.setenv("FERNET_KEY", Fernet.generate_key().decode())

    import services.config as config_module
    config_module.reset_config()

    import services.db as db_module
    db_module.reset_web_engine()

    import services.abuse_limits as abuse_limits
    abuse_limits.reset_abuse_limit_state()

    yield

    config_module.reset_config()
    db_module.reset_web_engine()
    abuse_limits.reset_abuse_limit_state()
