from datetime import datetime, timezone
from uuid import UUID

import pytest

from services.dashboard import create_api_key, update_profile
from services.exceptions import DetailLevelNotAllowed


USER_ID = UUID("00000000-0000-0000-0000-0000000000a1")


class FakeResult:
    def __init__(self, value):
        self.value = type("Row", (), value)()

    def mappings(self):
        return self

    def one(self):
        return self.value


class FakeSession:
    def __init__(self):
        self.executed = []

    def execute(self, statement, params=None):
        self.executed.append((str(statement), params or {}))
        return FakeResult({"key_prefix": "sk-a2cr-secr", "created_at": datetime.now(timezone.utc)})


class FakeTransaction:
    def __init__(self, session):
        self.session = session

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc, tb):
        return False


def test_create_api_key_stores_hmac_hash_not_plaintext(monkeypatch):
    session = FakeSession()

    monkeypatch.setattr("services.dashboard.web_transaction", lambda user_id: FakeTransaction(session))
    monkeypatch.setattr(
        "services.dashboard.get_web_config",
        lambda: type(
            "Config",
            (),
            {"public_api_key_prefix": "sk-a2cr", "api_key_hash_secret": "hash-secret"},
        )(),
    )
    monkeypatch.setattr("services.dashboard.secrets.token_urlsafe", lambda _: "fixed-secret-token")

    created = create_api_key(USER_ID)

    statement, params = session.executed[0]
    assert created.api_key == "sk-a2cr-fixed-secret-token"
    assert params["key_prefix"] == "sk-a2cr-fixe"
    assert params["key_hash"] != created.api_key
    assert "fixed-secret-token" not in params["key_hash"]
    assert "key_hash" in statement


def test_update_profile_rejects_free_detailed(monkeypatch):
    current = type(
        "Profile",
        (),
        {
            "plan": "free",
            "context_detail_level": "compact",
            "default_retention_seconds": 86400,
            "preferred_locale": "auto",
            "response_language": "auto",
            "timezone": "UTC",
        },
    )()
    monkeypatch.setattr("services.dashboard.get_profile", lambda user_id: current)

    with pytest.raises(DetailLevelNotAllowed):
        update_profile(user_id=USER_ID, context_detail_level="detailed")
