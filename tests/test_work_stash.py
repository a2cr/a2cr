from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from main import app
from routers.web_context import get_current_api_user
from services.auth import AuthError, AuthenticatedUser
from services.exceptions import AppError, PlanLimitExceeded
from services.limits import FREE_STASH_LIMITS, PRO_STASH_LIMITS, get_stash_limits
from services.work_stash import (
    WorkStashEntry,
    WorkStashEntryMeta,
    WorkStashListResult,
    WorkStashStoreResult,
)
import services.work_stash as work_stash_service

USER_ID = UUID("00000000-0000-0000-0000-0000000000b1")
ENTRY_KEY = "myapp_api_spec_v1"
ENCRYPTED_VALUE = '{"version":1,"alg":"Fernet","ciphertext":"abc","key_wrap":{"type":"local-key","kid":"test"}}'


def future_time() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=1)


def store_result(entry_key: str = ENTRY_KEY, size_bytes: int = 128) -> WorkStashStoreResult:
    return WorkStashStoreResult(
        entry_key=entry_key,
        expires_at=future_time(),
        size_bytes=size_bytes,
        quota_used_bytes=size_bytes,
        quota_bytes=FREE_STASH_LIMITS.quota_bytes,
        entry_count=1,
        entry_limit=FREE_STASH_LIMITS.max_entries,
    )


def get_entry(entry_key: str = ENTRY_KEY) -> WorkStashEntry:
    now = future_time()
    return WorkStashEntry(
        entry_key=entry_key,
        encrypted_value=ENCRYPTED_VALUE,
        size_bytes=len(ENCRYPTED_VALUE),
        tags=["api", "spec"],
        created_at=now,
        updated_at=now,
        expires_at=now,
    )


def list_result(entries: int = 1) -> WorkStashListResult:
    now = future_time()
    return WorkStashListResult(
        entries=[
            WorkStashEntryMeta(
                entry_key=f"key_{i}",
                size_bytes=100,
                tags=["api"],
                created_at=now,
                updated_at=now,
                expires_at=now,
            )
            for i in range(entries)
        ],
        total_size_bytes=100 * entries,
        quota_bytes=FREE_STASH_LIMITS.quota_bytes,
        entry_count=entries,
        entry_limit=FREE_STASH_LIMITS.max_entries,
    )


@pytest.fixture
def client():
    app.dependency_overrides[get_current_api_user] = lambda: AuthenticatedUser(USER_ID, "api_key")
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# プラン制限の定数確認
# ---------------------------------------------------------------------------

def test_free_stash_limits_values():
    limits = FREE_STASH_LIMITS
    assert limits.plan == "free"
    assert limits.quota_bytes == 256 * 1024
    assert limits.ttl_seconds == 7 * 24 * 60 * 60
    assert limits.max_entries == 50
    assert limits.max_entry_bytes == 8 * 1024
    assert limits.writes_per_hour == 60
    assert limits.reads_per_hour == 300


def test_pro_stash_limits_values():
    limits = PRO_STASH_LIMITS
    assert limits.plan == "pro"
    assert limits.quota_bytes == 1024 * 1024
    assert limits.ttl_seconds == 30 * 24 * 60 * 60
    assert limits.max_entries == 500
    assert limits.max_entry_bytes == 32 * 1024
    assert limits.writes_per_hour == 600
    assert limits.reads_per_hour == 3000


def test_get_stash_limits_returns_free_by_default():
    assert get_stash_limits(None).plan == "free"
    assert get_stash_limits("free").plan == "free"


def test_get_stash_limits_returns_pro():
    assert get_stash_limits("pro").plan == "pro"


# ---------------------------------------------------------------------------
# POST /api/v1/work-stash  （store）
# ---------------------------------------------------------------------------

def test_store_work_stash_returns_quota_info(client, monkeypatch):
    captured = {}

    def fake_store(**kwargs):
        captured.update(kwargs)
        return store_result()

    monkeypatch.setattr(work_stash_service, "store_work_stash", fake_store)

    response = client.post(
        "/api/v1/work-stash",
        json={
            "entry_key": ENTRY_KEY,
            "encrypted_value": ENCRYPTED_VALUE,
            "size_bytes": 128,
            "tags": ["api", "spec"],
        },
        headers={"Authorization": "Bearer sk-test"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["entry_key"] == ENTRY_KEY
    assert body["quota_bytes"] == FREE_STASH_LIMITS.quota_bytes
    assert body["entry_limit"] == FREE_STASH_LIMITS.max_entries
    assert captured["user_id"] == USER_ID
    assert captured["entry_key"] == ENTRY_KEY
    assert captured["tags"] == ["api", "spec"]


def test_store_work_stash_rejects_invalid_entry_key(client, monkeypatch):
    def fail_if_called(**kwargs):
        raise AssertionError("service should not run with invalid key")

    monkeypatch.setattr(work_stash_service, "store_work_stash", fail_if_called)

    for bad_key in ["", "a" * 257, "key with spaces", "key/slash"]:
        response = client.post(
            "/api/v1/work-stash",
            json={"entry_key": bad_key, "encrypted_value": ENCRYPTED_VALUE, "size_bytes": 10},
            headers={"Authorization": "Bearer sk-test"},
        )
        assert response.status_code == 422, f"expected 422 for key: {bad_key!r}"
        if bad_key:
            assert bad_key not in response.text


def test_store_work_stash_returns_413_when_entry_too_large(client, monkeypatch):
    def raise_too_large(**kwargs):
        raise AppError("entry_too_large", "Entry exceeds per-entry limit", 413)

    monkeypatch.setattr(work_stash_service, "store_work_stash", raise_too_large)

    response = client.post(
        "/api/v1/work-stash",
        json={"entry_key": ENTRY_KEY, "encrypted_value": ENCRYPTED_VALUE, "size_bytes": 999999},
        headers={"Authorization": "Bearer sk-test"},
    )

    assert response.status_code == 413
    assert response.json()["code"] == "entry_too_large"


def test_store_work_stash_returns_429_when_quota_exceeded(client, monkeypatch):
    def raise_quota(**kwargs):
        raise PlanLimitExceeded("stash_quota_exceeded", "Quota exceeded")

    monkeypatch.setattr(work_stash_service, "store_work_stash", raise_quota)

    response = client.post(
        "/api/v1/work-stash",
        json={"entry_key": ENTRY_KEY, "encrypted_value": ENCRYPTED_VALUE, "size_bytes": 128},
        headers={"Authorization": "Bearer sk-test"},
    )

    assert response.status_code == 429
    assert response.json()["code"] == "stash_quota_exceeded"


def test_store_work_stash_does_not_echo_encrypted_value_in_error(client, monkeypatch):
    def raise_error(**kwargs):
        raise AppError("entry_too_large", "Entry exceeds per-entry limit", 413)

    monkeypatch.setattr(work_stash_service, "store_work_stash", raise_error)

    secret_cipher = "SUPER_SECRET_CIPHER_TEXT_DO_NOT_ECHO"
    response = client.post(
        "/api/v1/work-stash",
        json={"entry_key": ENTRY_KEY, "encrypted_value": secret_cipher, "size_bytes": 99999},
        headers={"Authorization": "Bearer sk-test"},
    )

    assert response.status_code == 413
    assert secret_cipher not in response.text


# ---------------------------------------------------------------------------
# GET /api/v1/work-stash/{entry_key}  （get）
# ---------------------------------------------------------------------------

def test_get_work_stash_returns_encrypted_value(client, monkeypatch):
    monkeypatch.setattr(work_stash_service, "get_work_stash", lambda **_: get_entry())

    response = client.get(
        f"/api/v1/work-stash/{ENTRY_KEY}",
        headers={"Authorization": "Bearer sk-test"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["entry_key"] == ENTRY_KEY
    assert body["encrypted_value"] == ENCRYPTED_VALUE
    assert body["tags"] == ["api", "spec"]


def test_get_work_stash_returns_404_for_missing_key(client, monkeypatch):
    def raise_not_found(**kwargs):
        raise AppError("stash_entry_not_found", "WorkStash entry not found or expired", 404)

    monkeypatch.setattr(work_stash_service, "get_work_stash", raise_not_found)

    response = client.get(
        "/api/v1/work-stash/nonexistent_key",
        headers={"Authorization": "Bearer sk-test"},
    )

    assert response.status_code == 404
    assert response.json()["code"] == "stash_entry_not_found"
    assert "nonexistent_key" not in response.text


# ---------------------------------------------------------------------------
# GET /api/v1/work-stash  （list）
# ---------------------------------------------------------------------------

def test_list_work_stash_returns_metadata_without_values(client, monkeypatch):
    monkeypatch.setattr(work_stash_service, "list_work_stash", lambda **_: list_result(2))

    response = client.get(
        "/api/v1/work-stash",
        headers={"Authorization": "Bearer sk-test"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["entry_count"] == 2
    assert body["quota_bytes"] == FREE_STASH_LIMITS.quota_bytes
    for entry in body["entries"]:
        assert "encrypted_value" not in entry
        assert "value" not in entry


def test_list_work_stash_passes_tag_filter(client, monkeypatch):
    captured = {}

    def fake_list(**kwargs):
        captured.update(kwargs)
        return list_result(0)

    monkeypatch.setattr(work_stash_service, "list_work_stash", fake_list)

    response = client.get(
        "/api/v1/work-stash?tag_filter=api,spec",
        headers={"Authorization": "Bearer sk-test"},
    )

    assert response.status_code == 200
    assert captured["tag_filter"] == ["api", "spec"]


def test_list_work_stash_returns_empty_list_when_no_entries(client, monkeypatch):
    monkeypatch.setattr(work_stash_service, "list_work_stash", lambda **_: list_result(0))

    response = client.get("/api/v1/work-stash", headers={"Authorization": "Bearer sk-test"})

    assert response.status_code == 200
    body = response.json()
    assert body["entries"] == []
    assert body["entry_count"] == 0


# ---------------------------------------------------------------------------
# DELETE /api/v1/work-stash/{entry_key}  （delete）
# ---------------------------------------------------------------------------

def test_delete_work_stash_returns_204(client, monkeypatch):
    captured = {}

    def fake_delete(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(work_stash_service, "delete_work_stash", fake_delete)

    response = client.delete(
        f"/api/v1/work-stash/{ENTRY_KEY}",
        headers={"Authorization": "Bearer sk-test"},
    )

    assert response.status_code == 204
    assert captured["entry_key"] == ENTRY_KEY
    assert captured["user_id"] == USER_ID


def test_delete_work_stash_returns_404_for_missing_key(client, monkeypatch):
    def raise_not_found(**kwargs):
        raise AppError("stash_entry_not_found", "WorkStash entry not found or expired", 404)

    monkeypatch.setattr(work_stash_service, "delete_work_stash", raise_not_found)

    response = client.delete(
        "/api/v1/work-stash/ghost_key",
        headers={"Authorization": "Bearer sk-test"},
    )

    assert response.status_code == 404
    assert "ghost_key" not in response.text


# ---------------------------------------------------------------------------
# DELETE /api/v1/work-stash  （delete all）
# ---------------------------------------------------------------------------

def test_delete_all_work_stash_returns_deleted_count(client, monkeypatch):
    monkeypatch.setattr(work_stash_service, "delete_all_work_stash", lambda **_: 5)

    response = client.delete(
        "/api/v1/work-stash",
        headers={"Authorization": "Bearer sk-test"},
    )

    assert response.status_code == 200
    assert response.json()["deleted_count"] == 5


def test_delete_all_work_stash_returns_zero_when_empty(client, monkeypatch):
    monkeypatch.setattr(work_stash_service, "delete_all_work_stash", lambda **_: 0)

    response = client.delete("/api/v1/work-stash", headers={"Authorization": "Bearer sk-test"})

    assert response.status_code == 200
    assert response.json()["deleted_count"] == 0


# ---------------------------------------------------------------------------
# セキュリティ境界
# ---------------------------------------------------------------------------

def test_work_stash_auth_failure_does_not_leak_entry_key(client, monkeypatch):
    def fail_auth():
        raise AuthError()

    def fail_if_called(**kwargs):
        raise AssertionError("service should not run before auth")

    app.dependency_overrides[get_current_api_user] = fail_auth
    monkeypatch.setattr(work_stash_service, "get_work_stash", fail_if_called)

    response = client.get(
        "/api/v1/work-stash/secret_project_key",
        headers={"Authorization": "Bearer sk-test"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_auth"
    assert "secret_project_key" not in response.text
    assert "Bearer" not in response.text
    assert "sk-test" not in response.text


def test_work_stash_store_auth_failure_does_not_leak_value(client, monkeypatch):
    def fail_auth():
        raise AuthError()

    app.dependency_overrides[get_current_api_user] = fail_auth
    secret_cipher = "CONFIDENTIAL_CIPHER_MUST_NOT_LEAK"

    response = client.post(
        "/api/v1/work-stash",
        json={"entry_key": ENTRY_KEY, "encrypted_value": secret_cipher, "size_bytes": 10},
        headers={"Authorization": "Bearer sk-test"},
    )

    assert response.status_code == 401
    assert secret_cipher not in response.text


def test_work_stash_list_response_never_includes_encrypted_value(client, monkeypatch):
    now = future_time()
    monkeypatch.setattr(
        work_stash_service,
        "list_work_stash",
        lambda **_: WorkStashListResult(
            entries=[
                WorkStashEntryMeta(
                    entry_key="key1",
                    size_bytes=100,
                    tags=[],
                    created_at=now,
                    updated_at=now,
                    expires_at=now,
                )
            ],
            total_size_bytes=100,
            quota_bytes=FREE_STASH_LIMITS.quota_bytes,
            entry_count=1,
            entry_limit=FREE_STASH_LIMITS.max_entries,
        ),
    )

    response = client.get("/api/v1/work-stash", headers={"Authorization": "Bearer sk-test"})

    assert response.status_code == 200
    assert "encrypted_value" not in response.text
    assert "ciphertext" not in response.text
