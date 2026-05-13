import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from main import app
from models.schemas import ContentSchema
from routers import mcp_http
from services.auth import AuthError, AuthenticatedUser
from services.exceptions import AppError
from services.dashboard import DashboardProfile
from services.web_context import (
    RequestMeta,
    WebContextMetadata,
    WebLoadResult,
    WebResumeResult,
)
import services.dashboard as dashboard_service
import services.web_context as web_context_service
import services.workthreads as workthreads_service


USER_ID = UUID("00000000-0000-0000-0000-0000000000a1")
CONTENT = {
    "goal": "ship http mcp",
    "current_state": "testing tool mapping",
    "next_action": "run pytest",
}


def future_time():
    return datetime.now(timezone.utc) + timedelta(hours=1)


def auth_context():
    return AuthenticatedUser(USER_ID, "api_key"), RequestMeta(client_type="mcp", request_id="req-1")


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
        encrypted_content={
            "version": 1,
            "alg": "Fernet",
            "nonce": "embedded",
            "ciphertext": slot_name,
        },
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


def _sse_json(response):
    for line in response.text.splitlines():
        if line.startswith("data: "):
            return json.loads(line.removeprefix("data: "))
    raise AssertionError("SSE response did not contain a data line")


def test_mcp_streamable_http_lists_tools_and_rejects_remote_save(monkeypatch):
    monkeypatch.setattr(mcp_http, "_current_auth_context", auth_context)
    headers = {"content-type": "application/json", "accept": "application/json, text/event-stream"}

    with TestClient(app) as client:
        response = client.post(
            "/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "pytest", "version": "0.1"},
                },
            },
        )
        session_id = response.headers["mcp-session-id"]
        session_headers = {**headers, "mcp-session-id": session_id, "authorization": "Bearer sk-test"}
        client.post(
            "/mcp",
            headers=session_headers,
            json={"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        )
        tools_response = client.post(
            "/mcp",
            headers=session_headers,
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )
        save_response = client.post(
            "/mcp",
            headers=session_headers,
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "save_context",
                    "arguments": {
                        "slot_name": "slot-a",
                        "content": CONTENT,
                        "retention_seconds": 86400,
                    },
                },
            },
        )

    assert response.status_code == 200
    assert tools_response.status_code == 200
    tools = _sse_json(tools_response)["result"]["tools"]
    tool_names = {tool["name"] for tool in tools}
    assert {
        "explain_a2cr_flows",
        "should_save_workbaton",
        "save_context",
        "resume_context",
        "load_context",
        "list_contexts",
        "get_account_limits",
    } <= tool_names
    explain_tool = next(tool for tool in tools if tool["name"] == "explain_a2cr_flows")
    assert "WorkBaton serial handoff" in explain_tool["description"]
    assert "WorkThreads multi-agent collaboration" in explain_tool["description"]
    save_tool = next(tool for tool in tools if tool["name"] == "save_context")
    assert "client-side encryption" in save_tool["description"]
    assert "local stdio" in save_tool["description"]
    assert "tools lazily" in save_tool["description"]
    resume_tool = next(tool for tool in tools if tool["name"] == "resume_context")
    load_tool = next(tool for tool in tools if tool["name"] == "load_context")
    assert "agent_continuity_guidance" in resume_tool["description"]
    assert "agent_continuity_guidance" in load_tool["description"]
    advice_tool = next(tool for tool in tools if tool["name"] == "should_save_workbaton")
    assert "required local stdio save path" in advice_tool["description"]
    check_tool = next(tool for tool in tools if tool["name"] == "check_workthread_updates")
    wait_tool = next(tool for tool in tools if tool["name"] == "wait_workthread_updates")
    pending_tool = next(tool for tool in tools if tool["name"] == "pending_workthread_responses")
    unread_tool = next(tool for tool in tools if tool["name"] == "unread_workthread")
    fail_task_tool = next(tool for tool in tools if tool["name"] == "fail_workthread_task")
    assert check_tool["description"].startswith("Non-blocking check")
    assert wait_tool["description"].startswith("Blocking wait")
    assert check_tool["description"] != wait_tool["description"]
    assert "not true unread state" in pending_tool["description"]
    assert "Deprecated alias" in unread_tool["description"]
    assert "lease_owner must match" in fail_task_tool["description"]
    result_tool = next(tool for tool in tools if tool["name"] == "save_workthread_result")
    assert "Disabled" in result_tool["description"]
    assert "local stdio encryption flow" in result_tool["description"]

    assert save_response.status_code == 200
    result = _sse_json(save_response)["result"]
    assert result["isError"] is True
    assert "Error calling tool" in result["content"][0]["text"]


def test_mcp_explain_a2cr_flows_documents_baton_threads_and_encryption():
    result = mcp_http.explain_a2cr_flows()

    assert mcp_http.web_mcp.instructions == mcp_http.INSTRUCTIONS
    assert "Primary WorkBaton save tool name: save_context" in mcp_http.INSTRUCTIONS
    assert "tools lazily" in mcp_http.INSTRUCTIONS
    assert result["common_rule"]["mcp_first"].startswith("AI agents use A2CR MCP tools")
    assert "newly connected AI" in result["common_rule"]["new_agent_bootstrap"]
    assert result["common_rule"]["agent_continuity_guidance"]["use_proactively"] is True
    assert "tools lazily" in result["common_rule"]["deferred_tool_clients"]
    assert result["common_rule"]["deferred_tool_search_phrase"] == "save_context"
    assert result["common_rule"]["decision_table"]["WorkStash"].startswith("Use for safe supporting notes")
    assert result["workbaton"]["flow"] == "window -> WorkBaton -> new window"
    assert "should_save_workbaton" in result["workbaton"]["tools"]
    assert result["workbaton"]["stdio_wrapper_required_for_save"] is True
    assert "local stdio wrapper" in result["workbaton"]["how_to_check_stdio_wrapper"]
    assert "exact-search for save_context" in result["workbaton"]["how_to_check_stdio_wrapper"]
    assert "Remote MCP save_context is disabled" in result["workbaton"]["save_path"]
    assert "Client-encrypted before upload" in result["workbaton"]["encryption"]
    assert result["workbaton"]["storage"] == "public.contexts"
    assert "confirmed file paths" in result["workstash"]["good_examples"]
    assert "git diffs" in result["workstash"]["bad_examples"]
    assert result["workthreads"]["flow"] == "agent <-> WorkThread <-> agents"
    assert "remote MCP surface" in result["workthreads"]["availability"]
    assert "pending_workthread_responses" in result["workthreads"]["tools"]
    assert "fail_workthread_task" in result["workthreads"]["tools"]
    assert "encrypted locally with a thread key" in result["workthreads"]["encryption"]
    assert "only agents with the WorkThread key" in result["workthreads"]["encryption"]
    assert any("Do not send WorkThread keys to A2CR" in item for item in result["workthreads"]["must_not"])
    assert "Do not silently create or overwrite WorkBaton Slots." in result["workthreads"]["must_not"]
    assert "save_context through the local stdio wrapper" in result["finalization"]["allowed"]


def test_mcp_should_save_workbaton_advises_remote_stdio_path():
    result = mcp_http.should_save_workbaton(
        reason="conversation_getting_long",
        project="A2CR",
        recent_progress="WorkBaton autonomous save spec was reviewed",
        next_action="Patch the MCP self-description",
        context_pressure="medium",
    )

    assert result["should_save"] is True
    assert result["can_save_here"] is False
    assert result["required_save_path"] == "local stdio A2CR MCP wrapper"
    assert result["call_get_account_limits_first"] is True
    assert result["recommended_slot_name"] == "a2cr-main"
    assert "tools lazily" in result["tool_visibility_note"]
    assert result["deferred_tool_search_phrase"] == "save_context"
    assert result["save_readiness"]["save_with"] == "local stdio save_context"
    assert "remote MCP surface cannot save WorkBaton" in result["next_step"]
    assert "blockers" in result["optional_fields"]
    assert "confirmed file paths" in result["workstash_guidance"]["good_examples"]
    assert result["agent_continuity_guidance"]["use_proactively"] is True
    assert result["fresh_window_guidance"]["should_suggest"] is False


def test_mcp_should_save_workbaton_flags_context_freshness():
    result = mcp_http.should_save_workbaton(
        reason="context_contamination",
        recent_progress="Several unrelated decisions are mixed into the active context",
        next_action="Save a compact checkpoint and continue in a clean window",
    )

    assert result["should_save"] is True
    assert result["fresh_window_guidance"]["should_suggest"] is True
    assert "fresh AI window" in result["fresh_window_guidance"]["reason"]


def test_mcp_should_save_workbaton_blocks_unclear_or_prohibited_saves():
    missing_next_action = mcp_http.should_save_workbaton(
        reason="conversation_getting_long",
        recent_progress="Drafted a spec",
    )
    prohibited = mcp_http.should_save_workbaton(
        reason="conversation_getting_long",
        recent_progress="Drafted a spec",
        next_action="Continue implementation",
        has_prohibited_material=True,
    )

    assert missing_next_action["should_save"] is False
    assert "next_action is clear" in missing_next_action["warnings"][0]
    assert prohibited["should_save"] is False
    assert "prohibited material" in prohibited["warnings"][0]


def test_workbaton_content_schema_accepts_documented_blockers():
    content = ContentSchema(
        goal="align schema",
        current_state="spec mentions blockers",
        next_action="store blockers",
        blockers=["Claude review issue 2"],
    )

    assert content.blockers == ["Claude review issue 2"]


def test_mcp_save_context_requires_local_stdio_wrapper(monkeypatch):
    monkeypatch.setattr(mcp_http, "_current_auth_context", auth_context)

    with pytest.raises(AppError) as exc:
        mcp_http.save_context(
            slot_name="slot-a",
            slot_number=1,
            content=CONTENT,
            model_source="codex",
            retention_seconds=86400,
        )

    assert exc.value.code == "client_encryption_required"
    assert "local stdio" in exc.value.message


def test_mcp_save_context_gate_runs_before_auth_or_service(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("disabled remote save must not reach auth or service")

    monkeypatch.setattr(mcp_http, "_current_auth_context", fail_if_called)
    monkeypatch.setattr(web_context_service, "save_context", fail_if_called)

    with pytest.raises(AppError) as exc:
        mcp_http.save_context(
            slot_name="slot-a",
            slot_number=1,
            content={"goal": "secret goal", "current_state": "secret state", "next_action": "secret action"},
            model_source="codex",
            retention_seconds=86400,
        )

    assert exc.value.code == "client_encryption_required"
    assert "secret goal" not in exc.value.message
    assert "secret state" not in exc.value.message
    assert "secret action" not in exc.value.message


def test_mcp_save_workthread_result_requires_local_stdio_wrapper(monkeypatch):
    monkeypatch.setattr(mcp_http, "_current_auth_context", auth_context)
    secret_content = {
        "goal": "secret workthread goal",
        "current_state": "secret workthread state",
        "next_action": "secret workthread action",
    }

    with pytest.raises(AppError) as exc:
        mcp_http.save_workthread_result(
            thread_id="11111111-1111-1111-1111-111111111111",
            slot_name="slot-a",
            content=secret_content,
            retention_seconds=86400,
        )

    assert exc.value.code == "client_encryption_required"
    assert "local stdio" in exc.value.message
    assert "secret workthread goal" not in exc.value.message
    assert "secret workthread state" not in exc.value.message
    assert "secret workthread action" not in exc.value.message


def test_mcp_save_workthread_result_gate_runs_before_auth_or_service(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("disabled WorkThread result save must not reach auth or service")

    monkeypatch.setattr(mcp_http, "_current_auth_context", fail_if_called)
    monkeypatch.setattr(workthreads_service, "save_workthread_result", fail_if_called)

    with pytest.raises(AppError) as exc:
        mcp_http.save_workthread_result(
            thread_id="11111111-1111-1111-1111-111111111111",
            slot_name="slot-a",
            content={
                "goal": "secret workthread goal",
                "current_state": "secret workthread state",
                "next_action": "secret workthread action",
            },
            retention_seconds=86400,
        )

    assert exc.value.code == "client_encryption_required"
    assert "secret workthread goal" not in exc.value.message
    assert "secret workthread state" not in exc.value.message
    assert "secret workthread action" not in exc.value.message


def test_mcp_resume_context_loads_exact_slot_number(monkeypatch):
    captured = {}
    monkeypatch.setattr(mcp_http, "_current_auth_context", auth_context)

    def fake_resume_context(**kwargs):
        captured.update(kwargs)
        return WebResumeResult(mode="loaded", context=load_result("slot-b", 2))

    monkeypatch.setattr(web_context_service, "resume_context", fake_resume_context)

    result = mcp_http.resume_context(slot_number=2)

    assert captured["user_id"] == USER_ID
    assert captured["slot_number"] == 2
    assert result["mode"] == "loaded"
    assert result["context"]["slot_name"] == "slot-b"
    assert result["context"]["content"] is None
    assert result["context"]["encrypted_content"]["ciphertext"] == "slot-b"
    assert result["agent_continuity_guidance"]["use_proactively"] is True
    assert result["context"]["agent_continuity_guidance"]["use_proactively"] is True


def test_mcp_ambiguous_resume_returns_candidates_without_content(monkeypatch):
    monkeypatch.setattr(mcp_http, "_current_auth_context", auth_context)
    monkeypatch.setattr(
        web_context_service,
        "resume_context",
        lambda **_: WebResumeResult(
            mode="candidates",
            candidates=[metadata("proj-a", 1), metadata("proj-b", 2)],
        ),
    )

    result = mcp_http.resume_context(project="proj")

    assert result["mode"] == "candidates"
    assert result["context"] is None
    assert result["agent_continuity_guidance"]["use_proactively"] is True
    assert len(result["candidates"]) == 2
    assert "content" not in result["candidates"][0]


def test_mcp_resume_without_selector_returns_metadata_candidates(monkeypatch):
    monkeypatch.setattr(mcp_http, "_current_auth_context", auth_context)
    captured = {}

    def fake_list_contexts(**kwargs):
        captured.update(kwargs)
        return [metadata("slot-a", 1)]

    monkeypatch.setattr(web_context_service, "list_contexts", fake_list_contexts)

    result = mcp_http.resume_context()

    assert captured["user_id"] == USER_ID
    assert result["mode"] == "candidates"
    assert result["context"] is None
    assert result["agent_continuity_guidance"]["use_proactively"] is True
    assert result["candidates"][0]["slot_name"] == "slot-a"
    assert "content" not in result["candidates"][0]


def test_mcp_load_auth_failure_does_not_lookup_or_leak_slot(monkeypatch):
    def fail_auth():
        raise AuthError()

    def fail_if_called(**kwargs):
        raise AssertionError("slot lookup should not run before auth")

    monkeypatch.setattr(mcp_http, "_current_auth_context", fail_auth)
    monkeypatch.setattr(web_context_service, "load_context", fail_if_called)

    with pytest.raises(AuthError) as exc:
        mcp_http.load_context(slot_name="private-slot")

    assert "private-slot" not in str(exc.value)


def test_mcp_get_account_limits_returns_plan_settings(monkeypatch):
    monkeypatch.setattr(mcp_http, "_current_auth_context", auth_context)
    monkeypatch.setattr(dashboard_service, "get_profile", lambda user_id: profile())

    result = mcp_http.get_account_limits()

    assert result["plan"] == "free"
    assert result["active_slots"] == 5
    assert 86400 in result["allowed_retention_seconds"]
    assert result["max_body_bytes"] == 24 * 1024
    assert result["workstash_quota_bytes"] == 256 * 1024
    assert result["saves_per_hour"] == 100
    assert result["loads_per_hour"] == 200
    assert result["workstash_writes_per_hour"] == 200
    assert result["workstash_reads_per_hour"] == 300
    assert result["handoff_policy"]["basis"] == "size_budget"
    assert result["response_language"] == "auto"


def test_pending_workthread_responses_and_unread_alias_return_same_items(monkeypatch):
    monkeypatch.setattr(mcp_http, "_current_auth_context", auth_context)
    calls = []
    timestamp = future_time()
    pending_message = SimpleNamespace(
        message_id="22222222-2222-2222-2222-222222222222",
        thread_id="11111111-1111-1111-1111-111111111111",
        message_type="question",
        content={"question": "Need review?"},
        consultation_id="c1",
        requires_response=True,
        target_agent_name="codex",
        agent_name="claude",
        created_at=timestamp,
        resolved_at=None,
        resolved_by_message_id=None,
        loop_warning=None,
    )

    def fake_unread_workthread_messages(**kwargs):
        calls.append(kwargs)
        return [pending_message]

    monkeypatch.setattr(workthreads_service, "unread_workthread_messages", fake_unread_workthread_messages)

    pending = mcp_http.pending_workthread_responses(
        thread_id="11111111-1111-1111-1111-111111111111",
        target_agent_name="codex",
    )
    unread = mcp_http.unread_workthread(
        thread_id="11111111-1111-1111-1111-111111111111",
        target_agent_name="codex",
    )

    assert pending == unread
    assert pending[0]["message_id"] == "22222222-2222-2222-2222-222222222222"
    assert pending[0]["requires_response"] is True
    assert calls == [
        {
            "user_id": USER_ID,
            "thread_id": "11111111-1111-1111-1111-111111111111",
            "target_agent_name": "codex",
        },
        {
            "user_id": USER_ID,
            "thread_id": "11111111-1111-1111-1111-111111111111",
            "target_agent_name": "codex",
        },
    ]


def test_mcp_fail_workthread_task_maps_to_service(monkeypatch):
    monkeypatch.setattr(mcp_http, "_current_auth_context", auth_context)
    captured = {}
    timestamp = future_time()

    def fake_fail_workthread_task(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            task_id=kwargs["task_id"],
            thread_id="11111111-1111-1111-1111-111111111111",
            title="Verify WorkThreads",
            status="failed",
            lease_owner=kwargs["lease_owner"],
            lease_expires_at=timestamp,
            result_message_id=kwargs["result_message_id"],
            failure_reason=kwargs["reason"],
            created_at=timestamp,
            updated_at=timestamp,
        )

    monkeypatch.setattr(workthreads_service, "fail_workthread_task", fake_fail_workthread_task)

    result = mcp_http.fail_workthread_task(
        task_id="33333333-3333-3333-3333-333333333333",
        lease_owner="codex",
        reason="blocked by dependency",
        result_message_id="44444444-4444-4444-4444-444444444444",
    )

    assert captured == {
        "user_id": USER_ID,
        "task_id": "33333333-3333-3333-3333-333333333333",
        "lease_owner": "codex",
        "reason": "blocked by dependency",
        "result_message_id": "44444444-4444-4444-4444-444444444444",
    }
    assert result["status"] == "failed"
    assert result["failure_reason"] == "blocked by dependency"
