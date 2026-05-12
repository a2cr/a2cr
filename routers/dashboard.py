from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request

from models.schemas import (
    DashboardAccessLogItem,
    DashboardApiKeyCreateResponse,
    DashboardApiKeyResponse,
    DashboardContextItem,
    DashboardProfileResponse,
    DashboardProfileUpdateRequest,
    DashboardStatsResponse,
    WorkThreadMetadataResponse,
)
from services.auth import AuthenticatedUser, extract_bearer_token, verify_supabase_jwt
from services.auth import AuthError
from services.abuse_limits import (
    enforce_authenticated_rate_limit,
    ensure_auth_attempt_allowed,
    record_auth_failure,
)
from services.logs import hash_log_value
import services.dashboard as dashboard_service
import services.web_context as web_context_service
import services.workthreads as workthreads_service
import services.work_stash as work_stash_service
from services.web_context import RequestMeta

router = APIRouter(prefix="/api/dashboard")


def get_current_dashboard_user(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> AuthenticatedUser:
    ip_hash = hash_log_value(_request_ip(request))
    ensure_auth_attempt_allowed("dashboard.jwt", ip_hash)
    try:
        token = extract_bearer_token(authorization)
        return verify_supabase_jwt(token)
    except AuthError:
        record_auth_failure("dashboard.jwt", ip_hash)
        raise


def _request_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else None


def request_meta(
    request: Request,
    x_request_id: str | None = Header(default=None, alias="X-Request-ID"),
) -> RequestMeta:
    return RequestMeta(
        client_type="dashboard",
        request_id=x_request_id,
        ip=_request_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


def _profile_response(profile) -> DashboardProfileResponse:
    return DashboardProfileResponse(
        user_id=profile.user_id,
        plan=profile.plan,
        default_retention_seconds=profile.default_retention_seconds,
        preferred_locale=profile.preferred_locale,
        response_language=profile.response_language,
        timezone=profile.timezone,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def _context_response(item) -> DashboardContextItem:
    return DashboardContextItem(
        slot_name=item.slot_name,
        slot_number=item.slot_number,
        encryption_mode=item.encryption_mode,
        created_at=item.created_at,
        updated_at=item.updated_at,
        expires_at=item.expires_at,
        size_bytes=item.size_bytes,
        compressed_tokens=item.compressed_tokens,
        saved_tokens=item.saved_tokens,
        model_source=item.model_source,
        load_count=item.load_count,
        resume_context_call=item.resume_context_call,
        resume_prompt=item.resume_prompt,
    )


def _workthread_response(item) -> WorkThreadMetadataResponse:
    return WorkThreadMetadataResponse(
        thread_id=item.thread_id,
        title=item.title,
        purpose=item.purpose,
        status=item.status,
        loop_status=item.loop_status,
        final_slot_name=item.final_slot_name,
        message_count=item.message_count,
        task_count=item.task_count,
        task_status_counts=item.task_status_counts,
        agent_names=item.agent_names,
        last_activity_at=item.last_activity_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.get("/profile")
def get_profile(user: AuthenticatedUser = Depends(get_current_dashboard_user)) -> DashboardProfileResponse:
    enforce_authenticated_rate_limit(user.user_id, "dashboard.read")
    return _profile_response(dashboard_service.get_profile(user.user_id))


@router.patch("/profile")
def update_profile(
    req: DashboardProfileUpdateRequest,
    user: AuthenticatedUser = Depends(get_current_dashboard_user),
) -> DashboardProfileResponse:
    enforce_authenticated_rate_limit(user.user_id, "dashboard.mutate")
    return _profile_response(
        dashboard_service.update_profile(
            user_id=user.user_id,
            default_retention_seconds=req.default_retention_seconds,
            preferred_locale=req.preferred_locale,
            response_language=req.response_language,
            timezone=req.timezone,
        )
    )


@router.get("/contexts")
def list_contexts(user: AuthenticatedUser = Depends(get_current_dashboard_user)) -> list[DashboardContextItem]:
    enforce_authenticated_rate_limit(user.user_id, "dashboard.read")
    return [_context_response(item) for item in dashboard_service.list_contexts(user.user_id)]


@router.delete("/contexts/{slot_name}")
def delete_context(
    slot_name: str,
    user: AuthenticatedUser = Depends(get_current_dashboard_user),
    meta: RequestMeta = Depends(request_meta),
) -> dict:
    enforce_authenticated_rate_limit(user.user_id, "context.delete")
    web_context_service.delete_context(user_id=user.user_id, slot_name=slot_name, meta=meta)
    return {"message": "deleted"}


@router.get("/workthreads")
def list_workthreads(user: AuthenticatedUser = Depends(get_current_dashboard_user)) -> list[WorkThreadMetadataResponse]:
    enforce_authenticated_rate_limit(user.user_id, "dashboard.read")
    profile = dashboard_service.get_profile(user.user_id)
    if profile.plan != "pro":
        return []
    return [_workthread_response(item) for item in workthreads_service.list_workthreads(user_id=user.user_id)]


@router.get("/stats")
def get_stats(user: AuthenticatedUser = Depends(get_current_dashboard_user)) -> DashboardStatsResponse:
    enforce_authenticated_rate_limit(user.user_id, "dashboard.read")
    stats = dashboard_service.get_stats(user.user_id)
    return DashboardStatsResponse(
        total_saves=stats.total_saves,
        total_loads=stats.total_loads,
        total_deletes=stats.total_deletes,
        total_tokens_saved=stats.total_tokens_saved,
        active_slots=stats.active_slots,
        active_slot_limit=stats.active_slot_limit,
    )


@router.get("/access-logs")
def list_access_logs(
    limit: int = 100,
    user: AuthenticatedUser = Depends(get_current_dashboard_user),
) -> list[DashboardAccessLogItem]:
    enforce_authenticated_rate_limit(user.user_id, "dashboard.read")
    return [
        DashboardAccessLogItem(
            action=item.action,
            slot_name=item.slot_name,
            client_type=item.client_type,
            result=item.result,
            error_code=item.error_code,
            size_bytes=item.size_bytes,
            request_id=item.request_id,
            created_at=item.created_at,
        )
        for item in dashboard_service.list_access_logs(user.user_id, limit=limit)
    ]


@router.get("/api-key")
def get_api_key(user: AuthenticatedUser = Depends(get_current_dashboard_user)) -> DashboardApiKeyResponse | None:
    enforce_authenticated_rate_limit(user.user_id, "dashboard.read")
    api_key = dashboard_service.get_api_key(user.user_id)
    if api_key is None:
        return None
    return DashboardApiKeyResponse(
        key_prefix=api_key.key_prefix,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        revoked_at=api_key.revoked_at,
    )


@router.post("/api-key", status_code=201)
def create_api_key(user: AuthenticatedUser = Depends(get_current_dashboard_user)) -> DashboardApiKeyCreateResponse:
    enforce_authenticated_rate_limit(user.user_id, "dashboard.api_key.mutate")
    created = dashboard_service.create_api_key(user.user_id)
    return DashboardApiKeyCreateResponse(
        api_key=created.api_key,
        key_prefix=created.key_prefix,
        created_at=created.created_at,
    )


@router.delete("/api-key")
def revoke_api_key(user: AuthenticatedUser = Depends(get_current_dashboard_user)) -> dict:
    enforce_authenticated_rate_limit(user.user_id, "dashboard.api_key.mutate")
    dashboard_service.revoke_api_key(user.user_id)
    return {"message": "revoked"}


@router.get("/work-stash")
def get_work_stash_usage(user: AuthenticatedUser = Depends(get_current_dashboard_user)) -> dict:
    enforce_authenticated_rate_limit(user.user_id, "dashboard.read")
    result = work_stash_service.list_work_stash(user_id=user.user_id, tag_filter=None)
    return {
        "total_size_bytes": result.total_size_bytes,
        "quota_bytes": result.quota_bytes,
        "entry_count": result.entry_count,
        "entry_limit": result.entry_limit,
    }
