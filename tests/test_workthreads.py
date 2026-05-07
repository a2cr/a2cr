from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from main import app
from routers.dashboard import get_current_dashboard_user
from routers.web_context import get_current_api_user
from services.auth import AuthenticatedUser
from services.dashboard import DashboardProfile
from services.workthreads import WorkThread, WorkThreadMessage, WorkThreadTask, WorkThreadUpdateCheck
import services.dashboard as dashboard_service
import services.workthreads as workthreads_service


USER_ID = UUID("00000000-0000-0000-0000-0000000000a1")


@pytest.fixture
def api_client():
    app.dependency_overrides[get_current_api_user] = lambda: AuthenticatedUser(USER_ID, "api_key")
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def dashboard_client():
    app.dependency_overrides[get_current_dashboard_user] = lambda: AuthenticatedUser(USER_ID, "jwt")
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def now():
    return datetime.now(timezone.utc)


def thread_item():
    timestamp = now()
    return WorkThread(
        thread_id="11111111-1111-1111-1111-111111111111",
        title="Task 8 handoff",
        purpose="Continue work across windows",
        status="active",
        loop_status="ok",
        final_slot_name=None,
        message_count=2,
        task_count=0,
        task_status_counts={},
        agent_names=["codex"],
        last_activity_at=timestamp,
        created_at=timestamp,
        updated_at=timestamp,
    )


def profile_item(plan="pro"):
    timestamp = now()
    return DashboardProfile(
        user_id=str(USER_ID),
        plan=plan,
        context_detail_level="compact",
        default_retention_seconds=86400,
        preferred_locale="ja",
        response_language="ja",
        timezone="Asia/Tokyo",
        created_at=timestamp,
        updated_at=timestamp,
    )


def message_item(content=None, requires_response=False):
    timestamp = now()
    return WorkThreadMessage(
        message_id="22222222-2222-2222-2222-222222222222",
        thread_id="11111111-1111-1111-1111-111111111111",
        message_type="note",
        content=content or {"current_state": "schema done", "next_action": "run tests"},
        consultation_id=None,
        requires_response=requires_response,
        target_agent_name="codex" if requires_response else None,
        agent_name="claude",
        created_at=timestamp,
    )


def task_item(status="claimed", lease_owner="codex"):
    timestamp = now()
    return WorkThreadTask(
        task_id="33333333-3333-3333-3333-333333333333",
        thread_id="11111111-1111-1111-1111-111111111111",
        title="Verify WorkThreads",
        status=status,
        lease_owner=lease_owner,
        lease_expires_at=timestamp + timedelta(minutes=5) if lease_owner else None,
        result_message_id=None,
        created_at=timestamp,
        updated_at=timestamp,
    )


class FakeWorkThreadResult:
    def __init__(self, *, scalar=None, rows=None):
        self.scalar = scalar
        self.rows = rows or []

    def scalar_one_or_none(self):
        return self.scalar

    def mappings(self):
        return self

    def all(self):
        return self.rows


class FakeWorkThreadSession:
    def __init__(self):
        self.executed = []

    def execute(self, statement, params=None):
        statement_text = str(statement)
        self.executed.append((statement_text, params or {}))
        if "SELECT plan FROM public.user_profiles" in statement_text:
            return FakeWorkThreadResult(scalar="pro")
        return FakeWorkThreadResult(rows=[])


class FakeWorkThreadTransaction:
    def __init__(self, session):
        self.session = session

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc, tb):
        return False


def capture_workthread_session(monkeypatch):
    session = FakeWorkThreadSession()
    monkeypatch.setattr(workthreads_service, "web_transaction", lambda user_id: FakeWorkThreadTransaction(session))
    return session


def test_create_workthread_route_returns_metadata_only(api_client, monkeypatch):
    captured = {}

    def fake_create_workthread(**kwargs):
        captured.update(kwargs)
        return thread_item()

    monkeypatch.setattr(workthreads_service, "create_workthread", fake_create_workthread)

    response = api_client.post(
        "/api/v1/workthreads",
        json={
            "title": "Task 8 handoff",
            "purpose": "Continue work across windows",
            "initial_message": {"secret": "not returned"},
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Task 8 handoff"
    assert "initial_message" not in body
    assert "content" not in body
    assert captured["user_id"] == USER_ID


def test_api_read_workthread_returns_decrypted_messages(api_client, monkeypatch):
    monkeypatch.setattr(workthreads_service, "read_workthread", lambda **_: [message_item()])

    response = api_client.get("/api/v1/workthreads/11111111-1111-1111-1111-111111111111/messages")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["content"]["current_state"] == "schema done"


def test_dashboard_workthreads_return_metadata_without_message_content(dashboard_client, monkeypatch):
    monkeypatch.setattr(dashboard_service, "get_profile", lambda *_: profile_item(plan="pro"))
    monkeypatch.setattr(workthreads_service, "list_workthreads", lambda **_: [thread_item()])

    response = dashboard_client.get("/api/dashboard/workthreads")

    assert response.status_code == 200
    body = response.json()[0]
    assert body["message_count"] == 2
    assert "content" not in body
    assert "messages" not in body
    assert "secret" not in str(body).lower()


def test_free_dashboard_workthreads_returns_empty_without_pro_error(dashboard_client, monkeypatch):
    called = False

    def fail_if_called(**_):
        nonlocal called
        called = True
        raise AssertionError("free dashboard should not call pro-only workthreads service")

    monkeypatch.setattr(dashboard_service, "get_profile", lambda *_: profile_item(plan="free"))
    monkeypatch.setattr(workthreads_service, "list_workthreads", fail_if_called)

    response = dashboard_client.get("/api/dashboard/workthreads")

    assert response.status_code == 200
    assert response.json() == []
    assert called is False


def test_unread_and_update_routes_map_to_service(api_client, monkeypatch):
    monkeypatch.setattr(workthreads_service, "unread_workthread_messages", lambda **_: [message_item(requires_response=True)])
    monkeypatch.setattr(
        workthreads_service,
        "check_workthread_updates",
        lambda **_: WorkThreadUpdateCheck(
            thread_id="11111111-1111-1111-1111-111111111111",
            has_updates=True,
            message_count=1,
            latest_message_at=now() + timedelta(seconds=1),
        ),
    )

    unread = api_client.get(
        "/api/v1/workthreads/11111111-1111-1111-1111-111111111111/unread?target_agent_name=codex"
    )
    updates = api_client.get("/api/v1/workthreads/11111111-1111-1111-1111-111111111111/updates")

    assert unread.status_code == 200
    assert unread.json()[0]["requires_response"] is True
    assert updates.status_code == 200
    assert updates.json()["has_updates"] is True


def test_task_claim_and_complete_routes(api_client, monkeypatch):
    monkeypatch.setattr(workthreads_service, "claim_workthread_task", lambda **_: task_item())
    monkeypatch.setattr(workthreads_service, "complete_workthread_task", lambda **_: task_item(status="completed"))

    claimed = api_client.post(
        "/api/v1/workthreads/tasks/claim",
        json={"lease_owner": "codex", "thread_id": "11111111-1111-1111-1111-111111111111"},
    )
    completed = api_client.post(
        "/api/v1/workthreads/tasks/33333333-3333-3333-3333-333333333333/complete",
        json={"lease_owner": "codex"},
    )

    assert claimed.status_code == 200
    assert claimed.json()["lease_owner"] == "codex"
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"


def test_list_workthreads_applies_safe_limit(monkeypatch):
    session = capture_workthread_session(monkeypatch)

    assert workthreads_service.list_workthreads(user_id=USER_ID, limit=9999) == []

    statement, params = session.executed[1]
    assert "ORDER BY last_activity_at DESC LIMIT :limit" in " ".join(statement.split())
    assert params["limit"] == workthreads_service.MAX_LIST_WORKTHREADS


def test_unread_workthread_messages_applies_safe_limit(monkeypatch):
    session = capture_workthread_session(monkeypatch)

    assert (
        workthreads_service.unread_workthread_messages(
            user_id=USER_ID,
            thread_id="11111111-1111-1111-1111-111111111111",
            target_agent_name="codex",
            limit=9999,
        )
        == []
    )

    statement, params = session.executed[1]
    assert "LIMIT :limit" in statement
    assert params["target_agent_name"] == "codex"
    assert params["limit"] == workthreads_service.MAX_UNREAD_WORKTHREAD_MESSAGES


def test_workthreads_read_paths_do_not_use_unbounded_selects():
    service = (Path(__file__).resolve().parents[1] / "services/workthreads.py").read_text(encoding="utf-8")
    list_slice = service[service.index("def list_workthreads(") : service.index("def _insert_message(")]
    read_slice = service[service.index("def read_workthread(") : service.index("def unread_workthread_messages(")]
    unread_slice = service[service.index("def unread_workthread_messages(") : service.index("def _task_row_to_model(")]

    assert "LIMIT :limit" in list_slice
    assert "LIMIT :limit" in read_slice
    assert "LIMIT :limit" in unread_slice


def test_save_workthread_result_rejects_plaintext_without_echoing_body(api_client):
    secret_content = {
        "goal": "secret workthread goal",
        "current_state": "secret workthread state",
        "next_action": "secret workthread action",
    }

    response = api_client.post(
        "/api/v1/workthreads/11111111-1111-1111-1111-111111111111/result",
        json={"slot_name": "slot-a", "content": secret_content},
        headers={"Authorization": "Bearer sk-test-secret"},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "client_encryption_required"
    assert "secret workthread goal" not in response.text
    assert "secret workthread state" not in response.text
    assert "secret workthread action" not in response.text
    assert "sk-test-secret" not in response.text


def test_loop_guard_warning_and_dashboard_metadata(api_client, dashboard_client, monkeypatch):
    monkeypatch.setattr(
        workthreads_service,
        "post_workthread_message",
        lambda **_: WorkThreadMessage(
            **{
                **message_item(requires_response=True).__dict__,
                "loop_warning": "consultation_limit_approaching",
            }
        ),
    )
    monkeypatch.setattr(
        workthreads_service,
        "list_workthreads",
        lambda **_: [
            WorkThread(
                **{
                    **thread_item().__dict__,
                    "loop_status": "warning",
                    "task_count": 2,
                    "task_status_counts": {"pending": 1, "claimed": 1},
                }
            )
        ],
    )
    monkeypatch.setattr(dashboard_service, "get_profile", lambda *_: profile_item(plan="pro"))

    posted = api_client.post(
        "/api/v1/workthreads/11111111-1111-1111-1111-111111111111/messages",
        json={
            "content": {"question": "Need verification?"},
            "message_type": "question",
            "consultation_id": "c1",
            "requires_response": True,
        },
    )
    dashboard = dashboard_client.get("/api/dashboard/workthreads")

    assert posted.status_code == 201
    assert posted.json()["loop_warning"] == "consultation_limit_approaching"
    assert dashboard.status_code == 200
    assert dashboard.json()[0]["loop_status"] == "warning"
    assert "content" not in dashboard.json()[0]


def test_workthreads_migration_uses_skip_locked_and_separate_tables():
    migration = (Path(__file__).resolve().parents[1] / "supabase/migrations/002_workthreads.sql").read_text(
        encoding="utf-8"
    )
    uniqueness_migration = (
        Path(__file__).resolve().parents[1] / "supabase/migrations/007_workthreads_message_uniqueness.sql"
    ).read_text(encoding="utf-8")
    service = (Path(__file__).resolve().parents[1] / "services/workthreads.py").read_text(encoding="utf-8")

    assert "work_thread_messages" in migration
    assert "ENABLE ROW LEVEL SECURITY" in migration
    assert "FOR UPDATE SKIP LOCKED" in service
    assert "FOR UPDATE" in service[service.index("def _enforce_loop_guard(") : service.index("def _block_loop(")]
    assert "work_thread_messages_idempotency_unique_idx" in uniqueness_migration
    assert "work_thread_messages_content_hash_unique_idx" in uniqueness_migration
    assert "web_context_service.save_context" in service
