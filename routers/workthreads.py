from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends

from models.schemas import (
    WorkThreadCreateRequest,
    WorkThreadMessageRequest,
    WorkThreadMessageResponse,
    WorkThreadMetadataResponse,
    WorkThreadResultSaveRequest,
    WorkThreadResultSaveResponse,
    WorkThreadTaskClaimRequest,
    WorkThreadTaskCompleteRequest,
    WorkThreadTaskCreateRequest,
    WorkThreadTaskResponse,
    WorkThreadUpdateCheckResponse,
)
from routers.web_context import get_current_api_user
from services.auth import AuthenticatedUser
from services.exceptions import AppError
import services.workthreads as workthreads_service

router = APIRouter(prefix="/api/v1/workthreads")


def _thread_response(item) -> WorkThreadMetadataResponse:
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


def _message_response(item) -> WorkThreadMessageResponse:
    return WorkThreadMessageResponse(
        message_id=item.message_id,
        thread_id=item.thread_id,
        message_type=item.message_type,
        content=item.content,
        consultation_id=item.consultation_id,
        requires_response=item.requires_response,
        target_agent_name=item.target_agent_name,
        agent_name=item.agent_name,
        created_at=item.created_at,
        loop_warning=item.loop_warning,
    )


def _task_response(item) -> WorkThreadTaskResponse:
    return WorkThreadTaskResponse(
        task_id=item.task_id,
        thread_id=item.thread_id,
        title=item.title,
        status=item.status,
        lease_owner=item.lease_owner,
        lease_expires_at=item.lease_expires_at,
        result_message_id=item.result_message_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.post("", status_code=201)
def create_workthread(
    req: WorkThreadCreateRequest,
    user: AuthenticatedUser = Depends(get_current_api_user),
) -> WorkThreadMetadataResponse:
    return _thread_response(
        workthreads_service.create_workthread(
            user_id=user.user_id,
            title=req.title,
            purpose=req.purpose,
            initial_message=req.initial_message,
            agent_name=req.agent_name,
            idempotency_key=req.idempotency_key,
        )
    )


@router.get("")
def list_workthreads(user: AuthenticatedUser = Depends(get_current_api_user)) -> list[WorkThreadMetadataResponse]:
    return [_thread_response(item) for item in workthreads_service.list_workthreads(user_id=user.user_id)]


@router.post("/{thread_id}/messages", status_code=201)
def post_workthread_message(
    thread_id: str,
    req: WorkThreadMessageRequest,
    user: AuthenticatedUser = Depends(get_current_api_user),
) -> WorkThreadMessageResponse:
    return _message_response(
        workthreads_service.post_workthread_message(
            user_id=user.user_id,
            thread_id=thread_id,
            content_dict=req.content,
            message_type=req.message_type,
            parent_message_id=req.parent_message_id,
            consultation_id=req.consultation_id,
            requires_response=req.requires_response,
            target_agent_name=req.target_agent_name,
            response_deadline=req.response_deadline,
            idempotency_key=req.idempotency_key,
            agent_name=req.agent_name,
        )
    )


@router.get("/{thread_id}/messages")
def read_workthread(
    thread_id: str,
    limit: int = 100,
    user: AuthenticatedUser = Depends(get_current_api_user),
) -> list[WorkThreadMessageResponse]:
    return [
        _message_response(item)
        for item in workthreads_service.read_workthread(user_id=user.user_id, thread_id=thread_id, limit=limit)
    ]


@router.get("/{thread_id}/unread")
def unread_workthread_messages(
    thread_id: str,
    target_agent_name: str | None = None,
    user: AuthenticatedUser = Depends(get_current_api_user),
) -> list[WorkThreadMessageResponse]:
    return [
        _message_response(item)
        for item in workthreads_service.unread_workthread_messages(
            user_id=user.user_id,
            thread_id=thread_id,
            target_agent_name=target_agent_name,
        )
    ]


@router.get("/{thread_id}/updates")
def check_workthread_updates(
    thread_id: str,
    since: datetime | None = None,
    user: AuthenticatedUser = Depends(get_current_api_user),
) -> WorkThreadUpdateCheckResponse:
    result = workthreads_service.check_workthread_updates(user_id=user.user_id, thread_id=thread_id, since=since)
    return WorkThreadUpdateCheckResponse(
        thread_id=result.thread_id,
        has_updates=result.has_updates,
        message_count=result.message_count,
        latest_message_at=result.latest_message_at,
    )


@router.get("/{thread_id}/wait")
def wait_workthread_updates(
    thread_id: str,
    since: datetime | None = None,
    timeout_seconds: int = 30,
    user: AuthenticatedUser = Depends(get_current_api_user),
) -> WorkThreadUpdateCheckResponse:
    result = workthreads_service.wait_workthread_updates(
        user_id=user.user_id,
        thread_id=thread_id,
        since=since,
        timeout_seconds=timeout_seconds,
    )
    return WorkThreadUpdateCheckResponse(
        thread_id=result.thread_id,
        has_updates=result.has_updates,
        message_count=result.message_count,
        latest_message_at=result.latest_message_at,
    )


@router.post("/{thread_id}/tasks", status_code=201)
def create_workthread_task(
    thread_id: str,
    req: WorkThreadTaskCreateRequest,
    user: AuthenticatedUser = Depends(get_current_api_user),
) -> WorkThreadTaskResponse:
    return _task_response(
        workthreads_service.create_workthread_task(user_id=user.user_id, thread_id=thread_id, title=req.title)
    )


@router.post("/tasks/claim")
def claim_workthread_task(
    req: WorkThreadTaskClaimRequest,
    user: AuthenticatedUser = Depends(get_current_api_user),
) -> WorkThreadTaskResponse | None:
    task = workthreads_service.claim_workthread_task(
        user_id=user.user_id,
        lease_owner=req.lease_owner,
        thread_id=req.thread_id,
        lease_seconds=req.lease_seconds,
    )
    return _task_response(task) if task else None


@router.post("/tasks/{task_id}/complete")
def complete_workthread_task(
    task_id: str,
    req: WorkThreadTaskCompleteRequest,
    user: AuthenticatedUser = Depends(get_current_api_user),
) -> WorkThreadTaskResponse:
    return _task_response(
        workthreads_service.complete_workthread_task(
            user_id=user.user_id,
            task_id=task_id,
            lease_owner=req.lease_owner,
            result_message_id=req.result_message_id,
        )
    )


@router.post("/{thread_id}/result")
def save_workthread_result(
    thread_id: str,
    req: WorkThreadResultSaveRequest,
    user: AuthenticatedUser = Depends(get_current_api_user),
) -> WorkThreadResultSaveResponse:
    raise AppError(
        "client_encryption_required",
        "Saving a WorkThread result into WorkBaton requires client-side encryption before upload.",
        422,
    )
