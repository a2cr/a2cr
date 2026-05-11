from __future__ import annotations

import hashlib
import hmac
import re
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from services.config import get_web_config


_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")
_GENERIC_CLIENT_TYPES = {"", "api", "mcp"}


def infer_access_log_client_type(client_type: str, user_agent: str | None = None) -> str:
    explicit = (client_type or "").strip()
    if explicit.lower() not in _GENERIC_CLIENT_TYPES:
        return explicit
    agent = (user_agent or "").lower()
    if "chatgpt" in agent or "openai" in agent:
        return "gpt"
    if "claude" in agent or "anthropic" in agent:
        return "claude"
    if "codex" in agent:
        return "codex"
    return explicit or "api"


def hash_log_value(value: str | None, secret: str | None = None) -> str | None:
    if not value:
        return None
    secret = secret or get_web_config().audit_hash_secret
    return hmac.new(secret.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


def sanitize_log_request_id(request_id: str | None) -> str | None:
    if not request_id:
        return None
    if request_id.lower().startswith(("bearer", "sk-")):
        return None
    if _REQUEST_ID_PATTERN.fullmatch(request_id):
        return request_id
    return None


def build_access_log_row(
    *,
    user_id: UUID | str,
    action: str,
    client_type: str,
    result: str,
    slot_name: str | None = None,
    error_code: str | None = None,
    size_bytes: int | None = None,
    request_id: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    hash_secret: str | None = None,
) -> dict[str, Any]:
    return {
        "user_id": str(user_id),
        "action": action,
        "slot_name": slot_name,
        "client_type": infer_access_log_client_type(client_type, user_agent),
        "result": result,
        "error_code": error_code,
        "size_bytes": max(size_bytes, 0) if size_bytes is not None else None,
        "request_id": sanitize_log_request_id(request_id),
        "ip_hash": hash_log_value(ip, hash_secret),
        "user_agent_hash": hash_log_value(user_agent, hash_secret),
    }


def write_access_log(session: Session, row: dict[str, Any]) -> None:
    allowed = {
        "user_id",
        "action",
        "slot_name",
        "client_type",
        "result",
        "error_code",
        "size_bytes",
        "request_id",
        "ip_hash",
        "user_agent_hash",
    }
    safe_row = {key: row.get(key) for key in allowed}
    safe_row["request_id"] = sanitize_log_request_id(safe_row["request_id"])
    session.execute(
        text(
            """
            INSERT INTO public.access_logs (
              user_id, action, slot_name, client_type, result,
              error_code, size_bytes, request_id, ip_hash, user_agent_hash
            )
            VALUES (
              :user_id, :action, :slot_name, :client_type, :result,
              :error_code, :size_bytes, :request_id, :ip_hash, :user_agent_hash
            )
            """
        ),
        safe_row,
    )
