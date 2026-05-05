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
    "Use these MCP tools for save, resume, load, and list operations. "
    "Do not guess or call direct HTTP API endpoints. "
    "Never save secrets, API keys, Authorization headers, private database URLs, "
    "full transcripts, long logs, generated caches, or large code bodies that can be read from the repository."
)

SAVE_CONTEXT_DESCRIPTION = (
    "Save a WorkBaton checkpoint for a future AI window. The content object must include "
    "goal, current_state, and next_action. Keep Free saves compact. Pro detailed saves may include "
    "important decisions, constraints, failed attempts, references, and verification results. "
    "Never include secrets, API keys, Authorization headers, private database URLs, full transcripts, "
    "or long logs. Use the returned resume_prompt for the next AI window."
    " Use this MCP tool; do not guess direct HTTP API endpoints."
)

RESUME_CONTEXT_DESCRIPTION = (
    "Resume a WorkBaton checkpoint in a fresh AI window. Prefer slot_name when a resume prompt provides it. "
    "slot_number is an optional compatibility path. If project search is ambiguous, candidates are returned "
    "without saved content. Use this MCP tool; do not guess direct HTTP API endpoints."
)

LOAD_CONTEXT_DESCRIPTION = (
    "Load a known WorkBaton checkpoint by slot_name or slot_number. Provide exactly one selector. "
    "Use resume_context first in a fresh AI window when possible. Do not guess direct HTTP API endpoints."
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
    with Session(get_web_engine()) as session:
        user = authenticate_api_key(
            session,
            request.headers.get("authorization"),
            ip_hash=hash_log_value(ip),
        )
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
    }


def _load_result(result: WebLoadResult) -> dict[str, Any]:
    return {
        "slot_name": result.slot_name,
        "slot_number": result.slot_number,
        "content": result.content,
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
    user, meta = _current_auth_context()
    req = _validate_save_request(
        slot_name=slot_name,
        content=content,
        original_length=original_length,
        model_source=model_source,
        slot_number=slot_number,
        retention_seconds=retention_seconds,
        detail_level=detail_level,
    )
    result = web_context_service.save_context(
        user_id=user.user_id,
        slot_name=req.slot_name,
        content_dict=req.content.model_dump(),
        original_length=req.original_length,
        model_source=req.model_source,
        slot_number=req.slot_number,
        retention_seconds=req.retention_seconds,
        detail_level=req.detail_level,
        meta=meta,
    )
    return _save_result(result)


@web_mcp.tool(name="resume_context", description=RESUME_CONTEXT_DESCRIPTION)
def resume_context(
    slot_name: str | None = None,
    slot_number: int | None = None,
    project: str | None = None,
    prefer_latest: bool = False,
) -> dict:
    user, meta = _current_auth_context()
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
    return [_metadata_result(item) for item in web_context_service.list_contexts(user_id=user.user_id)]


@web_mcp.tool(name="get_account_limits", description=GET_LIMITS_DESCRIPTION)
def get_account_limits() -> dict:
    user, _ = _current_auth_context()
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


mcp_app = ReusableMCPApp()
