from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from services.abuse_limits import enforce_authenticated_rate_limit, ensure_auth_attempt_allowed, record_auth_failure
from services.auth import AuthenticatedUser, authenticate_api_key
from services.db import get_web_engine
from services.logs import hash_log_value
from services.web_context import RequestMeta
import services.work_stash as work_stash_service
from routers.web_context import _request_ip, get_current_api_user, request_meta

router = APIRouter(prefix="/api/v1")


class WorkStashStoreRequest(BaseModel):
    entry_key: str = Field(..., min_length=1, max_length=256, pattern=r"^[A-Za-z0-9_.:-]+$")
    encrypted_value: str = Field(..., description="Client-encrypted value ciphertext")
    size_bytes: int = Field(..., ge=0)
    tags: list[str] = Field(default_factory=list)


class WorkStashEntryResponse(BaseModel):
    entry_key: str
    encrypted_value: str
    size_bytes: int
    tags: list[str]
    created_at: str
    updated_at: str
    expires_at: str


class WorkStashStoreResponse(BaseModel):
    entry_key: str
    expires_at: str
    size_bytes: int
    quota_used_bytes: int
    quota_bytes: int
    entry_count: int
    entry_limit: int


class WorkStashEntryMetaItem(BaseModel):
    entry_key: str
    size_bytes: int
    tags: list[str]
    created_at: str
    updated_at: str
    expires_at: str


class WorkStashListResponse(BaseModel):
    entries: list[WorkStashEntryMetaItem]
    total_size_bytes: int
    quota_bytes: int
    entry_count: int
    entry_limit: int


@router.post("/work-stash", response_model=WorkStashStoreResponse)
def store_work_stash(
    body: WorkStashStoreRequest,
    user: AuthenticatedUser = Depends(get_current_api_user),
    meta: RequestMeta = Depends(request_meta),
):
    result = work_stash_service.store_work_stash(
        user_id=user.user_id,
        entry_key=body.entry_key,
        encrypted_value=body.encrypted_value,
        size_bytes=body.size_bytes,
        tags=body.tags,
        meta=meta,
    )
    return WorkStashStoreResponse(
        entry_key=result.entry_key,
        expires_at=result.expires_at.isoformat(),
        size_bytes=result.size_bytes,
        quota_used_bytes=result.quota_used_bytes,
        quota_bytes=result.quota_bytes,
        entry_count=result.entry_count,
        entry_limit=result.entry_limit,
    )


@router.get("/work-stash/{entry_key}", response_model=WorkStashEntryResponse)
def get_work_stash(
    entry_key: str,
    user: AuthenticatedUser = Depends(get_current_api_user),
    meta: RequestMeta = Depends(request_meta),
):
    result = work_stash_service.get_work_stash(
        user_id=user.user_id,
        entry_key=entry_key,
        meta=meta,
    )
    return WorkStashEntryResponse(
        entry_key=result.entry_key,
        encrypted_value=result.encrypted_value,
        size_bytes=result.size_bytes,
        tags=result.tags,
        created_at=result.created_at.isoformat(),
        updated_at=result.updated_at.isoformat(),
        expires_at=result.expires_at.isoformat(),
    )


@router.get("/work-stash", response_model=WorkStashListResponse)
def list_work_stash(
    user: AuthenticatedUser = Depends(get_current_api_user),
    tag_filter: str | None = None,
):
    tags = [t.strip() for t in tag_filter.split(",")] if tag_filter else None
    result = work_stash_service.list_work_stash(
        user_id=user.user_id,
        tag_filter=tags,
    )
    return WorkStashListResponse(
        entries=[
            WorkStashEntryMetaItem(
                entry_key=e.entry_key,
                size_bytes=e.size_bytes,
                tags=e.tags,
                created_at=e.created_at.isoformat(),
                updated_at=e.updated_at.isoformat(),
                expires_at=e.expires_at.isoformat(),
            )
            for e in result.entries
        ],
        total_size_bytes=result.total_size_bytes,
        quota_bytes=result.quota_bytes,
        entry_count=result.entry_count,
        entry_limit=result.entry_limit,
    )


@router.delete("/work-stash/{entry_key}", status_code=204)
def delete_work_stash(
    entry_key: str,
    user: AuthenticatedUser = Depends(get_current_api_user),
    meta: RequestMeta = Depends(request_meta),
):
    work_stash_service.delete_work_stash(
        user_id=user.user_id,
        entry_key=entry_key,
        meta=meta,
    )


@router.delete("/work-stash", status_code=200)
def delete_all_work_stash(
    user: AuthenticatedUser = Depends(get_current_api_user),
    meta: RequestMeta = Depends(request_meta),
):
    count = work_stash_service.delete_all_work_stash(
        user_id=user.user_id,
        meta=meta,
    )
    return {"deleted_count": count}
