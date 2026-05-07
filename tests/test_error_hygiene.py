from __future__ import annotations

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy.exc import DBAPIError

from main import app
from services.config import reset_config


FORBIDDEN_SNIPPETS = (
    "Authorization",
    "Bearer",
    "sk-a2cr-secret",
    "postgresql://",
    "postgresql+psycopg://",
    "DATABASE_URL",
    "SELECT secret",
    "request_body_secret",
    "Traceback",
    "RuntimeError",
)


class FakeOrig:
    def __init__(self, sqlstate: str):
        self.sqlstate = sqlstate


def set_web_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://a2cr_app:test@localhost:5432/a2cr")
    monkeypatch.setenv("FERNET_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("API_KEY_HASH_SECRET", "a" * 40)
    monkeypatch.setenv("AUDIT_HASH_SECRET", "b" * 40)
    monkeypatch.setenv("A2CR_SERVICE_URL", "https://a2cr.example/mcp")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "jwt-secret")
    reset_config()


def assert_no_secret_leak(response):
    body = response.text
    for snippet in FORBIDDEN_SNIPPETS:
        assert snippet not in body


def test_unexpected_exception_response_is_generic(monkeypatch):
    def raise_unexpected(full_path):
        raise RuntimeError(
            "Authorization: Bearer sk-a2cr-secret DATABASE_URL=postgresql://user:pass@db SELECT secret request_body_secret"
        )

    monkeypatch.setattr("main._render_spa_index", raise_unexpected)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            "/dashboard",
            headers={"X-Request-ID": "Bearer sk-a2cr-secret"},
        )

    assert response.status_code == 500
    body = response.json()
    assert body["code"] == "internal_error"
    assert body["message"] == "Request failed."
    assert body["request_id"] != "Bearer sk-a2cr-secret"
    assert_no_secret_leak(response)


def test_db_exception_response_hides_sql_and_secrets(monkeypatch):
    def raise_db_error(full_path):
        raise DBAPIError.instance(
            "SELECT secret FROM table WHERE token = 'sk-a2cr-secret'",
            {},
            FakeOrig("57014"),
            Exception,
        )

    monkeypatch.setattr("main._render_spa_index", raise_db_error)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/dashboard", headers={"X-Request-ID": "req-safe-1"})

    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "db_statement_timeout"
    assert body["request_id"] == "req-safe-1"
    assert_no_secret_leak(response)


def test_schema_readiness_db_error_hides_internals(monkeypatch):
    set_web_env(monkeypatch)

    def raise_db_error(engine):
        raise DBAPIError.instance(
            "SELECT secret FROM readiness WHERE token = 'sk-a2cr-secret'",
            {},
            FakeOrig("57014"),
            Exception,
        )

    monkeypatch.setattr("routers.health.get_web_engine", lambda: object())
    monkeypatch.setattr("routers.health.check_schema_readiness", raise_db_error)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            "/api/v1/health/readiness",
            headers={"Origin": "https://a2cr.example", "X-Request-ID": "readiness-req"},
        )

    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "db_statement_timeout"
    assert body["request_id"] == "readiness-req"
    assert_no_secret_leak(response)


def test_invalid_auth_response_does_not_echo_header_secret(monkeypatch):
    set_web_env(monkeypatch)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            "/api/v1/contexts",
            headers={"Authorization": "Basic sk-a2cr-secret", "X-Request-ID": "auth-req"},
        )

    assert response.status_code == 401
    body = response.json()
    assert body["code"] == "invalid_auth"
    assert_no_secret_leak(response)
