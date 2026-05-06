from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.config import get_config
from services.db import get_engine, Context, Stats
from services.exceptions import (
    AppError,
    SlotLimitExceeded,
    ContentTooLarge,
    SlotNotFound,
    InvalidSlotNumber,
    SlotNameConflict,
)
from services.tokens import count_tokens, original_tokens_from_length_optional

_MAX_SLOTS = 3
_MAX_BYTES = 10_240
_TTL_MINUTES = 30


@dataclass
class SaveResult:
    slot_name: str
    slot_number: int | None
    expires_at: datetime
    compressed_tokens: int
    saved_tokens: Optional[int]
    original_tokens: Optional[int]
    encryption_mode: str = "client"


@dataclass
class LoadResult:
    slot_name: str
    slot_number: int | None
    content: dict | None
    encrypted_content: dict | None
    encryption_mode: str
    expires_at: datetime
    compressed_tokens: int
    model_source: Optional[str]
    load_count: int


@dataclass
class ListResult:
    slot_name: str
    slot_number: int | None
    encryption_mode: str
    expires_at: datetime
    updated_at: datetime
    size_bytes: int
    compressed_tokens: int
    model_source: Optional[str]


@dataclass
class HandoffResult:
    slot_name: str
    handoff_text: str


def _now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _validate_slot_number(slot_number: Optional[int]) -> None:
    if slot_number is not None and not 1 <= slot_number <= _MAX_SLOTS:
        raise InvalidSlotNumber()


def _delete_expired(session: Session, now: datetime) -> None:
    expired = session.execute(
        select(Context).where(Context.expires_at <= now)
    ).scalars().all()
    for ctx in expired:
        session.delete(ctx)
    if expired:
        session.flush()


def _next_free_slot_number(session: Session, now: datetime) -> int:
    used = {
        n
        for n in session.scalars(
            select(Context.slot_number).where(
                Context.expires_at > now,
                Context.slot_number.is_not(None),
            )
        ).all()
        if n is not None
    }
    for candidate in range(1, _MAX_SLOTS + 1):
        if candidate not in used:
            return candidate
    raise SlotLimitExceeded()


def save_context(
    slot_name: str,
    content_dict: dict | None,
    original_length: Optional[int],
    model_source: Optional[str],
    slot_number: Optional[int] = None,
    encrypted_content: dict | None = None,
) -> SaveResult:
    _validate_slot_number(slot_number)
    if content_dict is not None:
        raise AppError(
            "client_encryption_required",
            "WorkBaton requires client-encrypted encrypted_content; plaintext content is not accepted.",
            422,
        )
    if encrypted_content is None:
        raise ValueError("encrypted_content is required")

    encryption_mode = "client"
    content_json = json.dumps(encrypted_content, ensure_ascii=False)
    content_bytes = content_json.encode("utf-8")
    if len(content_bytes) > _MAX_BYTES:
        raise ContentTooLarge()

    stored_content = content_json
    compressed_tokens = count_tokens(content_json)
    original_tokens = original_tokens_from_length_optional(original_length)
    saved_tokens = (original_tokens - compressed_tokens) if original_tokens is not None else None

    now = _now_utc()
    expires_at = now + timedelta(minutes=_TTL_MINUTES)

    with Session(get_engine()) as session:
        _delete_expired(session, now)

        existing_by_name = session.execute(
            select(Context).where(Context.slot_name == slot_name)
        ).scalar_one_or_none()

        existing_by_number = None
        if slot_number is not None:
            existing_by_number = session.execute(
                select(Context).where(Context.slot_number == slot_number)
            ).scalar_one_or_none()

        if (
            existing_by_number is not None
            and existing_by_name is not None
            and existing_by_number.id != existing_by_name.id
        ):
            raise SlotNameConflict()

        existing = existing_by_number or existing_by_name
        assigned_slot_number = (
            slot_number
            if slot_number is not None
            else existing.slot_number if existing is not None and existing.slot_number is not None
            else _next_free_slot_number(session, now)
        )

        if existing is None:
            ctx = Context(
                id=str(uuid4()),
                slot_name=slot_name,
                slot_number=assigned_slot_number,
                content=stored_content,
                created_at=now,
                updated_at=now,
                expires_at=expires_at,
                size_bytes=len(content_bytes),
                original_tokens=original_tokens,
                compressed_tokens=compressed_tokens,
                load_count=0,
                model_source=model_source,
                encryption_mode=encryption_mode,
                encryption_version=1,
                encryption_metadata=None,
            )
            session.add(ctx)
        else:
            existing.slot_name = slot_name
            existing.slot_number = assigned_slot_number
            existing.content = stored_content
            existing.updated_at = now
            existing.expires_at = expires_at
            existing.size_bytes = len(content_bytes)
            existing.original_tokens = original_tokens
            existing.compressed_tokens = compressed_tokens
            existing.model_source = model_source
            existing.encryption_mode = encryption_mode
            existing.encryption_version = 1
            existing.encryption_metadata = None

        stats = session.get(Stats, 1)
        stats.total_saves += 1
        if saved_tokens is not None and saved_tokens > 0:
            stats.total_tokens_saved += saved_tokens

        session.commit()

    return SaveResult(
        slot_name=slot_name,
        slot_number=assigned_slot_number,
        expires_at=expires_at,
        compressed_tokens=compressed_tokens,
        saved_tokens=saved_tokens,
        original_tokens=original_tokens,
        encryption_mode=encryption_mode,
    )


def _find_context(
    session: Session,
    slot_name: Optional[str] = None,
    slot_number: Optional[int] = None,
) -> Context | None:
    _validate_slot_number(slot_number)
    if slot_number is not None:
        ctx = session.execute(
            select(Context).where(Context.slot_number == slot_number)
        ).scalar_one_or_none()
        if ctx is not None and slot_name is not None and ctx.slot_name != slot_name:
            return None
        return ctx
    if slot_name is not None:
        return session.execute(
            select(Context).where(Context.slot_name == slot_name)
        ).scalar_one_or_none()
    return None


def load_context(slot_name: Optional[str] = None, slot_number: Optional[int] = None) -> LoadResult:
    now = _now_utc()
    with Session(get_engine()) as session:
        ctx = _find_context(session, slot_name=slot_name, slot_number=slot_number)

        if ctx is None or ctx.expires_at < now:
            if ctx is not None:
                session.delete(ctx)
                session.commit()
            raise SlotNotFound()

        ctx.load_count += 1
        stats = session.get(Stats, 1)
        stats.total_loads += 1
        session.commit()

        encryption_mode = getattr(ctx, "encryption_mode", "client") or "client"
        if encryption_mode != "client":
            raise AppError(
                "legacy_decryption_disabled",
                "Legacy WorkBaton slots that require server-side decryption are disabled and cannot be loaded.",
                410,
            )
        content_dict = None
        encrypted_content = json.loads(ctx.content)
        return LoadResult(
            slot_name=ctx.slot_name,
            slot_number=ctx.slot_number,
            content=content_dict,
            encrypted_content=encrypted_content,
            encryption_mode=encryption_mode,
            expires_at=ctx.expires_at,
            compressed_tokens=ctx.compressed_tokens,
            model_source=ctx.model_source,
            load_count=ctx.load_count,
        )


def delete_context(slot_name: str) -> None:
    with Session(get_engine()) as session:
        ctx = session.execute(
            select(Context).where(Context.slot_name == slot_name)
        ).scalar_one_or_none()
        if ctx is None:
            raise SlotNotFound()
        session.delete(ctx)
        session.commit()


def list_contexts() -> list[ListResult]:
    now = _now_utc()
    with Session(get_engine()) as session:
        rows = session.execute(
            select(Context).where(Context.expires_at > now)
            .order_by(Context.slot_number.asc(), Context.updated_at.desc())
        ).scalars().all()
        return [
            ListResult(
                slot_name=r.slot_name,
                slot_number=r.slot_number,
                encryption_mode=getattr(r, "encryption_mode", "client") or "client",
                expires_at=r.expires_at,
                updated_at=r.updated_at,
                size_bytes=r.size_bytes,
                compressed_tokens=r.compressed_tokens,
                model_source=r.model_source,
            )
            for r in rows
        ]


def cleanup_expired() -> int:
    now = _now_utc()
    with Session(get_engine()) as session:
        expired = session.execute(
            select(Context).where(Context.expires_at <= now)
        ).scalars().all()
        count = len(expired)
        for ctx in expired:
            session.delete(ctx)
        session.commit()
    return count


def get_handoff(slot_name: str) -> HandoffResult:
    load_context(slot_name=slot_name)  # raises SlotNotFound if missing/expired
    raise AppError(
        "client_decryption_required",
        "A2CR cannot render handoff text server-side for client-encrypted WorkBaton slots. Load through the local stdio MCP wrapper.",
        422,
    )
