from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from services.config import get_web_config
from services.db import acquire_user_mutation_lock, web_transaction
from services.exceptions import AppError, PlanLimitExceeded, SlotNameConflict, SlotNotFound
from services.limits import (
    ensure_hourly_limit,
    get_plan_limits,
    validate_body_size,
    validate_detail_level,
    validate_retention_seconds,
)
from services.logs import build_access_log_row, write_access_log
from services.prompts import build_resume_context_call, build_resume_prompt
from services.tokens import count_tokens, original_tokens_from_length_optional


@dataclass(frozen=True)
class RequestMeta:
    client_type: str = "api"
    request_id: str | None = None
    ip: str | None = None
    user_agent: str | None = None


@dataclass(frozen=True)
class WebSaveResult:
    slot_name: str
    slot_number: int
    expires_at: datetime
    compressed_tokens: int
    saved_tokens: int | None
    resume_context_call: str
    resume_prompt: str


@dataclass(frozen=True)
class WebContextMetadata:
    slot_name: str
    slot_number: int
    expires_at: datetime
    updated_at: datetime
    size_bytes: int
    compressed_tokens: int
    detail_level: str
    model_source: str | None
    load_count: int
    encryption_mode: str = "client"


@dataclass(frozen=True)
class WebLoadResult:
    slot_name: str
    slot_number: int
    content: dict | None
    expires_at: datetime
    compressed_tokens: int
    detail_level: str
    model_source: str | None
    load_count: int
    encrypted_content: dict | None = None
    encryption_mode: str = "client"


@dataclass(frozen=True)
class WebResumeResult:
    mode: str
    context: WebLoadResult | None = None
    candidates: list[WebContextMetadata] | None = None


def _row_to_metadata(row) -> WebContextMetadata:
    return WebContextMetadata(
        slot_name=row.slot_name,
        slot_number=row.slot_number,
        expires_at=row.expires_at,
        updated_at=row.updated_at,
        size_bytes=row.size_bytes,
        compressed_tokens=row.compressed_tokens,
        detail_level=row.detail_level,
        model_source=row.model_source,
        load_count=row.load_count,
        encryption_mode=getattr(row, "encryption_mode", "client") or "client",
    )


def _get_profile(session: Session, user_id: UUID | str) -> tuple[str, int]:
    row = session.execute(
        text(
            """
            SELECT plan, default_retention_seconds
            FROM public.user_profiles
            WHERE user_id = :user_id
            """
        ),
        {"user_id": str(user_id)},
    ).mappings().first()
    if row is None:
        return "free", 86400
    return row["plan"], row["default_retention_seconds"]


def _delete_legacy_contexts(session: Session, user_id: UUID | str) -> None:
    session.execute(
        text(
            """
            DELETE FROM public.contexts
            WHERE user_id = :user_id
              AND encryption_mode <> 'client'
            """
        ),
        {"user_id": str(user_id)},
    )


def _get_existing_context_id(
    session: Session,
    *,
    user_id: UUID | str,
    slot_name: str,
    slot_number: int | None,
) -> str | None:
    by_name = session.execute(
        text(
            """
            SELECT id, slot_number
            FROM public.contexts
            WHERE user_id = :user_id
              AND slot_name = :slot_name
              AND expires_at > now()
              AND encryption_mode = 'client'
            """
        ),
        {"user_id": str(user_id), "slot_name": slot_name},
    ).mappings().first()
    by_number = None
    if slot_number is not None:
        by_number = session.execute(
            text(
                """
                SELECT id, slot_name
                FROM public.contexts
                WHERE user_id = :user_id
                  AND slot_number = :slot_number
                  AND expires_at > now()
                  AND encryption_mode = 'client'
                """
            ),
            {"user_id": str(user_id), "slot_number": slot_number},
        ).mappings().first()

    if by_name is not None and by_number is not None and by_name["id"] != by_number["id"]:
        raise SlotNameConflict()
    if by_number is not None:
        return str(by_number["id"])
    if by_name is not None:
        return str(by_name["id"])
    return None


def _oldest_active_slot(session: Session, *, user_id: UUID | str) -> tuple[str, int] | None:
    row = session.execute(
        text(
            """
            SELECT id, slot_number
            FROM public.contexts
            WHERE user_id = :user_id
              AND expires_at > now()
              AND encryption_mode = 'client'
            ORDER BY updated_at ASC
            LIMIT 1
            """
        ),
        {"user_id": str(user_id)},
    ).mappings().first()
    return (str(row["id"]), int(row["slot_number"])) if row else None


def _next_slot_number(session: Session, *, user_id: UUID | str, active_slots: int) -> int:
    rows = session.execute(
        text(
            """
            SELECT slot_number
            FROM public.contexts
            WHERE user_id = :user_id
              AND expires_at > now()
              AND encryption_mode = 'client'
            """
        ),
        {"user_id": str(user_id)},
    ).scalars().all()
    used = {int(row) for row in rows}
    for candidate in range(1, active_slots + 1):
        if candidate not in used:
            return candidate
    raise PlanLimitExceeded("slot_limit_exceeded", "Active slot limit exceeded")


def _get_context_row(
    session: Session,
    *,
    user_id: UUID | str,
    slot_name: str | None = None,
    slot_number: int | None = None,
):
    if (slot_name is None) == (slot_number is None):
        raise AppError("invalid_slot_selector", "Provide exactly one of slot_name or slot_number", 422)

    selector_sql = "slot_name = :slot_name" if slot_name is not None else "slot_number = :slot_number"
    return session.execute(
        text(
            f"""
            SELECT id, slot_name, slot_number, content, expires_at, compressed_tokens,
                   detail_level, model_source, load_count, encryption_mode
            FROM public.contexts
            WHERE user_id = :user_id
              AND {selector_sql}
              AND expires_at > now()
              AND encryption_mode = 'client'
            """
        ),
        {"user_id": str(user_id), "slot_name": slot_name, "slot_number": slot_number},
    ).mappings().first()


def save_context(
    *,
    user_id: UUID | str,
    slot_name: str,
    content_dict: dict | None,
    encrypted_content: dict | None = None,
    original_length: Optional[int] = None,
    compressed_tokens: Optional[int] = None,
    model_source: Optional[str] = None,
    slot_number: Optional[int] = None,
    retention_seconds: Optional[int] = None,
    detail_level: Optional[str] = None,
    meta: RequestMeta | None = None,
) -> WebSaveResult:
    meta = meta or RequestMeta()
    config = get_web_config()
    if content_dict is not None:
        raise AppError(
            "client_encryption_required",
            "WorkBaton requires client-encrypted encrypted_content; plaintext content is not accepted.",
            422,
        )
    if encrypted_content is None:
        raise AppError("invalid_context_body", "encrypted_content is required", 422)

    encryption_mode = "client"
    body_dict = encrypted_content
    content_json = json.dumps(body_dict, ensure_ascii=False, separators=(",", ":"))
    content_bytes = content_json.encode("utf-8")
    compressed_tokens = compressed_tokens if compressed_tokens is not None else count_tokens(content_json)
    original_tokens = original_tokens_from_length_optional(original_length)
    saved_tokens = (original_tokens - compressed_tokens) if original_tokens is not None else None

    with web_transaction(user_id) as session:
        acquire_user_mutation_lock(session, user_id)
        session.execute(text("SELECT app.expire_contexts()"))
        _delete_legacy_contexts(session, user_id)
        plan, default_retention = _get_profile(session, user_id)
        limits = get_plan_limits(plan)
        if retention_seconds is None:
            retention_seconds = default_retention
        retention_seconds = validate_retention_seconds(retention_seconds, limits)
        detail_level = validate_detail_level(detail_level, limits)
        validate_body_size(len(content_bytes), limits)
        if slot_number is not None and slot_number > limits.active_slots:
            raise AppError("slot_number_not_allowed", "slot_number is not allowed for this plan", 422)

        ensure_hourly_limit(
            session,
            user_id=user_id,
            action="context.save",
            limit=limits.saves_per_hour,
            code="save_rate_limit_exceeded",
        )
        existing_id = _get_existing_context_id(
            session,
            user_id=user_id,
            slot_name=slot_name,
            slot_number=slot_number,
        )
        if existing_id is not None:
            assigned_slot_number = slot_number or session.execute(
                text("SELECT slot_number FROM public.contexts WHERE id = :id AND user_id = :user_id"),
                {"id": existing_id, "user_id": str(user_id)},
            ).scalar_one()
        else:
            try:
                assigned_slot_number = slot_number or _next_slot_number(
                    session, user_id=user_id, active_slots=limits.active_slots
                )
            except PlanLimitExceeded:
                if slot_number is not None:
                    target = session.execute(
                        text(
                            """
                            SELECT id FROM public.contexts
                            WHERE user_id = :user_id
                              AND slot_number = :slot_number
                              AND expires_at > now()
                              AND encryption_mode = 'client'
                            """
                        ),
                        {"user_id": str(user_id), "slot_number": slot_number},
                    ).scalar_one_or_none()
                    if target is None:
                        raise
                    existing_id = str(target)
                    assigned_slot_number = slot_number
                else:
                    oldest = _oldest_active_slot(session, user_id=user_id)
                    if oldest is None:
                        raise
                    existing_id, assigned_slot_number = oldest

        stored_content = content_json
        params = {
            "user_id": str(user_id),
            "slot_name": slot_name,
            "slot_number": assigned_slot_number,
            "content": stored_content,
            "encryption_mode": encryption_mode,
            "encryption_version": 1,
            "encryption_metadata": None,
            "detail_level": detail_level,
            "retention_seconds": retention_seconds,
            "size_bytes": len(content_bytes),
            "original_tokens": original_tokens,
            "compressed_tokens": compressed_tokens,
            "saved_tokens": max(saved_tokens or 0, 0),
            "model_source": model_source,
            "existing_id": existing_id,
        }
        if existing_id is None:
            row = session.execute(
                text(
                    """
                    INSERT INTO public.contexts (
                      user_id, slot_name, slot_number, content, detail_level, expires_at,
                      size_bytes, original_tokens, compressed_tokens, saved_tokens, model_source
                      , encryption_mode, encryption_version, encryption_metadata
                    )
                    VALUES (
                      :user_id, :slot_name, :slot_number, :content, :detail_level,
                      now() + (:retention_seconds * interval '1 second'),
                      :size_bytes, :original_tokens, :compressed_tokens, :saved_tokens, :model_source,
                      :encryption_mode, :encryption_version, CAST(:encryption_metadata AS jsonb)
                    )
                    RETURNING slot_name, slot_number, expires_at
                    """
                ),
                params,
            ).mappings().one()
        else:
            row = session.execute(
                text(
                    """
                    UPDATE public.contexts
                    SET slot_name = :slot_name,
                        slot_number = :slot_number,
                        content = :content,
                        detail_level = :detail_level,
                        expires_at = now() + (:retention_seconds * interval '1 second'),
                        size_bytes = :size_bytes,
                        original_tokens = :original_tokens,
                        compressed_tokens = :compressed_tokens,
                        saved_tokens = :saved_tokens,
                        model_source = :model_source,
                        encryption_mode = :encryption_mode,
                        encryption_version = :encryption_version,
                        encryption_metadata = CAST(:encryption_metadata AS jsonb)
                    WHERE id = :existing_id
                      AND user_id = :user_id
                    RETURNING slot_name, slot_number, expires_at
                    """
                ),
                params,
            ).mappings().one()

        session.execute(
            text("SELECT app.record_context_save(:user_id, :saved_tokens)"),
            {"user_id": str(user_id), "saved_tokens": max(saved_tokens or 0, 0)},
        )
        write_access_log(
            session,
            build_access_log_row(
                user_id=user_id,
                action="context.save",
                slot_name=slot_name,
                client_type=meta.client_type,
                result="success",
                size_bytes=len(content_bytes),
                request_id=meta.request_id,
                ip=meta.ip,
                user_agent=meta.user_agent,
            ),
        )

    return WebSaveResult(
        slot_name=row["slot_name"],
        slot_number=row["slot_number"],
        expires_at=row["expires_at"],
        compressed_tokens=compressed_tokens,
        saved_tokens=saved_tokens,
        resume_context_call=build_resume_context_call(row["slot_name"]),
        resume_prompt=build_resume_prompt(service_url=config.a2cr_service_url, slot_name=row["slot_name"]),
    )


def list_contexts(*, user_id: UUID | str) -> list[WebContextMetadata]:
    with web_transaction(user_id) as session:
        rows = session.execute(
            text(
                """
                SELECT slot_name, slot_number, expires_at, updated_at, size_bytes,
                       compressed_tokens, detail_level, model_source, load_count, encryption_mode
                FROM public.contexts
                WHERE user_id = :user_id
                  AND expires_at > now()
                  AND encryption_mode = 'client'
                ORDER BY slot_number ASC, updated_at DESC
                """
            ),
            {"user_id": str(user_id)},
        ).mappings().all()
    return [_row_to_metadata(row) for row in rows]


def load_context(
    *,
    user_id: UUID | str,
    slot_name: str | None = None,
    slot_number: int | None = None,
    meta: RequestMeta | None = None,
) -> WebLoadResult:
    if (slot_name is None) == (slot_number is None):
        raise AppError("invalid_slot_selector", "Provide exactly one of slot_name or slot_number", 422)

    meta = meta or RequestMeta()
    with web_transaction(user_id) as session:
        plan, _ = _get_profile(session, user_id)
        limits = get_plan_limits(plan)
        ensure_hourly_limit(
            session,
            user_id=user_id,
            action="context.load",
            limit=limits.loads_per_hour,
            code="load_rate_limit_exceeded",
        )
        row = _get_context_row(session, user_id=user_id, slot_name=slot_name, slot_number=slot_number)
        if row is None:
            raise SlotNotFound()

        load_count = session.execute(
            text(
                """
                UPDATE public.contexts
                SET load_count = load_count + 1
                WHERE id = :id
                  AND user_id = :user_id
                RETURNING load_count
                """
            ),
            {"id": row["id"], "user_id": str(user_id)},
        ).scalar_one()
        session.execute(text("SELECT app.record_context_load(:user_id)"), {"user_id": str(user_id)})
        write_access_log(
            session,
            build_access_log_row(
                user_id=user_id,
                action="context.load",
                slot_name=row["slot_name"],
                client_type=meta.client_type,
                result="success",
                request_id=meta.request_id,
                ip=meta.ip,
                user_agent=meta.user_agent,
            ),
        )

    encryption_mode = row["encryption_mode"] or "client"
    if encryption_mode != "client":
        raise AppError(
            "legacy_decryption_disabled",
            "Legacy WorkBaton slots that require server-side decryption are disabled and cannot be loaded.",
            410,
        )
    content = None
    encrypted = json.loads(row["content"])
    return WebLoadResult(
        slot_name=row["slot_name"],
        slot_number=row["slot_number"],
        content=content,
        expires_at=row["expires_at"],
        compressed_tokens=row["compressed_tokens"],
        detail_level=row["detail_level"],
        model_source=row["model_source"],
        load_count=load_count,
        encrypted_content=encrypted,
        encryption_mode=encryption_mode,
    )


def resume_context(
    *,
    user_id: UUID | str,
    slot_name: str | None = None,
    slot_number: int | None = None,
    project: str | None = None,
    prefer_latest: bool = False,
    meta: RequestMeta | None = None,
) -> WebResumeResult:
    if slot_name and slot_number is not None:
        raise AppError("invalid_slot_selector", "Provide only one of slot_name or slot_number", 422)
    if slot_name:
        return WebResumeResult(mode="loaded", context=load_context(user_id=user_id, slot_name=slot_name, meta=meta))
    if slot_number is not None:
        return WebResumeResult(
            mode="loaded",
            context=load_context(user_id=user_id, slot_number=slot_number, meta=meta),
        )
    if not project:
        raise SlotNotFound()

    with web_transaction(user_id) as session:
        rows = session.execute(
            text(
                """
                SELECT slot_name, slot_number, expires_at, updated_at, size_bytes,
                       compressed_tokens, detail_level, model_source, load_count, encryption_mode
                FROM public.contexts
                WHERE user_id = :user_id
                  AND expires_at > now()
                  AND slot_name ILIKE :project_pattern
                  AND encryption_mode = 'client'
                ORDER BY updated_at DESC
                """
            ),
            {"user_id": str(user_id), "project_pattern": f"%{project}%"},
        ).mappings().all()
    candidates = [_row_to_metadata(row) for row in rows]
    if not candidates:
        raise SlotNotFound()
    if len(candidates) == 1 or prefer_latest:
        return WebResumeResult(
            mode="loaded",
            context=load_context(user_id=user_id, slot_name=candidates[0].slot_name, meta=meta),
        )
    return WebResumeResult(mode="candidates", candidates=candidates)


def delete_context(*, user_id: UUID | str, slot_name: str, meta: RequestMeta | None = None) -> None:
    meta = meta or RequestMeta()
    with web_transaction(user_id) as session:
        acquire_user_mutation_lock(session, user_id)
        deleted = session.execute(
            text(
                """
                DELETE FROM public.contexts
                WHERE user_id = :user_id
                  AND slot_name = :slot_name
                RETURNING slot_name
                """
            ),
            {"user_id": str(user_id), "slot_name": slot_name},
        ).scalar_one_or_none()
        if deleted is None:
            raise SlotNotFound()
        session.execute(text("SELECT app.record_context_delete(:user_id)"), {"user_id": str(user_id)})
        write_access_log(
            session,
            build_access_log_row(
                user_id=user_id,
                action="context.delete",
                slot_name=slot_name,
                client_type=meta.client_type,
                result="success",
                request_id=meta.request_id,
                ip=meta.ip,
                user_agent=meta.user_agent,
            ),
        )
