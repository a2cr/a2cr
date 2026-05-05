from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, field_validator


class ContentSchema(BaseModel):
    goal: str
    current_state: str
    next_action: str
    decisions: list[str] = []
    constraints: list[str] = []
    problems: list[str] = []
    environment: Optional[str] = None
    background: Optional[str] = None
    summary: Optional[str] = None
    failed_attempts: list[str] = []
    references: list[str] = []


class SaveRequest(BaseModel):
    slot_name: str
    slot_number: Optional[int] = None
    content: ContentSchema
    original_length: Optional[int] = None
    model_source: Optional[Literal["claude", "gpt", "gemini", "other"]] = None

    @field_validator("slot_name")
    @classmethod
    def validate_slot_name(cls, v: str) -> str:
        import re
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", v):
            raise ValueError("slot_name must match ^[a-zA-Z0-9_-]{1,64}$")
        return v

    @field_validator("slot_number")
    @classmethod
    def validate_slot_number(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not 1 <= v <= 3:
            raise ValueError("slot_number must be between 1 and 3")
        return v

    @field_validator("original_length")
    @classmethod
    def validate_original_length(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("original_length must be >= 0")
        return v


class SaveResponse(BaseModel):
    slot_name: str
    slot_number: Optional[int] = None
    expires_at: datetime
    compressed_tokens: int
    saved_tokens: Optional[int] = None
    resume_context_call: str
    resume_prompt: str


class LoadResponse(BaseModel):
    slot_name: str
    slot_number: Optional[int] = None
    content: ContentSchema
    expires_at: datetime
    compressed_tokens: int
    model_source: Optional[str] = None
    load_count: int


class ListItem(BaseModel):
    slot_name: str
    slot_number: Optional[int] = None
    expires_at: datetime
    updated_at: datetime
    size_bytes: int
    compressed_tokens: int
    model_source: Optional[str] = None


class HandoffResponse(BaseModel):
    slot_name: str
    handoff_text: str


class ErrorResponse(BaseModel):
    code: str
    message: str


class WebContextSaveRequest(BaseModel):
    slot_name: str
    slot_number: Optional[int] = None
    content: ContentSchema
    original_length: Optional[int] = None
    model_source: Optional[Literal["claude", "gpt", "gemini", "other"]] = None
    retention_seconds: Optional[int] = None
    detail_level: Optional[Literal["compact", "detailed"]] = "compact"

    @field_validator("slot_name")
    @classmethod
    def validate_slot_name(cls, v: str) -> str:
        import re
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", v):
            raise ValueError("slot_name must match ^[a-zA-Z0-9_-]{1,64}$")
        return v

    @field_validator("slot_number")
    @classmethod
    def validate_slot_number(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
            raise ValueError("slot_number must be >= 1")
        return v

    @field_validator("retention_seconds")
    @classmethod
    def validate_retention_seconds(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("retention_seconds must be > 0")
        return v


class WebContextSaveResponse(BaseModel):
    slot_name: str
    slot_number: int
    expires_at: datetime
    compressed_tokens: int
    saved_tokens: Optional[int] = None
    resume_context_call: str
    resume_prompt: str


class WebContextMetadataItem(BaseModel):
    slot_name: str
    slot_number: int
    expires_at: datetime
    updated_at: datetime
    size_bytes: int
    compressed_tokens: int
    detail_level: str
    model_source: Optional[str] = None
    load_count: int


class WebContextLoadResponse(BaseModel):
    slot_name: str
    slot_number: int
    content: ContentSchema
    expires_at: datetime
    compressed_tokens: int
    detail_level: str
    model_source: Optional[str] = None
    load_count: int


class WebContextResumeResponse(BaseModel):
    mode: Literal["loaded", "candidates"]
    context: Optional[WebContextLoadResponse] = None
    candidates: list[WebContextMetadataItem] = []


class DashboardProfileResponse(BaseModel):
    user_id: str
    plan: str
    context_detail_level: str
    default_retention_seconds: int
    preferred_locale: str
    response_language: str
    timezone: str
    created_at: datetime
    updated_at: datetime


class DashboardProfileUpdateRequest(BaseModel):
    context_detail_level: Optional[Literal["compact", "detailed"]] = None
    default_retention_seconds: Optional[int] = None
    preferred_locale: Optional[str] = None
    response_language: Optional[str] = None
    timezone: Optional[str] = None

    @field_validator("default_retention_seconds")
    @classmethod
    def validate_default_retention_seconds(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("default_retention_seconds must be > 0")
        return v

    @field_validator("preferred_locale", "response_language", "timezone")
    @classmethod
    def validate_short_setting(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and (not v or len(v) > 64):
            raise ValueError("setting must be 1-64 characters")
        return v


class DashboardContextItem(BaseModel):
    slot_name: str
    slot_number: int
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    size_bytes: int
    compressed_tokens: int
    saved_tokens: int
    detail_level: str
    model_source: Optional[str] = None
    load_count: int
    resume_context_call: str
    resume_prompt: str


class DashboardStatsResponse(BaseModel):
    total_saves: int
    total_loads: int
    total_deletes: int
    total_tokens_saved: int
    active_slots: int


class DashboardAccessLogItem(BaseModel):
    action: str
    slot_name: Optional[str] = None
    client_type: str
    result: str
    error_code: Optional[str] = None
    size_bytes: Optional[int] = None
    request_id: Optional[str] = None
    created_at: datetime


class DashboardApiKeyResponse(BaseModel):
    key_prefix: str
    created_at: datetime
    last_used_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None


class DashboardApiKeyCreateResponse(BaseModel):
    api_key: str
    key_prefix: str
    created_at: datetime
