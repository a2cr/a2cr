from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from main import app
from routers.dashboard import get_current_dashboard_user
from routers.web_context import get_current_api_user
from services.auth import AuthenticatedUser
from services.dashboard import DashboardProfile
from services.exceptions import AppError, ContentTooLarge
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
        failure_reason="blocked by dependency" if status == "failed" else None,
        created_at=timestamp,
        updated_at=timestamp,
    )


class FakeWorkThreadResult:
    def __init__(self, *, scalar=None, rows=None):
        self.scalar = scalar
        self.rows = rows or []

    def scalar_one_or_none(self):
        return self.scalar

    def scalar_one(self):
        return self.scalar

    def mappings(self):
        return self

    def all(self):
        return self.rows

    def first(self):
        return self.rows[0] if self.rows else None

    def one(self):
        return self.rows[0]


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


class ResponseResolutionSession(FakeWorkThreadSession):
    def __init__(self, *, parent_rows=None, unresolved_count=0):
        super().__init__()
        self.parent_rows = parent_rows or []
        self.unresolved_count = unresolved_count

    def execute(self, statement, params=None):
        statement_text = str(statement)
        params = params or {}
        self.executed.append((statement_text, params))
        if "SELECT id, requires_response, resolved_at" in statement_text:
            return FakeWorkThreadResult(rows=self.parent_rows)
        if "SELECT loop_status" in statement_text:
            return FakeWorkThreadResult(scalar="ok")
        if "SELECT 1" in statement_text and "content_hash = :content_hash" in statement_text:
            return FakeWorkThreadResult(scalar=None)
        if "SELECT count(*)" in statement_text and "requires_response = true" in statement_text:
            return FakeWorkThreadResult(scalar=self.unresolved_count)
        if "INSERT INTO public.work_thread_messages" in statement_text:
            return FakeWorkThreadResult(
                rows=[
                    SimpleNamespace(
                        id=UUID("44444444-4444-4444-4444-444444444444"),
                        thread_id=params["thread_id"],
                        message_type=params["message_type"],
                        content=params["content"],
                        consultation_id=params["consultation_id"],
                        requires_response=params["requires_response"],
                        target_agent_name=params["target_agent_name"],
                        agent_name=params["agent_name"],
                        created_at=now(),
                        resolved_at=None,
                        resolved_by_message_id=None,
                    )
                ]
            )
        return FakeWorkThreadResult(rows=[])


class TaskMutationSession(FakeWorkThreadSession):
    def execute(self, statement, params=None):
        statement_text = str(statement)
        params = params or {}
        self.executed.append((statement_text, params))
        if "SELECT plan FROM public.user_profiles" in statement_text:
            return FakeWorkThreadResult(scalar="pro")
        if "UPDATE public.work_thread_tasks" in statement_text:
            return FakeWorkThreadResult(
                rows=[
                    SimpleNamespace(
                        id=UUID(params["task_id"]),
                        thread_id=UUID("11111111-1111-1111-1111-111111111111"),
                        title="Verify WorkThreads",
                        status="failed",
                        lease_owner=params["lease_owner"],
                        lease_expires_at=now() + timedelta(minutes=5),
                        result_message_id=(
                            UUID(params["result_message_id"]) if params.get("result_message_id") else None
                        ),
                        failure_reason=params["failure_reason"],
                        created_at=now(),
                        updated_at=now(),
                    )
                ]
            )
        return FakeWorkThreadResult(rows=[])


def patch_workthread_crypto(monkeypatch):
    monkeypatch.setattr(workthreads_service, "encrypt", lambda value, _key: value)
    monkeypatch.setattr(workthreads_service, "get_web_config", lambda: SimpleNamespace(fernet_key="test-key"))


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
    assert body[0]["resolved_at"] is None
    assert body[0]["resolved_by_message_id"] is None


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


def test_response_message_resolves_unresolved_parent(monkeypatch):
    patch_workthread_crypto(monkeypatch)
    parent_message_id = "22222222-2222-2222-2222-222222222222"
    session = ResponseResolutionSession(
        parent_rows=[SimpleNamespace(id=UUID(parent_message_id), requires_response=True, resolved_at=None)],
        unresolved_count=3,
    )

    row, warning = workthreads_service._insert_message(
        session,
        user_id=USER_ID,
        thread_id="11111111-1111-1111-1111-111111111111",
        content_dict={"answer": "Done"},
        message_type="answer",
        parent_message_id=parent_message_id,
        agent_name="codex",
    )

    unresolved_statement, unresolved_params = next(
        item
        for item in session.executed
        if "SELECT count(*)" in item[0] and "requires_response = true" in item[0]
    )
    _resolution_statement, resolution_params = next(
        item for item in session.executed if "SET resolved_at = now()" in item[0]
    )
    assert row.id == UUID("44444444-4444-4444-4444-444444444444")
    assert warning is None
    assert "resolved_at IS NULL" in unresolved_statement
    assert "id <> CAST(:resolved_parent_message_id AS uuid)" in unresolved_statement
    assert unresolved_params["resolved_parent_message_id"] == parent_message_id
    assert resolution_params["parent_message_id"] == parent_message_id
    assert resolution_params["resolved_by_message_id"] == str(row.id)


def test_parent_message_id_must_belong_to_same_thread(monkeypatch):
    patch_workthread_crypto(monkeypatch)
    session = ResponseResolutionSession(parent_rows=[])

    with pytest.raises(AppError) as exc:
        workthreads_service._insert_message(
            session,
            user_id=USER_ID,
            thread_id="11111111-1111-1111-1111-111111111111",
            content_dict={"answer": "Wrong thread"},
            message_type="answer",
            parent_message_id="22222222-2222-2222-2222-222222222222",
            agent_name="codex",
        )

    assert exc.value.code == "invalid_parent_message_id"
    assert exc.value.status == 400
    assert not any("INSERT INTO public.work_thread_messages" in statement for statement, _ in session.executed)


def test_workthread_message_rejects_oversized_content_before_db():
    session = ResponseResolutionSession()

    with pytest.raises(ContentTooLarge):
        workthreads_service._insert_message(
            session,
            user_id=USER_ID,
            thread_id="11111111-1111-1111-1111-111111111111",
            content_dict={"body": "x" * workthreads_service.MAX_WORKTHREAD_MESSAGE_CONTENT_BYTES},
            message_type="note",
            agent_name="codex",
        )

    assert session.executed == []


def test_fail_workthread_task_uses_active_lease_and_compact_reason(monkeypatch):
    session = TaskMutationSession()
    monkeypatch.setattr(workthreads_service, "web_transaction", lambda user_id: FakeWorkThreadTransaction(session))

    task = workthreads_service.fail_workthread_task(
        user_id=USER_ID,
        task_id="33333333-3333-3333-3333-333333333333",
        lease_owner="codex",
        reason="  blocked by dependency  ",
        result_message_id="44444444-4444-4444-4444-444444444444",
    )

    statement, params = next(item for item in session.executed if "UPDATE public.work_thread_tasks" in item[0])
    assert "SET status = 'failed'" in statement
    assert "failure_reason = :failure_reason" in statement
    assert "AND status = 'claimed'" in statement
    assert "AND lease_owner = :lease_owner" in statement
    assert "AND lease_expires_at > now()" in statement
    assert params["failure_reason"] == "blocked by dependency"
    assert task.status == "failed"
    assert task.failure_reason == "blocked by dependency"
    assert task.result_message_id == "44444444-4444-4444-4444-444444444444"


def test_fail_workthread_task_rejects_blank_reason_before_db(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("blank task failure reason should not open a transaction")

    monkeypatch.setattr(workthreads_service, "web_transaction", fail_if_called)

    with pytest.raises(AppError) as exc:
        workthreads_service.fail_workthread_task(
            user_id=USER_ID,
            task_id="33333333-3333-3333-3333-333333333333",
            lease_owner="codex",
            reason=" ",
        )

    assert exc.value.code == "invalid_task_failure_reason"
    assert exc.value.status == 400


def test_task_claim_complete_and_fail_routes(api_client, monkeypatch):
    monkeypatch.setattr(workthreads_service, "claim_workthread_task", lambda **_: task_item())
    monkeypatch.setattr(workthreads_service, "complete_workthread_task", lambda **_: task_item(status="completed"))
    monkeypatch.setattr(workthreads_service, "fail_workthread_task", lambda **_: task_item(status="failed"))

    claimed = api_client.post(
        "/api/v1/workthreads/tasks/claim",
        json={"lease_owner": "codex", "thread_id": "11111111-1111-1111-1111-111111111111"},
    )
    completed = api_client.post(
        "/api/v1/workthreads/tasks/33333333-3333-3333-3333-333333333333/complete",
        json={"lease_owner": "codex"},
    )
    failed = api_client.post(
        "/api/v1/workthreads/tasks/33333333-3333-3333-3333-333333333333/fail",
        json={"lease_owner": "codex", "reason": "blocked by dependency"},
    )

    assert claimed.status_code == 200
    assert claimed.json()["lease_owner"] == "codex"
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert failed.status_code == 200
    assert failed.json()["status"] == "failed"
    assert failed.json()["failure_reason"] == "blocked by dependency"


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
    assert "resolved_at IS NULL" in statement
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


def test_service_save_workthread_result_is_disabled_before_db(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("disabled WorkThread result save must not open a transaction")

    monkeypatch.setattr(workthreads_service, "web_transaction", fail_if_called)

    with pytest.raises(AppError) as exc:
        workthreads_service.save_workthread_result(
            user_id=USER_ID,
            thread_id="11111111-1111-1111-1111-111111111111",
            slot_name="slot-a",
            content_dict={
                "goal": "secret workthread goal",
                "current_state": "secret workthread state",
                "next_action": "secret workthread action",
            },
        )

    assert exc.value.code == "client_encryption_required"
    assert "local stdio" in exc.value.message
    assert "secret workthread goal" not in exc.value.message
    assert "secret workthread state" not in exc.value.message
    assert "secret workthread action" not in exc.value.message


def test_save_workthread_result_rejects_plaintext_without_echoing_body(api_client, monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("disabled route should not call WorkThread result service")

    monkeypatch.setattr(workthreads_service, "save_workthread_result", fail_if_called)
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
    resolution_migration = (
        Path(__file__).resolve().parents[1] / "supabase/migrations/009_workthreads_response_resolution.sql"
    ).read_text(encoding="utf-8")
    task_failure_migration = (
        Path(__file__).resolve().parents[1] / "supabase/migrations/010_workthreads_task_failure_reason.sql"
    ).read_text(encoding="utf-8")
    service = (Path(__file__).resolve().parents[1] / "services/workthreads.py").read_text(encoding="utf-8")

    assert "work_thread_messages" in migration
    assert "ENABLE ROW LEVEL SECURITY" in migration
    assert "FOR UPDATE SKIP LOCKED" in service
    assert "FOR UPDATE" in service[service.index("def _enforce_loop_guard(") : service.index("def _block_loop(")]
    assert "work_thread_messages_idempotency_unique_idx" in uniqueness_migration
    assert "work_thread_messages_content_hash_unique_idx" in uniqueness_migration
    assert "resolved_at" in resolution_migration
    assert "resolved_by_message_id" in resolution_migration
    assert "work_thread_messages_pending_response_idx" in resolution_migration
    assert "failure_reason" in task_failure_migration
    assert "work_thread_tasks_failure_reason_length" in task_failure_migration
    final_result_slice = service[service.index("def save_workthread_result(") : service.index("def check_workthread_updates(")]
    assert "client_encryption_required" in final_result_slice
    assert "web_context_service.save_context" not in final_result_slice


def test_workthreads_docs_require_local_thread_key_encryption():
    runbook = (Path(__file__).resolve().parents[1] / "docs/runbooks/workthreads.md").read_text(encoding="utf-8")
    plan = (Path(__file__).resolve().parents[1] / "docs/runbooks/workthreads-mvp-plan.md").read_text(
        encoding="utf-8"
    )
    flow = (Path(__file__).resolve().parents[1] / "docs/runbooks/mcp-baton-vs-threads-flow.md").read_text(
        encoding="utf-8"
    )

    assert "thread-scoped shared key" in runbook
    assert "A2CR cannot decrypt WorkThread message bodies without the thread key" in runbook
    assert "pre-beta implementation gap" in runbook
    assert "thread-scoped key shared only with participating agent windows" in plan
    assert "ciphertext envelopes only" in flow
