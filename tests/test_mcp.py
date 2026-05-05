import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from main import app
from routers import mcp_http
from services.auth import AuthError, AuthenticatedUser
from services.dashboard import DashboardProfile
from services.web_context import (
    RequestMeta,
    WebContextMetadata,
    WebLoadResult,
    WebResumeResult,
    WebSaveResult,
)
import services.dashboard as dashboard_service
import services.web_context as web_context_service


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
        content=CONTENT,
        expires_at=future_time(),
        compressed_tokens=12,
        detail_level="compact",
        model_source="gpt",
        load_count=1,
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


def test_mcp_streamable_http_lists_tools_and_calls_save(monkeypatch):
    captured = {}
    monkeypatch.setattr(mcp_http, "_current_auth_context", auth_context)

    def fake_save_context(**kwargs):
        captured.update(kwargs)
        return WebSaveResult(
            slot_name=kwargs["slot_name"],
            slot_number=1,
            expires_at=future_time(),
            compressed_tokens=10,
            saved_tokens=3,
            resume_context_call='resume_context(slot_name="slot-a")',
            resume_prompt=(
                "Use the A2CR MCP tool. Do not guess or call direct HTTP API endpoints. "
                'First run: resume_context(slot_name="slot-a")'
            ),
        )

    monkeypatch.setattr(web_context_service, "save_context", fake_save_context)
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
    assert {"save_context", "resume_context", "load_context", "list_contexts", "get_account_limits"} <= tool_names
    save_tool = next(tool for tool in tools if tool["name"] == "save_context")
    assert "do not guess" in save_tool["description"].lower()
    assert "direct HTTP API" in save_tool["description"]

    assert save_response.status_code == 200
    result = _sse_json(save_response)["result"]
    assert result["isError"] is False
    saved = json.loads(result["content"][0]["text"])
    assert saved["resume_context_call"] == 'resume_context(slot_name="slot-a")'
    assert "A2CR MCP tool" in saved["resume_prompt"]
    assert captured["meta"].client_type == "mcp"


def test_mcp_save_context_returns_resume_prompt_without_content_or_key(monkeypatch):
    captured = {}
    monkeypatch.setattr(mcp_http, "_current_auth_context", auth_context)

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
                "A2CR service: https://a2cr.example/mcp\n"
                "Use the A2CR MCP tool. Do not guess or call direct HTTP API endpoints.\n"
                'First run: resume_context(slot_name="slot-a")'
            ),
        )

    monkeypatch.setattr(web_context_service, "save_context", fake_save_context)

    result = mcp_http.save_context(
        slot_name="slot-a",
        slot_number=1,
        content=CONTENT,
        retention_seconds=86400,
        detail_level="compact",
    )

    assert result["resume_context_call"] == 'resume_context(slot_name="slot-a")'
    assert "A2CR MCP tool" in result["resume_prompt"]
    assert "direct HTTP API" in result["resume_prompt"]
    assert "ship http mcp" not in result["resume_prompt"]
    assert "sk-test-secret" not in result["resume_prompt"]
    assert captured["user_id"] == USER_ID
    assert captured["meta"].client_type == "mcp"


def test_mcp_resume_context_loads_exact_slot_number(monkeypatch):
    captured = {}
    monkeypatch.setattr(mcp_http, "_current_auth_context", auth_context)

    def fake_resume_context(**kwargs):
        captured.update(kwargs)
        return WebResumeResult(mode="loaded", context=load_result("slot-b", 2))

    monkeypatch.setattr(web_context_service, "resume_context", fake_resume_context)

    result = mcp_http.resume_context(slot_number=2)

    assert captured["slot_number"] == 2
    assert result["mode"] == "loaded"
    assert result["context"]["slot_name"] == "slot-b"
    assert result["context"]["content"]["next_action"] == "run pytest"


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
    assert len(result["candidates"]) == 2
    assert "content" not in result["candidates"][0]


def test_mcp_resume_without_selector_returns_metadata_candidates(monkeypatch):
    monkeypatch.setattr(mcp_http, "_current_auth_context", auth_context)
    monkeypatch.setattr(web_context_service, "list_contexts", lambda **_: [metadata("slot-a", 1)])

    result = mcp_http.resume_context()

    assert result["mode"] == "candidates"
    assert result["context"] is None
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
    assert result["active_slots"] == 3
    assert 86400 in result["allowed_retention_seconds"]
    assert result["max_body_bytes"] == 32 * 1024
    assert result["allowed_detail_levels"] == ["compact"]
    assert result["response_language"] == "auto"
