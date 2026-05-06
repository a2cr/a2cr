import json
from pathlib import Path

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from main import app
from services.config import reset_config
import services.maintenance as maintenance


ROOT = Path(__file__).resolve().parents[1]


def set_production_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://a2cr_app:test@localhost:5432/a2cr")
    monkeypatch.setenv("FERNET_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("API_KEY_HASH_SECRET", "a" * 40)
    monkeypatch.setenv("AUDIT_HASH_SECRET", "b" * 40)
    monkeypatch.setenv("A2CR_SERVICE_URL", "https://a2cr.example/mcp")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "jwt-secret")
    reset_config()


def test_railway_json_uses_dockerfile_and_healthcheck():
    config = json.loads((ROOT / "railway.json").read_text(encoding="utf-8"))

    assert config["build"]["builder"] == "DOCKERFILE"
    assert config["build"]["dockerfilePath"] == "Dockerfile"
    assert config["deploy"]["healthcheckPath"] == "/api/v1/health"


def test_dockerfile_builds_react_before_python_runtime():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "FROM node:22-slim AS web-build" in dockerfile
    assert "ARG VITE_SUPABASE_ANON_KEY" in dockerfile
    assert 'VITE_SUPABASE_ANON_KEY="$VITE_SUPABASE_ANON_KEY"' in dockerfile
    assert "PUBLIC_SUPABASE_ANON" not in dockerfile
    assert "RUN npm ci" in dockerfile
    assert "npm run build" in dockerfile
    assert "FROM python:3.13-slim AS runtime" in dockerfile
    assert "COPY --from=web-build /app/web/dist ./web/dist" in dockerfile
    assert "uvicorn main:app" in dockerfile


def test_production_same_origin_guard_rejects_unexpected_origin(monkeypatch):
    set_production_env(monkeypatch)

    with TestClient(app) as client:
        response = client.options(
            "/api/v1/health",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 403
    assert "access-control-allow-origin" not in response.headers


def test_production_same_origin_guard_allows_public_origin(monkeypatch):
    set_production_env(monkeypatch)

    with TestClient(app) as client:
        response = client.get("/api/v1/health", headers={"Origin": "https://a2cr.example"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_expire_web_contexts_uses_only_db_expiration_function(monkeypatch):
    executed = []

    class FakeResult:
        def scalar_one(self):
            return 4

    class FakeConnection:
        def execute(self, statement):
            executed.append(str(statement))
            return FakeResult()

    class FakeBegin:
        def __enter__(self):
            return FakeConnection()

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def begin(self):
            return FakeBegin()

    monkeypatch.setattr(maintenance, "validate_runtime_environment", lambda: None)
    monkeypatch.setattr(maintenance, "get_web_engine", lambda: FakeEngine())

    assert maintenance.expire_web_contexts() == 4
    assert executed == ["SELECT app.expire_contexts()"]


def test_web_context_save_expires_old_rows_before_slot_capacity_check():
    service = (ROOT / "services" / "web_context.py").read_text(encoding="utf-8")
    save_start = service.index("def save_context(")

    expire_call = service.index('session.execute(text("SELECT app.expire_contexts()"))', save_start)
    capacity_check = service.index("ensure_active_slot_capacity(", save_start)
    next_slot = service.index("_next_slot_number(", save_start)

    assert expire_call < capacity_check
    assert expire_call < next_slot


def test_web_context_id_based_context_queries_remain_user_scoped():
    service = (ROOT / "services" / "web_context.py").read_text(encoding="utf-8")

    assert "SELECT slot_number FROM public.contexts WHERE id = :id AND user_id = :user_id" in service
    assert "WHERE id = :existing_id\n                      AND user_id = :user_id" in service
    assert "WHERE id = :id\n                  AND user_id = :user_id" in service
