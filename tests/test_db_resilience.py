from __future__ import annotations

from pathlib import Path

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy.exc import DBAPIError, TimeoutError

import services.db as db
from main import app
from services.config import reset_config
from services.db_errors import classify_db_error


def set_web_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://a2cr_app:test@localhost:5432/a2cr")
    monkeypatch.setenv("FERNET_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("API_KEY_HASH_SECRET", "a" * 40)
    monkeypatch.setenv("AUDIT_HASH_SECRET", "b" * 40)
    monkeypatch.setenv("A2CR_SERVICE_URL", "https://a2cr.example/mcp")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "jwt-secret")
    reset_config()
    db.reset_web_engine()


class FakeOrig:
    def __init__(self, sqlstate: str):
        self.sqlstate = sqlstate


def test_db_sqlstate_errors_are_classified_safely():
    cases = {
        "40P01": ("db_deadlock_retry", 503),
        "40001": ("db_serialization_retry", 503),
        "55P03": ("db_lock_timeout", 503),
        "57014": ("db_statement_timeout", 503),
        "23505": ("db_unique_conflict", 409),
    }

    for sqlstate, expected in cases.items():
        exc = DBAPIError.instance("SELECT secret FROM table", {}, FakeOrig(sqlstate), Exception)
        classification = classify_db_error(exc)
        assert (classification.code, classification.status) == expected
        assert "SELECT" not in classification.message
        assert "secret" not in classification.message


def test_db_pool_timeout_is_retryable():
    classification = classify_db_error(TimeoutError("QueuePool limit reached"))

    assert classification.code == "db_pool_timeout"
    assert classification.status == 503
    assert classification.retry_after == 2
    assert "QueuePool" not in classification.message


def test_web_engine_uses_bounded_pool_settings(monkeypatch):
    set_web_env(monkeypatch)
    created = {}

    def fake_create_engine(url, **kwargs):
        created["url"] = url
        created["kwargs"] = kwargs
        return object()

    monkeypatch.setattr(db, "create_engine", fake_create_engine)

    db.get_web_engine()

    assert created["kwargs"]["pool_pre_ping"] is True
    assert created["kwargs"]["pool_size"] == 5
    assert created["kwargs"]["max_overflow"] == 5
    assert created["kwargs"]["pool_timeout"] == 5.0
    assert created["kwargs"]["pool_recycle"] == 1800


def test_web_transaction_sets_timeouts_before_rls_context(monkeypatch):
    set_web_env(monkeypatch)
    executed = []

    class FakeBegin:
        def __enter__(self):
            return None

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeSession:
        def __init__(self, engine):
            pass

        def begin(self):
            return FakeBegin()

        def execute(self, statement, params=None):
            executed.append((str(statement), params))

        def close(self):
            pass

    monkeypatch.setattr(db, "get_web_engine", lambda: object())
    monkeypatch.setattr(db, "Session", FakeSession)

    with db.web_transaction("00000000-0000-0000-0000-000000000001"):
        pass

    assert executed[:3] == [
        ("SELECT set_config(:name, :value, true)", {"name": "statement_timeout", "value": "8000ms"}),
        ("SELECT set_config(:name, :value, true)", {"name": "lock_timeout", "value": "2000ms"}),
        (
            "SELECT set_config(:name, :value, true)",
            {"name": "idle_in_transaction_session_timeout", "value": "10000ms"},
        ),
    ]
    assert executed[3][0] == "SELECT set_config('app.user_id', :user_id, true)"


def test_readiness_endpoint_returns_safe_not_ready(monkeypatch):
    set_web_env(monkeypatch)

    class FakeResult:
        ready = False
        checks = {"columns": False}
        missing = {"columns": ["contexts.encryption_mode"]}

    monkeypatch.setattr("routers.health.get_web_engine", lambda: object())
    monkeypatch.setattr("routers.health.check_schema_readiness", lambda engine: FakeResult())

    with TestClient(app) as client:
        response = client.get("/api/v1/health/readiness")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "ready": False,
        "checks": {"columns": False},
        "missing": {"columns": ["contexts.encryption_mode"]},
    }


def test_workbaton_mutations_take_user_advisory_lock():
    source = Path(db.__file__).with_name("web_context.py")
    web_context_source = source.read_text(encoding="utf-8")

    save_start = web_context_source.index("def save_context(")
    delete_start = web_context_source.index("def delete_context(")

    assert web_context_source.index("acquire_user_mutation_lock(session, user_id)", save_start) < web_context_source.index(
        'session.execute(text("SELECT app.expire_contexts()"))', save_start
    )
    assert web_context_source.index("acquire_user_mutation_lock(session, user_id)", delete_start) < web_context_source.index(
        "DELETE FROM public.contexts", delete_start
    )
