from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from main import app
from routers.dashboard import get_current_dashboard_user
from services.auth import AuthenticatedUser
from services.dashboard import (
    CreatedApiKey,
    DashboardAccessLog,
    DashboardApiKey,
    DashboardContext,
    DashboardProfile,
    DashboardStats,
)
import services.dashboard as dashboard_service


USER_ID = UUID("00000000-0000-0000-0000-0000000000a1")


@pytest.fixture
def client():
    app.dependency_overrides[get_current_dashboard_user] = lambda: AuthenticatedUser(USER_ID, "jwt")
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def now():
    return datetime.now(timezone.utc)


def profile(plan="free", detail="compact", retention=86400):
    timestamp = now()
    return DashboardProfile(
        user_id=str(USER_ID),
        plan=plan,
        context_detail_level=detail,
        default_retention_seconds=retention,
        preferred_locale="auto",
        response_language="auto",
        timezone="UTC",
        created_at=timestamp,
        updated_at=timestamp,
    )


def context_item():
    timestamp = now()
    return DashboardContext(
        slot_name="slot-a",
        slot_number=1,
        created_at=timestamp,
        updated_at=timestamp,
        expires_at=timestamp + timedelta(hours=1),
        size_bytes=100,
        compressed_tokens=12,
        saved_tokens=8,
        detail_level="compact",
        model_source="gpt",
        load_count=2,
        resume_context_call='resume_context(slot_name="slot-a")',
        resume_prompt='resume_context(slot_name="slot-a")',
    )


def test_get_profile_returns_current_settings(client, monkeypatch):
    monkeypatch.setattr(dashboard_service, "get_profile", lambda user_id: profile())

    response = client.get("/api/dashboard/profile")

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == str(USER_ID)
    assert body["plan"] == "free"
    assert body["context_detail_level"] == "compact"


def test_patch_profile_does_not_accept_plan_change(client, monkeypatch):
    captured = {}

    def fake_update_profile(**kwargs):
        captured.update(kwargs)
        return profile(retention=43200)

    monkeypatch.setattr(dashboard_service, "update_profile", fake_update_profile)

    response = client.patch(
        "/api/dashboard/profile",
        json={"plan": "pro", "default_retention_seconds": 43200},
    )

    assert response.status_code == 200
    assert "plan" not in captured
    assert captured["default_retention_seconds"] == 43200
    assert response.json()["plan"] == "free"


def test_contexts_return_metadata_without_content(client, monkeypatch):
    monkeypatch.setattr(dashboard_service, "list_contexts", lambda user_id: [context_item()])

    response = client.get("/api/dashboard/contexts")

    assert response.status_code == 200
    item = response.json()[0]
    assert item["slot_name"] == "slot-a"
    assert item["encryption_mode"] == "client"
    assert "content" not in item
    assert "private" not in str(item).lower()


def test_stats_return_no_content(client, monkeypatch):
    monkeypatch.setattr(
        dashboard_service,
        "get_stats",
        lambda user_id: DashboardStats(
            total_saves=3,
            total_loads=4,
            total_deletes=1,
            total_tokens_saved=20,
            active_slots=2,
        ),
    )

    response = client.get("/api/dashboard/stats")

    assert response.status_code == 200
    assert response.json()["total_saves"] == 3
    assert "content" not in response.json()


def test_access_logs_are_sanitized(client, monkeypatch):
    monkeypatch.setattr(
        dashboard_service,
        "list_access_logs",
        lambda user_id, limit=100: [
            DashboardAccessLog(
                action="context.save",
                slot_name="slot-a",
                client_type="api",
                result="success",
                error_code=None,
                size_bytes=120,
                request_id="req-1",
                created_at=now(),
            )
        ],
    )

    response = client.get("/api/dashboard/access-logs?limit=10")

    assert response.status_code == 200
    item = response.json()[0]
    assert item["action"] == "context.save"
    assert "ip_hash" not in item
    assert "user_agent_hash" not in item
    assert "authorization" not in item
    assert "content" not in item


def test_create_api_key_returns_plaintext_once(client, monkeypatch):
    created_at = now()
    monkeypatch.setattr(
        dashboard_service,
        "create_api_key",
        lambda user_id: CreatedApiKey(
            api_key="sk-a2cr-secret-only-once",
            key_prefix="sk-a2cr-secr",
            created_at=created_at,
        ),
    )

    response = client.post("/api/dashboard/api-key")

    assert response.status_code == 201
    body = response.json()
    assert body["api_key"] == "sk-a2cr-secret-only-once"
    assert body["key_prefix"] == "sk-a2cr-secr"


def test_get_api_key_returns_prefix_only(client, monkeypatch):
    monkeypatch.setattr(
        dashboard_service,
        "get_api_key",
        lambda user_id: DashboardApiKey(
            key_prefix="sk-a2cr-secr",
            created_at=now(),
            last_used_at=None,
            revoked_at=None,
        ),
    )

    response = client.get("/api/dashboard/api-key")

    assert response.status_code == 200
    body = response.json()
    assert body["key_prefix"] == "sk-a2cr-secr"
    assert "api_key" not in body
    assert "key_hash" not in body


def test_delete_api_key_revokes(client, monkeypatch):
    captured = {}

    def fake_revoke(user_id):
        captured["user_id"] = user_id

    monkeypatch.setattr(dashboard_service, "revoke_api_key", fake_revoke)

    response = client.delete("/api/dashboard/api-key")

    assert response.status_code == 200
    assert response.json() == {"message": "revoked"}
    assert captured["user_id"] == USER_ID
