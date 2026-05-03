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

    @field_validator("original_length")
    @classmethod
    def validate_original_length(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("original_length must be >= 0")
        return v


class SaveResponse(BaseModel):
    slot_name: str
    expires_at: datetime
    compressed_tokens: int
    saved_tokens: Optional[int] = None


class LoadResponse(BaseModel):
    slot_name: str
    content: ContentSchema
    expires_at: datetime
    compressed_tokens: int
    model_source: Optional[str] = None
    load_count: int


class ListItem(BaseModel):
    slot_name: str
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
