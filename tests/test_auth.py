import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from services.auth import (
    AuthError,
    authenticate_api_key,
    hash_api_key,
    verify_supabase_jwt,
)
from services.config import WebConfig, get_web_config, reset_config
from services.db import set_rls_user_context
from services.logs import build_access_log_row, write_access_log


USER_ID = UUID("00000000-0000-0000-0000-0000000000a1")


def web_config() -> WebConfig:
    return WebConfig(
        database_url="postgresql+psycopg://a2cr_app:test@localhost:5432/a2cr",
        fernet_key="fernet",
        api_key_hash_secret="api-hash-secret",
        supabase_jwt_secret="jwt-secret",
        supabase_jwks_url=None,
        supabase_jwt_audience="authenticated",
        supabase_jwt_issuer="https://project.supabase.co/auth/v1",
        a2cr_service_url="https://a2cr.example",
        app_env="test",
        audit_hash_secret="audit-secret",
        public_api_key_prefix="sk-a2cr",
    )


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def make_hs256_token(payload: dict, secret: str = "jwt-secret", header: dict | None = None) -> str:
    header = header or {"alg": "HS256", "typ": "JWT"}
    encoded_header = b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signed = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).digest()
    return f"{encoded_header}.{encoded_payload}.{b64url(signature)}"


def valid_payload() -> dict:
    now = datetime.now(timezone.utc)
    return {
        "sub": str(USER_ID),
        "aud": "authenticated",
        "iss": "https://project.supabase.co/auth/v1",
        "exp": int((now + timedelta(minutes=10)).timestamp()),
        "iat": int(now.timestamp()),
    }


def set_required_web_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://a2cr_app:test@localhost:5432/a2cr")
    monkeypatch.setenv("API_KEY_HASH_SECRET", "api-hash-secret")
    monkeypatch.setenv("A2CR_SERVICE_URL", "https://a2cr.example")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "jwt-secret")


def test_web_config_requires_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("API_KEY_HASH_SECRET", "api-hash-secret")
    monkeypatch.setenv("A2CR_SERVICE_URL", "https://a2cr.example")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "jwt-secret")
    reset_config()

    with pytest.raises(RuntimeError, match="DATABASE_URL is required"):
        get_web_config()


def test_web_config_rejects_service_role_in_runtime(monkeypatch):
    set_required_web_env(monkeypatch)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-secret")
    reset_config()

    with pytest.raises(RuntimeError, match="SUPABASE_SERVICE_ROLE_KEY"):
        get_web_config()


def test_web_config_loads_required_runtime_values(monkeypatch):
    set_required_web_env(monkeypatch)
    reset_config()

    config = get_web_config()

    assert config.database_url.startswith("postgresql+psycopg://")
    assert config.api_key_hash_secret == "api-hash-secret"
    assert config.supabase_jwt_audience == "authenticated"
    assert config.app_env == "test"


def test_verify_supabase_jwt_accepts_valid_token():
    token = make_hs256_token(valid_payload())

    user = verify_supabase_jwt(token, config=web_config())

    assert user.user_id == USER_ID
    assert user.auth_method == "jwt"


def test_verify_supabase_jwt_rejects_expired_token():
    payload = valid_payload()
    payload["exp"] = int((datetime.now(timezone.utc) - timedelta(seconds=1)).timestamp())
    token = make_hs256_token(payload)

    with pytest.raises(AuthError):
        verify_supabase_jwt(token, config=web_config())


def test_verify_supabase_jwt_rejects_wrong_audience():
    payload = valid_payload()
    payload["aud"] = "anon"
    token = make_hs256_token(payload)

    with pytest.raises(AuthError):
        verify_supabase_jwt(token, config=web_config())


def test_verify_supabase_jwt_rejects_wrong_signature():
    token = make_hs256_token(valid_payload(), secret="wrong-secret")

    with pytest.raises(AuthError):
        verify_supabase_jwt(token, config=web_config())


def test_verify_supabase_jwt_rejects_unsigned_alg():
    token = make_hs256_token(valid_payload(), header={"alg": "none"})

    with pytest.raises(AuthError):
        verify_supabase_jwt(token, config=web_config())


class FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeSession:
    def __init__(self, result_value=USER_ID):
        self.result_value = result_value
        self.executed = []

    def execute(self, statement, params=None):
        self.executed.append((str(statement), params or {}))
        return FakeResult(self.result_value)


def test_authenticate_api_key_uses_hmac_hash_and_db_function():
    session = FakeSession()
    config = web_config()

    user = authenticate_api_key(session, "Bearer sk-test-secret", ip_hash="iphash", config=config)

    statement, params = session.executed[0]
    assert user.user_id == USER_ID
    assert "app.resolve_api_key" in statement
    assert params["key_hash"] == hash_api_key("sk-test-secret", config.api_key_hash_secret)
    assert params["key_hash"] != "sk-test-secret"
    assert params["ip_hash"] == "iphash"


def test_authenticate_api_key_rejects_bad_scheme():
    with pytest.raises(AuthError):
        authenticate_api_key(FakeSession(), "Basic sk-test-secret", config=web_config())


def test_authenticate_api_key_rejects_missing_db_match():
    with pytest.raises(AuthError):
        authenticate_api_key(FakeSession(result_value=None), "Bearer sk-test-secret", config=web_config())


def test_set_rls_user_context_uses_set_local():
    session = FakeSession()

    set_rls_user_context(session, USER_ID)

    statement, params = session.executed[0]
    assert "set_config('app.user_id'" in statement
    assert params == {"user_id": str(USER_ID)}


def test_build_access_log_row_hashes_ip_and_user_agent_without_raw_values():
    row = build_access_log_row(
        user_id=USER_ID,
        action="context.save",
        client_type="api",
        result="success",
        slot_name="slot-a",
        ip="203.0.113.10",
        user_agent="Bearer sk-test-secret",
        hash_secret="audit-secret",
    )

    assert row["ip_hash"] != "203.0.113.10"
    assert row["user_agent_hash"] != "Bearer sk-test-secret"
    assert "ip" not in row
    assert "user_agent" not in row
    assert "authorization" not in row
    assert "content" not in row


def test_write_access_log_drops_unapproved_fields():
    session = FakeSession()
    row = build_access_log_row(
        user_id=USER_ID,
        action="context.load",
        client_type="mcp",
        result="failure",
        error_code="slot_not_found",
        hash_secret="audit-secret",
    )
    row["authorization"] = "Bearer sk-test-secret"
    row["content"] = "private context"

    write_access_log(session, row)

    statement, params = session.executed[0]
    assert "INSERT INTO public.access_logs" in statement
    assert "authorization" not in params
    assert "content" not in params
    assert "sk-test-secret" not in params.values()
