from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from models.schemas import (
    WebContextLoadResponse,
    WebContextMetadataItem,
    WebContextResumeResponse,
    WebContextSaveRequest,
    WebContextSaveResponse,
)
from services.abuse_limits import (
    enforce_authenticated_rate_limit,
    ensure_auth_attempt_allowed,
    record_auth_failure,
)
from services.auth import AuthError, AuthenticatedUser, authenticate_api_key
from services.db import get_web_engine
from services.limits import get_plan_limits
from services.logs import hash_log_value
from services.web_context import RequestMeta
import services.dashboard as dashboard_service
import services.web_context as web_context_service

router = APIRouter(prefix="/api/v1")


def _request_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else None


def request_meta(
    request: Request,
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
    x_a2cr_client_type: str | None = Header(default=None, alias="X-A2CR-Client-Type"),
) -> RequestMeta:
    return RequestMeta(
        client_type=x_a2cr_client_type or "api",
        request_id=x_request_id,
        ip=_request_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


def get_current_api_user(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> AuthenticatedUser:
    ip_hash = hash_log_value(_request_ip(request))
    ensure_auth_attempt_allowed("api.api_key", ip_hash)
    try:
        with Session(get_web_engine()) as session:
            return authenticate_api_key(session, authorization, ip_hash=ip_hash)
    except AuthError:
        record_auth_failure("api.api_key", ip_hash)
        raise


def _save_response(result) -> WebContextSaveResponse:
    return WebContextSaveResponse(
        slot_name=result.slot_name,
        slot_number=result.slot_number,
        expires_at=result.expires_at,
        compressed_tokens=result.compressed_tokens,
        saved_tokens=result.saved_tokens,
        resume_context_call=result.resume_context_call,
        resume_prompt=result.resume_prompt,
    )


def _metadata_response(result) -> WebContextMetadataItem:
    return WebContextMetadataItem(
        slot_name=result.slot_name,
        slot_number=result.slot_number,
        encryption_mode=result.encryption_mode,
        expires_at=result.expires_at,
        updated_at=result.updated_at,
        size_bytes=result.size_bytes,
        compressed_tokens=result.compressed_tokens,
        detail_level=result.detail_level,
        model_source=result.model_source,
        load_count=result.load_count,
    )


def _load_response(result) -> WebContextLoadResponse:
    return WebContextLoadResponse(
        slot_name=result.slot_name,
        slot_number=result.slot_number,
        encryption_mode=result.encryption_mode,
        content=result.content,
        encrypted_content=result.encrypted_content,
        expires_at=result.expires_at,
        compressed_tokens=result.compressed_tokens,
        detail_level=result.detail_level,
        model_source=result.model_source,
        load_count=result.load_count,
    )


@router.post("/context", status_code=201)
def save_context(
    req: WebContextSaveRequest,
    user: AuthenticatedUser = Depends(get_current_api_user),
    meta: RequestMeta = Depends(request_meta),
) -> WebContextSaveResponse:
    enforce_authenticated_rate_limit(user.user_id, "context.write")
    result = web_context_service.save_context(
        user_id=user.user_id,
        slot_name=req.slot_name,
        content_dict=req.content.model_dump() if req.content else None,
        encrypted_content=req.encrypted_content.model_dump() if req.encrypted_content else None,
        original_length=req.original_length,
        compressed_tokens=req.compressed_tokens,
        model_source=req.model_source,
        slot_number=req.slot_number,
        retention_seconds=req.retention_seconds,
        detail_level=req.detail_level,
        meta=meta,
    )
    return _save_response(result)


@router.get("/contexts")
def list_contexts(user: AuthenticatedUser = Depends(get_current_api_user)) -> list[WebContextMetadataItem]:
    enforce_authenticated_rate_limit(user.user_id, "context.read")
    return [_metadata_response(item) for item in web_context_service.list_contexts(user_id=user.user_id)]


@router.get("/account/limits")
def get_account_limits(user: AuthenticatedUser = Depends(get_current_api_user)) -> dict:
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


@router.get("/context/resume")
def resume_context(
    slot_name: str | None = None,
    slot_number: int | None = None,
    project: str | None = None,
    prefer_latest: bool = False,
    user: AuthenticatedUser = Depends(get_current_api_user),
    meta: RequestMeta = Depends(request_meta),
) -> WebContextResumeResponse:
    enforce_authenticated_rate_limit(user.user_id, "context.read")
    result = web_context_service.resume_context(
        user_id=user.user_id,
        slot_name=slot_name,
        slot_number=slot_number,
        project=project,
        prefer_latest=prefer_latest,
        meta=meta,
    )
    return WebContextResumeResponse(
        mode=result.mode,  # type: ignore[arg-type]
        context=_load_response(result.context) if result.context else None,
        candidates=[_metadata_response(item) for item in (result.candidates or [])],
    )


@router.get("/context/slot/{slot_number}")
def load_context_by_slot_number(
    slot_number: int,
    user: AuthenticatedUser = Depends(get_current_api_user),
    meta: RequestMeta = Depends(request_meta),
) -> WebContextLoadResponse:
    enforce_authenticated_rate_limit(user.user_id, "context.read")
    return _load_response(web_context_service.load_context(user_id=user.user_id, slot_number=slot_number, meta=meta))


@router.get("/context/{slot_name}")
def load_context(
    slot_name: str,
    user: AuthenticatedUser = Depends(get_current_api_user),
    meta: RequestMeta = Depends(request_meta),
) -> WebContextLoadResponse:
    enforce_authenticated_rate_limit(user.user_id, "context.read")
    return _load_response(web_context_service.load_context(user_id=user.user_id, slot_name=slot_name, meta=meta))


@router.delete("/context/{slot_name}")
def delete_context(
    slot_name: str,
    user: AuthenticatedUser = Depends(get_current_api_user),
    meta: RequestMeta = Depends(request_meta),
) -> dict:
    enforce_authenticated_rate_limit(user.user_id, "context.delete")
    web_context_service.delete_context(user_id=user.user_id, slot_name=slot_name, meta=meta)
    return {"message": "deleted"}
