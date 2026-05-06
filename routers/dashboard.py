from __future__ import annotations

from fastapi import APIRouter, Depends, Header

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
import services.dashboard as dashboard_service
import services.workthreads as workthreads_service

router = APIRouter(prefix="/api/dashboard")


def get_current_dashboard_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> AuthenticatedUser:
    token = extract_bearer_token(authorization)
    return verify_supabase_jwt(token)


def _profile_response(profile) -> DashboardProfileResponse:
    return DashboardProfileResponse(
        user_id=profile.user_id,
        plan=profile.plan,
        context_detail_level=profile.context_detail_level,
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
        detail_level=item.detail_level,
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
    return _profile_response(dashboard_service.get_profile(user.user_id))


@router.patch("/profile")
def update_profile(
    req: DashboardProfileUpdateRequest,
    user: AuthenticatedUser = Depends(get_current_dashboard_user),
) -> DashboardProfileResponse:
    return _profile_response(
        dashboard_service.update_profile(
            user_id=user.user_id,
            context_detail_level=req.context_detail_level,
            default_retention_seconds=req.default_retention_seconds,
            preferred_locale=req.preferred_locale,
            response_language=req.response_language,
            timezone=req.timezone,
        )
    )


@router.get("/contexts")
def list_contexts(user: AuthenticatedUser = Depends(get_current_dashboard_user)) -> list[DashboardContextItem]:
    return [_context_response(item) for item in dashboard_service.list_contexts(user.user_id)]


@router.get("/workthreads")
def list_workthreads(user: AuthenticatedUser = Depends(get_current_dashboard_user)) -> list[WorkThreadMetadataResponse]:
    profile = dashboard_service.get_profile(user.user_id)
    if profile.plan != "pro":
        return []
    return [_workthread_response(item) for item in workthreads_service.list_workthreads(user_id=user.user_id)]


@router.get("/stats")
def get_stats(user: AuthenticatedUser = Depends(get_current_dashboard_user)) -> DashboardStatsResponse:
    stats = dashboard_service.get_stats(user.user_id)
    return DashboardStatsResponse(
        total_saves=stats.total_saves,
        total_loads=stats.total_loads,
        total_deletes=stats.total_deletes,
        total_tokens_saved=stats.total_tokens_saved,
        active_slots=stats.active_slots,
    )


@router.get("/access-logs")
def list_access_logs(
    limit: int = 100,
    user: AuthenticatedUser = Depends(get_current_dashboard_user),
) -> list[DashboardAccessLogItem]:
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
    created = dashboard_service.create_api_key(user.user_id)
    return DashboardApiKeyCreateResponse(
        api_key=created.api_key,
        key_prefix=created.key_prefix,
        created_at=created.created_at,
    )


@router.delete("/api-key")
def revoke_api_key(user: AuthenticatedUser = Depends(get_current_dashboard_user)) -> dict:
    dashboard_service.revoke_api_key(user.user_id)
    return {"message": "revoked"}
