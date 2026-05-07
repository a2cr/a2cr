import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives.hashes import SHA256

from services.auth import (
    AuthError,
    authenticate_api_key,
    hash_api_key,
    verify_supabase_jwt,
)
from services.config import WebConfig, get_web_config, is_request_origin_allowed, reset_config, validate_runtime_environment
from services.db import set_rls_user_context
from services.logs import build_access_log_row, sanitize_log_request_id, write_access_log


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


def jwks_config() -> WebConfig:
    config = web_config()
    return WebConfig(
        database_url=config.database_url,
        fernet_key=config.fernet_key,
        api_key_hash_secret=config.api_key_hash_secret,
        supabase_jwt_secret=None,
        supabase_jwks_url="https://project.supabase.co/auth/v1/.well-known/jwks.json",
        supabase_jwt_audience=config.supabase_jwt_audience,
        supabase_jwt_issuer=config.supabase_jwt_issuer,
        a2cr_service_url=config.a2cr_service_url,
        app_env=config.app_env,
        audit_hash_secret=config.audit_hash_secret,
        public_api_key_prefix=config.public_api_key_prefix,
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


def make_es256_token(payload: dict, private_key, kid: str = "test-key") -> str:
    header = {"alg": "ES256", "typ": "JWT", "kid": kid}
    encoded_header = b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signed = f"{encoded_header}.{encoded_payload}".encode("ascii")
    der_signature = private_key.sign(signed, ec.ECDSA(SHA256()))
    r, s = decode_dss_signature(der_signature)
    raw_signature = r.to_bytes(32, "big") + s.to_bytes(32, "big")
    return f"{encoded_header}.{encoded_payload}.{b64url(raw_signature)}"


def public_jwk(private_key, kid: str = "test-key") -> dict:
    public_numbers = private_key.public_key().public_numbers()
    return {
        "kty": "EC",
        "crv": "P-256",
        "kid": kid,
        "alg": "ES256",
        "use": "sig",
        "x": b64url(public_numbers.x.to_bytes(32, "big")),
        "y": b64url(public_numbers.y.to_bytes(32, "big")),
    }


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


def set_required_web_env_with_jwks(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://a2cr_app:test@localhost:5432/a2cr")
    monkeypatch.setenv("FERNET_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("API_KEY_HASH_SECRET", "api-hash-secret")
    monkeypatch.setenv("A2CR_SERVICE_URL", "https://a2cr.example")
    monkeypatch.setenv("SUPABASE_JWKS_URL", "https://project.supabase.co/auth/v1/.well-known/jwks.json")


def set_required_production_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://a2cr_app:test@localhost:5432/a2cr")
    monkeypatch.setenv("FERNET_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("API_KEY_HASH_SECRET", "a" * 40)
    monkeypatch.setenv("AUDIT_HASH_SECRET", "b" * 40)
    monkeypatch.setenv("A2CR_SERVICE_URL", "https://a2cr.example/mcp")
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


def test_web_config_accepts_jwks_url_without_legacy_secret(monkeypatch):
    set_required_web_env_with_jwks(monkeypatch)
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    reset_config()

    config = get_web_config()

    assert config.supabase_jwt_secret is None
    assert config.supabase_jwks_url == "https://project.supabase.co/auth/v1/.well-known/jwks.json"


def test_web_config_rejects_service_role_in_runtime(monkeypatch):
    set_required_web_env(monkeypatch)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-secret")
    reset_config()

    with pytest.raises(RuntimeError, match="SUPABASE_SERVICE_ROLE_KEY"):
        get_web_config()


def test_runtime_validation_requires_web_env_in_production(monkeypatch):
    set_required_production_env(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    reset_config()

    with pytest.raises(RuntimeError, match="DATABASE_URL is required"):
        validate_runtime_environment()


def test_runtime_validation_rejects_invalid_fernet_key(monkeypatch):
    set_required_production_env(monkeypatch)
    monkeypatch.setenv("FERNET_KEY", "not-a-fernet-key")
    reset_config()

    with pytest.raises(RuntimeError, match="FERNET_KEY"):
        validate_runtime_environment()


def test_runtime_validation_rejects_http_public_url_in_production(monkeypatch):
    set_required_production_env(monkeypatch)
    monkeypatch.setenv("A2CR_SERVICE_URL", "http://a2cr.example/mcp")
    reset_config()

    with pytest.raises(RuntimeError, match="HTTPS public URL"):
        validate_runtime_environment()


def test_runtime_validation_rejects_localhost_public_url_in_production(monkeypatch):
    set_required_production_env(monkeypatch)
    monkeypatch.setenv("A2CR_SERVICE_URL", "https://localhost:8000/mcp")
    reset_config()

    with pytest.raises(RuntimeError, match="localhost"):
        validate_runtime_environment()


def test_runtime_validation_rejects_unsafe_allowed_origin_in_production(monkeypatch):
    set_required_production_env(monkeypatch)
    monkeypatch.setenv("A2CR_ALLOWED_ORIGINS", "https://a2cr.example,http://localhost:5173")
    reset_config()

    with pytest.raises(RuntimeError, match="Allowed production origins"):
        validate_runtime_environment()


def test_same_origin_policy_uses_public_service_origin(monkeypatch):
    set_required_production_env(monkeypatch)
    reset_config()

    assert is_request_origin_allowed("https://a2cr.example")
    assert not is_request_origin_allowed("https://evil.example")


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


def test_verify_supabase_jwt_accepts_valid_es256_token(monkeypatch):
    private_key = ec.generate_private_key(ec.SECP256R1())
    token = make_es256_token(valid_payload(), private_key)

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"keys": [public_jwk(private_key)]}

    monkeypatch.setattr("services.auth._jwks_cache", {})
    monkeypatch.setattr("httpx.get", lambda url, timeout=5: FakeResponse())

    user = verify_supabase_jwt(token, config=jwks_config())

    assert user.user_id == USER_ID
    assert user.auth_method == "jwt"


def test_verify_supabase_jwt_rejects_wrong_es256_signature(monkeypatch):
    private_key = ec.generate_private_key(ec.SECP256R1())
    wrong_key = ec.generate_private_key(ec.SECP256R1())
    token = make_es256_token(valid_payload(), private_key)

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"keys": [public_jwk(wrong_key)]}

    monkeypatch.setattr("services.auth._jwks_cache", {})
    monkeypatch.setattr("httpx.get", lambda url, timeout=5: FakeResponse())

    with pytest.raises(AuthError):
        verify_supabase_jwt(token, config=jwks_config())


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
    assert statement == "SELECT set_config('app.user_id', :user_id, true)"
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


def test_access_log_request_id_allows_only_safe_values():
    safe_row = build_access_log_row(
        user_id=USER_ID,
        action="context.load",
        client_type="mcp",
        result="success",
        request_id="req-123.safe:value",
    )
    secret_row = build_access_log_row(
        user_id=USER_ID,
        action="context.load",
        client_type="mcp",
        result="failure",
        request_id="sk-test-secret",
    )

    assert safe_row["request_id"] == "req-123.safe:value"
    assert secret_row["request_id"] is None
    assert sanitize_log_request_id("req_1") == "req_1"
    assert sanitize_log_request_id("Bearer sk-test-secret") is None
    assert sanitize_log_request_id("sk-test-secret") is None


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


def test_write_access_log_sanitizes_direct_request_id():
    session = FakeSession()
    row = build_access_log_row(
        user_id=USER_ID,
        action="context.load",
        client_type="mcp",
        result="failure",
        error_code="slot_not_found",
        hash_secret="audit-secret",
    )
    row["request_id"] = "Bearer sk-test-secret"

    write_access_log(session, row)

    _, params = session.executed[0]
    assert params["request_id"] is None
    assert "sk-test-secret" not in params.values()
