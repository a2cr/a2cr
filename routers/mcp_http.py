from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from models.schemas import WebContextSaveRequest
from services.abuse_limits import (
    enforce_authenticated_rate_limit,
    ensure_auth_attempt_allowed,
    record_auth_failure,
)
from services.auth import AuthError, AuthenticatedUser, authenticate_api_key
from services.db import get_web_engine
from services.exceptions import AppError, SlotNotFound
from services.limits import get_plan_limits
from services.logs import hash_log_value
from services.web_context import (
    RequestMeta,
    WebContextMetadata,
    WebLoadResult,
    WebResumeResult,
    WebSaveResult,
)
import services.dashboard as dashboard_service
import services.web_context as web_context_service
import services.workthreads as workthreads_service


_PROJECT_ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def _without_project_root_on_path():
    original = list(sys.path)
    sys.path[:] = [
        entry
        for entry in sys.path
        if Path(entry or os.getcwd()).resolve() != _PROJECT_ROOT
    ]
    try:
        yield
    finally:
        sys.path[:] = original


with _without_project_root_on_path():
    from fastmcp import FastMCP
    from fastmcp.server.dependencies import get_http_request


INSTRUCTIONS = (
    "A2CR is the MCP surface for WorkBaton checkpoints. "
    "Use the local stdio MCP wrapper for WorkBaton saves so content is encrypted before upload. "
    "This remote MCP surface can list metadata, load ciphertext, check account limits, and work with WorkThreads. "
    "Do not guess or call direct HTTP API endpoints. "
    "Never save secrets, API keys, Authorization headers, private database URLs, "
    "full transcripts, long logs, generated caches, or large code bodies that can be read from the repository."
)

SAVE_CONTEXT_DESCRIPTION = (
    "Direct remote MCP saving is disabled because WorkBaton requires client-side encryption. "
    "Use the local stdio A2CR MCP wrapper so the WorkBaton body is encrypted before it reaches A2CR. "
    "Do not guess or call direct HTTP API endpoints."
)

RESUME_CONTEXT_DESCRIPTION = (
    "Resume a WorkBaton checkpoint in a fresh AI window. Prefer slot_name when a resume prompt provides it. "
    "slot_number is an optional compatibility path. If project search is ambiguous, candidates are returned "
    "without saved content. This remote MCP surface cannot decrypt WorkBaton bodies; use the local stdio wrapper for decrypted resumes."
)

LOAD_CONTEXT_DESCRIPTION = (
    "Load a known WorkBaton checkpoint by slot_name or slot_number. The remote MCP surface returns encrypted_content only; "
    "use the local stdio wrapper when the AI needs decrypted WorkBaton content. Do not guess direct HTTP API endpoints."
)

LIST_CONTEXTS_DESCRIPTION = (
    "List active WorkBaton checkpoint metadata only. This never returns saved content bodies."
    " Use this MCP tool; do not guess direct HTTP API endpoints."
)

GET_LIMITS_DESCRIPTION = (
    "Return the current account plan, retention choices, body limits, detail level, language, timezone, "
    "and hourly save/load limits. Use this before automatic saves so the checkpoint matches the user's plan."
    " Use this MCP tool; do not guess direct HTTP API endpoints."
)

CREATE_WORKTHREAD_DESCRIPTION = (
    "Create a durable WorkThread for cross-window or cross-agent handoff. "
    "WorkThreads are Pro-only and store encrypted append-only work notes. "
    "Use this MCP tool; do not guess direct HTTP API endpoints."
)

POST_WORKTHREAD_MESSAGE_DESCRIPTION = (
    "Append a message to an existing WorkThread. Messages are append-only and encrypted at rest. "
    "Use idempotency_key to avoid accidental duplicate posts. Use this MCP tool; do not guess direct HTTP API endpoints."
)

READ_WORKTHREAD_DESCRIPTION = (
    "Read decrypted WorkThread messages for the authenticated API/MCP agent. "
    "Dashboard routes expose only metadata, not message content. Use this MCP tool; do not guess direct HTTP API endpoints."
)

WORKTHREAD_UNREAD_DESCRIPTION = (
    "Return WorkThread messages that require a response, optionally filtered by target_agent_name. "
    "Use this MCP tool; do not guess direct HTTP API endpoints."
)

WORKTHREAD_UPDATES_DESCRIPTION = (
    "Check or wait for WorkThread updates since an optional timestamp. "
    "Use this MCP tool; do not guess direct HTTP API endpoints."
)


web_mcp = FastMCP("A2CR", instructions=INSTRUCTIONS)


def create_mcp_http_app():
    return web_mcp.http_app(path="/")


class ReusableMCPApp:
    def __init__(self):
        self._app = create_mcp_http_app()

    async def __call__(self, scope, receive, send):
        await self._app(scope, receive, send)

    @asynccontextmanager
    async def lifespan(self):
        self._app = create_mcp_http_app()
        async with self._app.router.lifespan_context(self._app):
            yield


def _iso(value: datetime) -> str:
    return value.isoformat()


def _request_ip(request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else None


def _current_auth_context() -> tuple[AuthenticatedUser, RequestMeta]:
    try:
        request = get_http_request()
    except RuntimeError as exc:
        raise AuthError() from exc

    ip = _request_ip(request)
    ip_hash = hash_log_value(ip)
    ensure_auth_attempt_allowed("mcp.api_key", ip_hash)
    try:
        with Session(get_web_engine()) as session:
            user = authenticate_api_key(
                session,
                request.headers.get("authorization"),
                ip_hash=ip_hash,
            )
    except AuthError:
        record_auth_failure("mcp.api_key", ip_hash)
        raise
    return user, RequestMeta(
        client_type="mcp",
        request_id=request.headers.get("x-request-id"),
        ip=ip,
        user_agent=request.headers.get("user-agent"),
    )


def _save_result(result: WebSaveResult) -> dict[str, Any]:
    return {
        "slot_name": result.slot_name,
        "slot_number": result.slot_number,
        "expires_at": _iso(result.expires_at),
        "compressed_tokens": result.compressed_tokens,
        "saved_tokens": result.saved_tokens,
        "resume_context_call": result.resume_context_call,
        "resume_prompt": result.resume_prompt,
    }


def _metadata_result(result: WebContextMetadata) -> dict[str, Any]:
    return {
        "slot_name": result.slot_name,
        "slot_number": result.slot_number,
        "expires_at": _iso(result.expires_at),
        "updated_at": _iso(result.updated_at),
        "size_bytes": result.size_bytes,
        "compressed_tokens": result.compressed_tokens,
        "detail_level": result.detail_level,
        "model_source": result.model_source,
        "load_count": result.load_count,
        "encryption_mode": result.encryption_mode,
    }


def _load_result(result: WebLoadResult) -> dict[str, Any]:
    return {
        "slot_name": result.slot_name,
        "slot_number": result.slot_number,
        "encryption_mode": result.encryption_mode,
        "content": result.content,
        "encrypted_content": result.encrypted_content,
        "expires_at": _iso(result.expires_at),
        "compressed_tokens": result.compressed_tokens,
        "detail_level": result.detail_level,
        "model_source": result.model_source,
        "load_count": result.load_count,
    }


def _resume_result(result: WebResumeResult) -> dict[str, Any]:
    return {
        "mode": result.mode,
        "context": _load_result(result.context) if result.context else None,
        "candidates": [_metadata_result(item) for item in (result.candidates or [])],
    }


def _workthread_result(result) -> dict[str, Any]:
    return {
        "thread_id": result.thread_id,
        "title": result.title,
        "purpose": result.purpose,
        "status": result.status,
        "loop_status": result.loop_status,
        "final_slot_name": result.final_slot_name,
        "message_count": result.message_count,
        "task_count": result.task_count,
        "task_status_counts": result.task_status_counts,
        "agent_names": result.agent_names,
        "last_activity_at": _iso(result.last_activity_at),
        "created_at": _iso(result.created_at),
        "updated_at": _iso(result.updated_at),
    }


def _workthread_message_result(result) -> dict[str, Any]:
    return {
        "message_id": result.message_id,
        "thread_id": result.thread_id,
        "message_type": result.message_type,
        "content": result.content,
        "consultation_id": result.consultation_id,
        "requires_response": result.requires_response,
        "target_agent_name": result.target_agent_name,
        "agent_name": result.agent_name,
        "created_at": _iso(result.created_at),
        "loop_warning": result.loop_warning,
    }


def _workthread_update_result(result) -> dict[str, Any]:
    return {
        "thread_id": result.thread_id,
        "has_updates": result.has_updates,
        "message_count": result.message_count,
        "latest_message_at": _iso(result.latest_message_at) if result.latest_message_at else None,
    }


def _workthread_task_result(result) -> dict[str, Any]:
    return {
        "task_id": result.task_id,
        "thread_id": result.thread_id,
        "title": result.title,
        "status": result.status,
        "lease_owner": result.lease_owner,
        "lease_expires_at": _iso(result.lease_expires_at) if result.lease_expires_at else None,
        "result_message_id": result.result_message_id,
        "created_at": _iso(result.created_at),
        "updated_at": _iso(result.updated_at),
    }


def _validate_save_request(
    *,
    slot_name: str,
    content: dict[str, Any],
    original_length: int | None,
    model_source: str | None,
    slot_number: int | None,
    retention_seconds: int | None,
    detail_level: str | None,
) -> WebContextSaveRequest:
    try:
        return WebContextSaveRequest(
            slot_name=slot_name,
            slot_number=slot_number,
            content=content,
            original_length=original_length,
            model_source=model_source,
            retention_seconds=retention_seconds,
            detail_level=detail_level or "compact",
        )
    except ValidationError as exc:
        raise AppError("invalid_tool_input", "Invalid save_context input", 422, {"details": exc.errors()}) from exc


@web_mcp.tool(name="save_context", description=SAVE_CONTEXT_DESCRIPTION)
def save_context(
    slot_name: str,
    content: dict,
    original_length: int | None = None,
    model_source: str | None = None,
    slot_number: int | None = None,
    retention_seconds: int | None = None,
    detail_level: str | None = "compact",
) -> dict:
    raise AppError(
        "client_encryption_required",
        "Direct remote MCP save_context cannot save WorkBaton content. Use the local stdio A2CR MCP wrapper so content is encrypted before upload.",
        422,
    )


@web_mcp.tool(name="resume_context", description=RESUME_CONTEXT_DESCRIPTION)
def resume_context(
    slot_name: str | None = None,
    slot_number: int | None = None,
    project: str | None = None,
    prefer_latest: bool = False,
) -> dict:
    user, meta = _current_auth_context()
    enforce_authenticated_rate_limit(user.user_id, "context.read")
    if slot_name is None and slot_number is None and project is None:
        candidates = web_context_service.list_contexts(user_id=user.user_id)
        if not candidates:
            raise SlotNotFound()
        return {
            "mode": "candidates",
            "context": None,
            "candidates": [_metadata_result(item) for item in candidates],
        }
    result = web_context_service.resume_context(
        user_id=user.user_id,
        slot_name=slot_name,
        slot_number=slot_number,
        project=project,
        prefer_latest=prefer_latest,
        meta=meta,
    )
    return _resume_result(result)


@web_mcp.tool(name="load_context", description=LOAD_CONTEXT_DESCRIPTION)
def load_context(slot_name: str | None = None, slot_number: int | None = None) -> dict:
    user, meta = _current_auth_context()
    enforce_authenticated_rate_limit(user.user_id, "context.read")
    result = web_context_service.load_context(
        user_id=user.user_id,
        slot_name=slot_name,
        slot_number=slot_number,
        meta=meta,
    )
    return _load_result(result)


@web_mcp.tool(name="list_contexts", description=LIST_CONTEXTS_DESCRIPTION)
def list_contexts() -> list:
    user, _ = _current_auth_context()
    enforce_authenticated_rate_limit(user.user_id, "context.read")
    return [_metadata_result(item) for item in web_context_service.list_contexts(user_id=user.user_id)]


@web_mcp.tool(name="get_account_limits", description=GET_LIMITS_DESCRIPTION)
def get_account_limits() -> dict:
    user, _ = _current_auth_context()
    enforce_authenticated_rate_limit(user.user_id, "context.read")
    profile = dashboard_service.get_profile(user.user_id)
    limits = get_plan_limits(profile.plan)
    return {
        "plan": profile.plan,
        "active_slots": limits.active_slots,
        "allowed_retention_seconds": list(limits.allowed_retention_seconds),
        "default_retention_seconds": profile.default_retention_seconds,
        "max_body_bytes": limits.max_body_bytes,
        "allowed_detail_levels": list(limits.allowed_detail_levels),
        "context_detail_level": profile.context_detail_level,
        "saves_per_hour": limits.saves_per_hour,
        "loads_per_hour": limits.loads_per_hour,
        "access_log_retention_seconds": limits.access_log_retention_seconds,
        "api_keys": limits.api_keys,
        "preferred_locale": profile.preferred_locale,
        "response_language": profile.response_language,
        "timezone": profile.timezone,
    }


@web_mcp.tool(name="create_workthread", description=CREATE_WORKTHREAD_DESCRIPTION)
def create_workthread(
    title: str,
    purpose: str | None = None,
    initial_message: dict | None = None,
    agent_name: str | None = None,
    idempotency_key: str | None = None,
) -> dict:
    user, _ = _current_auth_context()
    enforce_authenticated_rate_limit(user.user_id, "workthreads.write")
    result = workthreads_service.create_workthread(
        user_id=user.user_id,
        title=title,
        purpose=purpose,
        initial_message=initial_message,
        agent_name=agent_name,
        idempotency_key=idempotency_key,
    )
    return _workthread_result(result)


@web_mcp.tool(name="list_workthreads", description="List WorkThread progress metadata only. This never returns message content.")
def list_workthreads() -> list:
    user, _ = _current_auth_context()
    enforce_authenticated_rate_limit(user.user_id, "workthreads.read")
    return [_workthread_result(item) for item in workthreads_service.list_workthreads(user_id=user.user_id)]


@web_mcp.tool(name="post_workthread_message", description=POST_WORKTHREAD_MESSAGE_DESCRIPTION)
def post_workthread_message(
    thread_id: str,
    content: dict,
    message_type: str = "note",
    parent_message_id: str | None = None,
    consultation_id: str | None = None,
    requires_response: bool = False,
    target_agent_name: str | None = None,
    response_deadline: str | None = None,
    idempotency_key: str | None = None,
    agent_name: str | None = None,
) -> dict:
    user, _ = _current_auth_context()
    enforce_authenticated_rate_limit(user.user_id, "workthreads.write")
    result = workthreads_service.post_workthread_message(
        user_id=user.user_id,
        thread_id=thread_id,
        content_dict=content,
        message_type=message_type,
        parent_message_id=parent_message_id,
        consultation_id=consultation_id,
        requires_response=requires_response,
        target_agent_name=target_agent_name,
        response_deadline=datetime.fromisoformat(response_deadline) if response_deadline else None,
        idempotency_key=idempotency_key,
        agent_name=agent_name,
    )
    return _workthread_message_result(result)


@web_mcp.tool(name="read_workthread", description=READ_WORKTHREAD_DESCRIPTION)
def read_workthread(thread_id: str, limit: int = 100) -> list:
    user, _ = _current_auth_context()
    enforce_authenticated_rate_limit(user.user_id, "workthreads.read")
    return [
        _workthread_message_result(item)
        for item in workthreads_service.read_workthread(user_id=user.user_id, thread_id=thread_id, limit=limit)
    ]


@web_mcp.tool(name="unread_workthread", description=WORKTHREAD_UNREAD_DESCRIPTION)
def unread_workthread(thread_id: str, target_agent_name: str | None = None) -> list:
    user, _ = _current_auth_context()
    enforce_authenticated_rate_limit(user.user_id, "workthreads.read")
    return [
        _workthread_message_result(item)
        for item in workthreads_service.unread_workthread_messages(
            user_id=user.user_id,
            thread_id=thread_id,
            target_agent_name=target_agent_name,
        )
    ]


@web_mcp.tool(name="check_workthread_updates", description=WORKTHREAD_UPDATES_DESCRIPTION)
def check_workthread_updates(thread_id: str, since: str | None = None) -> dict:
    user, _ = _current_auth_context()
    enforce_authenticated_rate_limit(user.user_id, "workthreads.read")
    parsed_since = datetime.fromisoformat(since) if since else None
    return _workthread_update_result(
        workthreads_service.check_workthread_updates(user_id=user.user_id, thread_id=thread_id, since=parsed_since)
    )


@web_mcp.tool(name="wait_workthread_updates", description=WORKTHREAD_UPDATES_DESCRIPTION)
def wait_workthread_updates(
    thread_id: str,
    since: str | None = None,
    timeout_seconds: int = 30,
) -> dict:
    user, _ = _current_auth_context()
    enforce_authenticated_rate_limit(user.user_id, "workthreads.wait")
    parsed_since = datetime.fromisoformat(since) if since else None
    return _workthread_update_result(
        workthreads_service.wait_workthread_updates(
            user_id=user.user_id,
            thread_id=thread_id,
            since=parsed_since,
            timeout_seconds=timeout_seconds,
        )
    )


@web_mcp.tool(name="create_workthread_task", description="Create a pending WorkThread task for later claim by an agent.")
def create_workthread_task(thread_id: str, title: str) -> dict:
    user, _ = _current_auth_context()
    enforce_authenticated_rate_limit(user.user_id, "workthreads.task")
    return _workthread_task_result(
        workthreads_service.create_workthread_task(user_id=user.user_id, thread_id=thread_id, title=title)
    )


@web_mcp.tool(
    name="claim_workthread_task",
    description="Claim one pending or expired WorkThread task using a short lease. Uses database SKIP LOCKED semantics.",
)
def claim_workthread_task(
    lease_owner: str,
    thread_id: str | None = None,
    lease_seconds: int = 300,
) -> dict | None:
    user, _ = _current_auth_context()
    enforce_authenticated_rate_limit(user.user_id, "workthreads.task")
    task = workthreads_service.claim_workthread_task(
        user_id=user.user_id,
        lease_owner=lease_owner,
        thread_id=thread_id,
        lease_seconds=lease_seconds,
    )
    return _workthread_task_result(task) if task else None


@web_mcp.tool(
    name="complete_workthread_task",
    description="Complete a claimed WorkThread task. The lease_owner must match the active lease.",
)
def complete_workthread_task(
    task_id: str,
    lease_owner: str,
    result_message_id: str | None = None,
) -> dict:
    user, _ = _current_auth_context()
    enforce_authenticated_rate_limit(user.user_id, "workthreads.task")
    return _workthread_task_result(
        workthreads_service.complete_workthread_task(
            user_id=user.user_id,
            task_id=task_id,
            lease_owner=lease_owner,
            result_message_id=result_message_id,
        )
    )


@web_mcp.tool(
    name="save_workthread_result",
    description=(
        "Disabled until WorkThread final-result saving has a local stdio encryption flow. "
        "Do not send WorkThread result content to this remote MCP tool."
    ),
)
def save_workthread_result(
    thread_id: str,
    slot_name: str,
    content: dict,
    original_length: int | None = None,
    model_source: str | None = None,
    slot_number: int | None = None,
    retention_seconds: int | None = None,
    detail_level: str | None = "compact",
) -> dict:
    raise AppError(
        "client_encryption_required",
        "Saving a WorkThread result into WorkBaton requires the local stdio A2CR MCP wrapper so content is encrypted before upload.",
        422,
    )


mcp_app = ReusableMCPApp()
