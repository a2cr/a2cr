from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

ModelSource = Literal["claude", "gpt", "gemini", "codex", "other"]
EncryptionMode = Literal["server", "client"]


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


class EncryptedContentSchema(BaseModel):
    version: int = Field(ge=1)
    alg: str
    nonce: str
    ciphertext: str
    key_wrap: dict[str, Any] | None = None

    @field_validator("alg", "nonce", "ciphertext")
    @classmethod
    def validate_non_empty_string(cls, v: str) -> str:
        if not v:
            raise ValueError("field must not be empty")
        return v


class SaveRequest(BaseModel):
    slot_name: str
    slot_number: Optional[int] = None
    content: Optional[ContentSchema] = None
    encrypted_content: Optional[EncryptedContentSchema] = None
    original_length: Optional[int] = None
    model_source: Optional[ModelSource] = None

    @model_validator(mode="after")
    def validate_exactly_one_body(self) -> "SaveRequest":
        if (self.content is None) == (self.encrypted_content is None):
            raise ValueError("Provide exactly one of content or encrypted_content")
        return self

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
    encryption_mode: EncryptionMode = "server"
    content: Optional[ContentSchema] = None
    encrypted_content: Optional[EncryptedContentSchema] = None
    expires_at: datetime
    compressed_tokens: int
    model_source: Optional[str] = None
    load_count: int


class ListItem(BaseModel):
    slot_name: str
    slot_number: Optional[int] = None
    encryption_mode: EncryptionMode = "server"
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
    content: Optional[ContentSchema] = None
    encrypted_content: Optional[EncryptedContentSchema] = None
    original_length: Optional[int] = None
    model_source: Optional[ModelSource] = None
    retention_seconds: Optional[int] = None
    detail_level: Optional[Literal["compact", "detailed"]] = "compact"

    @model_validator(mode="after")
    def validate_exactly_one_body(self) -> "WebContextSaveRequest":
        if (self.content is None) == (self.encrypted_content is None):
            raise ValueError("Provide exactly one of content or encrypted_content")
        return self

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
    encryption_mode: EncryptionMode = "server"
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
    encryption_mode: EncryptionMode = "server"
    content: Optional[ContentSchema] = None
    encrypted_content: Optional[EncryptedContentSchema] = None
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
    encryption_mode: EncryptionMode = "server"
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


class WorkThreadCreateRequest(BaseModel):
    title: str
    purpose: Optional[str] = None
    initial_message: Optional[dict] = None
    agent_name: Optional[str] = None
    idempotency_key: Optional[str] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        if not v or len(v) > 120:
            raise ValueError("title must be 1-120 characters")
        return v


class WorkThreadMetadataResponse(BaseModel):
    thread_id: str
    title: str
    purpose: Optional[str] = None
    status: str
    loop_status: str
    final_slot_name: Optional[str] = None
    message_count: int
    task_count: int
    task_status_counts: dict[str, int]
    agent_names: list[str]
    last_activity_at: datetime
    created_at: datetime
    updated_at: datetime


class WorkThreadMessageRequest(BaseModel):
    content: dict
    message_type: Literal["note", "question", "answer", "decision", "handoff", "blocked", "result"] = "note"
    parent_message_id: Optional[str] = None
    consultation_id: Optional[str] = None
    requires_response: bool = False
    target_agent_name: Optional[str] = None
    response_deadline: Optional[datetime] = None
    idempotency_key: Optional[str] = None
    agent_name: Optional[str] = None


class WorkThreadMessageResponse(BaseModel):
    message_id: str
    thread_id: str
    message_type: str
    content: dict
    consultation_id: Optional[str] = None
    requires_response: bool
    target_agent_name: Optional[str] = None
    agent_name: Optional[str] = None
    created_at: datetime
    loop_warning: Optional[str] = None


class WorkThreadUpdateCheckResponse(BaseModel):
    thread_id: str
    has_updates: bool
    message_count: int
    latest_message_at: Optional[datetime] = None


class WorkThreadTaskCreateRequest(BaseModel):
    title: str

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        if not v or len(v) > 200:
            raise ValueError("title must be 1-200 characters")
        return v


class WorkThreadTaskClaimRequest(BaseModel):
    lease_owner: str
    thread_id: Optional[str] = None
    lease_seconds: int = 300

    @field_validator("lease_owner")
    @classmethod
    def validate_lease_owner(cls, v: str) -> str:
        if not v or len(v) > 120:
            raise ValueError("lease_owner must be 1-120 characters")
        return v


class WorkThreadTaskCompleteRequest(BaseModel):
    lease_owner: str
    result_message_id: Optional[str] = None


class WorkThreadTaskResponse(BaseModel):
    task_id: str
    thread_id: str
    title: str
    status: str
    lease_owner: Optional[str] = None
    lease_expires_at: Optional[datetime] = None
    result_message_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class WorkThreadResultSaveRequest(BaseModel):
    slot_name: str
    content: ContentSchema
    original_length: Optional[int] = None
    model_source: Optional[ModelSource] = None
    slot_number: Optional[int] = None
    retention_seconds: Optional[int] = None
    detail_level: Optional[Literal["compact", "detailed"]] = "compact"


class WorkThreadResultSaveResponse(BaseModel):
    thread_id: str
    final_slot_name: str
    resume_context_call: str
    resume_prompt: str
