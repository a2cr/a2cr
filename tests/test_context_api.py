from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from main import app
from routers.web_context import get_current_api_user
from services.auth import AuthError, AuthenticatedUser
from services.dashboard import DashboardProfile
from services.exceptions import RateLimitExceeded
from services.web_context import (
    WebContextMetadata,
    WebLoadResult,
    WebResumeResult,
    WebSaveResult,
)
import services.dashboard as dashboard_service
import services.web_context as web_context_service


USER_ID = UUID("00000000-0000-0000-0000-0000000000a1")
CONTENT = {
    "goal": "ship web context api",
    "current_state": "testing route",
    "next_action": "assert response",
}


def encrypted(label: str = "ciphertext") -> dict:
    return {
        "version": 1,
        "alg": "Fernet",
        "nonce": "embedded",
        "ciphertext": label,
        "key_wrap": {"type": "local-key", "kid": "test"},
    }


@pytest.fixture
def client():
    app.dependency_overrides[get_current_api_user] = lambda: AuthenticatedUser(USER_ID, "api_key")
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def future_time():
    return datetime.now(timezone.utc) + timedelta(hours=1)


def metadata(slot_name="slot-a", slot_number=1):
    return WebContextMetadata(
        slot_name=slot_name,
        slot_number=slot_number,
        expires_at=future_time(),
        updated_at=future_time(),
        size_bytes=120,
        compressed_tokens=12,
        detail_level="compact",
        model_source="gpt",
        load_count=0,
    )


def profile(plan="free", detail="compact", retention=86400):
    now = future_time()
    return DashboardProfile(
        user_id=str(USER_ID),
        plan=plan,
        context_detail_level=detail,
        default_retention_seconds=retention,
        preferred_locale="auto",
        response_language="auto",
        timezone="UTC",
        created_at=now,
        updated_at=now,
    )


def load_result(slot_name="slot-a", slot_number=1):
    return WebLoadResult(
        slot_name=slot_name,
        slot_number=slot_number,
        content=None,
        expires_at=future_time(),
        compressed_tokens=12,
        detail_level="compact",
        model_source="gpt",
        load_count=1,
        encrypted_content=encrypted(slot_name),
    )


def test_web_save_context_returns_resume_prompt_without_content_or_key(client, monkeypatch):
    captured = {}

    def fake_save_context(**kwargs):
        captured.update(kwargs)
        return WebSaveResult(
            slot_name=kwargs["slot_name"],
            slot_number=kwargs["slot_number"],
            expires_at=future_time(),
            compressed_tokens=12,
            saved_tokens=8,
            resume_context_call='resume_context(slot_name="slot-a")',
            resume_prompt=(
                "A2CR service: https://a2cr.example\n"
                "Use the A2CR MCP tool. Do not guess or call direct HTTP API endpoints.\n"
                'First run: resume_context(slot_name="slot-a")'
            ),
            user_facing_summary="Saved WorkBaton to Slot 1 (`slot-a`).",
        )

    monkeypatch.setattr(web_context_service, "save_context", fake_save_context)

    response = client.post(
        "/api/v1/context",
        json={
            "slot_name": "slot-a",
            "slot_number": 1,
            "encrypted_content": encrypted("slot-a"),
            "compressed_tokens": 12,
            "model_source": "codex",
            "retention_seconds": 86400,
            "detail_level": "compact",
        },
        headers={"Authorization": "Bearer sk-test-secret", "X-A2CR-Client-Type": "mcp"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["slot_name"] == "slot-a"
    assert body["resume_context_call"] == 'resume_context(slot_name="slot-a")'
    assert "A2CR MCP tool" in body["resume_prompt"]
    assert "direct HTTP API" in body["resume_prompt"]
    assert body["user_facing_summary"].startswith("Saved WorkBaton")
    assert "ship web context api" not in body["resume_prompt"]
    assert "ship web context api" not in body["user_facing_summary"]
    assert "sk-test-secret" not in body["resume_prompt"]
    assert "sk-test-secret" not in body["user_facing_summary"]
    assert captured["user_id"] == USER_ID
    assert captured["content_dict"] is None
    assert captured["encrypted_content"]["ciphertext"] == "slot-a"
    assert captured["compressed_tokens"] == 12
    assert captured["model_source"] == "codex"
    assert captured["retention_seconds"] == 86400
    assert captured["detail_level"] == "compact"
    assert captured["meta"].client_type == "mcp"


def test_web_save_context_uses_model_source_as_client_type_when_header_missing(client, monkeypatch):
    captured = {}

    def fake_save_context(**kwargs):
        captured.update(kwargs)
        return WebSaveResult(
            slot_name=kwargs["slot_name"],
            slot_number=kwargs["slot_number"],
            expires_at=future_time(),
            compressed_tokens=12,
            saved_tokens=8,
            resume_context_call='resume_context(slot_name="slot-a")',
            resume_prompt='resume_context(slot_name="slot-a")',
        )

    monkeypatch.setattr(web_context_service, "save_context", fake_save_context)

    response = client.post(
        "/api/v1/context",
        json={
            "slot_name": "slot-a",
            "slot_number": 1,
            "encrypted_content": encrypted("slot-a"),
            "model_source": "codex",
            "detail_level": "compact",
        },
        headers={"Authorization": "Bearer sk-test-secret"},
    )

    assert response.status_code == 201
    assert captured["meta"].client_type == "codex"


def test_web_list_contexts_returns_metadata_without_content(client, monkeypatch):
    captured = {}

    def fake_list_contexts(**kwargs):
        captured.update(kwargs)
        return [metadata()]

    monkeypatch.setattr(web_context_service, "list_contexts", fake_list_contexts)

    response = client.get("/api/v1/contexts", headers={"Authorization": "Bearer sk-test-secret"})

    assert response.status_code == 200
    body = response.json()
    assert body[0]["slot_name"] == "slot-a"
    assert "content" not in body[0]
    assert captured["user_id"] == USER_ID


def test_web_save_context_rejects_plaintext_without_echoing_body(client, monkeypatch):
    def fail_if_called(**kwargs):
        raise AssertionError("plaintext request should fail before service call")

    monkeypatch.setattr(web_context_service, "save_context", fail_if_called)

    response = client.post(
        "/api/v1/context",
        json={"slot_name": "plain", "content": CONTENT},
        headers={"Authorization": "Bearer sk-test-secret", "X-Request-ID": "plain-req"},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "invalid_request"
    assert body["request_id"] == "plain-req"
    assert "ship web context api" not in response.text
    assert "current_state" not in response.text
    assert "sk-test-secret" not in response.text


@pytest.mark.parametrize(
    "hostile_slot_name",
    [
        "<script>alert('x')</script>",
        "=HYPERLINK",
        "+SUM",
        "-cmd",
        "@HYPERLINK",
    ],
)
def test_web_save_context_rejects_hostile_slot_name_without_echoing_value(
    client,
    monkeypatch,
    hostile_slot_name,
):

    def fail_if_called(**kwargs):
        raise AssertionError("invalid slot_name should fail before service call")

    monkeypatch.setattr(web_context_service, "save_context", fail_if_called)

    response = client.post(
        "/api/v1/context",
        json={"slot_name": hostile_slot_name, "encrypted_content": encrypted("slot-a")},
        headers={"Authorization": "Bearer sk-test-secret"},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "invalid_request"
    assert hostile_slot_name not in response.text
    assert "<script>" not in response.text
    assert "HYPERLINK" not in response.text


def test_web_list_contexts_returns_429_when_abuse_limited(client, monkeypatch):
    def fail_if_called(**kwargs):
        raise AssertionError("service should not run after abuse limit")

    def reject(*args, **kwargs):
        raise RateLimitExceeded("context_read_rate_limited")

    monkeypatch.setattr(web_context_service, "list_contexts", fail_if_called)
    monkeypatch.setattr("routers.web_context.enforce_authenticated_rate_limit", reject)

    response = client.get("/api/v1/contexts", headers={"Authorization": "Bearer sk-test-secret"})

    assert response.status_code == 429
    assert response.json()["code"] == "context_read_rate_limited"


def test_web_account_limits_returns_free_compact_plan(client, monkeypatch):
    monkeypatch.setattr(dashboard_service, "get_profile", lambda user_id: profile())

    response = client.get("/api/v1/account/limits", headers={"Authorization": "Bearer sk-test-secret"})

    assert response.status_code == 200
    body = response.json()
    assert body["plan"] == "free"
    assert body["active_slots"] == 5
    assert body["allowed_detail_levels"] == ["compact"]
    assert body["context_detail_level"] == "compact"
    assert body["max_body_bytes"] == 24 * 1024


def test_web_load_context_returns_ciphertext_for_api_key_route(client, monkeypatch):
    monkeypatch.setattr(web_context_service, "load_context", lambda **_: load_result())

    response = client.get("/api/v1/context/slot-a", headers={"Authorization": "Bearer sk-test-secret"})

    assert response.status_code == 200
    body = response.json()
    assert body["content"] is None
    assert body["encrypted_content"]["ciphertext"] == "slot-a"
    assert body["load_count"] == 1


def test_web_load_auth_failure_does_not_lookup_or_leak_slot(client, monkeypatch):
    def fail_auth():
        raise AuthError()

    def fail_if_called(**kwargs):
        raise AssertionError("slot lookup should not run before auth")

    app.dependency_overrides[get_current_api_user] = fail_auth
    monkeypatch.setattr(web_context_service, "load_context", fail_if_called)

    response = client.get(
        "/api/v1/context/private-slot",
        headers={"Authorization": "Bearer sk-test-secret"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_auth"
    assert "private-slot" not in response.text
    assert "sk-test-secret" not in response.text
    assert "Bearer" not in response.text


def test_web_resume_context_returns_candidates_without_loading_content(client, monkeypatch):
    monkeypatch.setattr(
        web_context_service,
        "resume_context",
        lambda **_: WebResumeResult(mode="candidates", candidates=[metadata("proj-a", 1), metadata("proj-b", 2)]),
    )

    response = client.get(
        "/api/v1/context/resume?project=proj",
        headers={"Authorization": "Bearer sk-test-secret"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "candidates"
    assert body["context"] is None
    assert len(body["candidates"]) == 2
    assert "content" not in body["candidates"][0]


def test_web_resume_context_loads_exact_slot(client, monkeypatch):
    monkeypatch.setattr(
        web_context_service,
        "resume_context",
        lambda **_: WebResumeResult(mode="loaded", context=load_result("slot-a", 1)),
    )

    response = client.get(
        "/api/v1/context/resume?slot_name=slot-a",
        headers={"Authorization": "Bearer sk-test-secret"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "loaded"
    assert body["context"]["content"] is None
    assert body["context"]["encrypted_content"]["ciphertext"] == "slot-a"
    assert body["candidates"] == []


def test_web_delete_context_returns_deleted(client, monkeypatch):
    captured = {}

    def fake_delete_context(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(web_context_service, "delete_context", fake_delete_context)

    response = client.delete("/api/v1/context/slot-a", headers={"Authorization": "Bearer sk-test-secret"})

    assert response.status_code == 200
    assert response.json() == {"message": "deleted"}
    assert captured["slot_name"] == "slot-a"
    assert captured["user_id"] == USER_ID
