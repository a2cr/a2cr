from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text

from services.auth import hash_api_key
from services.config import get_web_config
from services.db import web_transaction
from services.exceptions import DetailLevelNotAllowed, RetentionNotAllowed
from services.limits import get_plan_limits, validate_detail_level, validate_retention_seconds
from services.prompts import build_resume_context_call, build_resume_prompt


@dataclass(frozen=True)
class DashboardProfile:
    user_id: str
    plan: str
    context_detail_level: str
    default_retention_seconds: int
    preferred_locale: str
    response_language: str
    timezone: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class DashboardContext:
    slot_name: str
    slot_number: int
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    size_bytes: int
    compressed_tokens: int
    saved_tokens: int
    detail_level: str
    model_source: str | None
    load_count: int
    resume_context_call: str
    resume_prompt: str
    encryption_mode: str = "client"


@dataclass(frozen=True)
class DashboardStats:
    total_saves: int
    total_loads: int
    total_deletes: int
    total_tokens_saved: int
    active_slots: int


@dataclass(frozen=True)
class DashboardAccessLog:
    action: str
    slot_name: str | None
    client_type: str
    result: str
    error_code: str | None
    size_bytes: int | None
    request_id: str | None
    created_at: datetime


@dataclass(frozen=True)
class DashboardApiKey:
    key_prefix: str
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None


@dataclass(frozen=True)
class CreatedApiKey:
    api_key: str
    key_prefix: str
    created_at: datetime


def _profile_from_row(row) -> DashboardProfile:
    return DashboardProfile(
        user_id=str(row.user_id),
        plan=row.plan,
        context_detail_level=row.context_detail_level,
        default_retention_seconds=row.default_retention_seconds,
        preferred_locale=row.preferred_locale,
        response_language=row.response_language,
        timezone=row.timezone,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def get_profile(user_id: UUID | str) -> DashboardProfile:
    with web_transaction(user_id) as session:
        session.execute(
            text(
                """
                INSERT INTO public.user_profiles (user_id)
                VALUES (:user_id)
                ON CONFLICT (user_id) DO NOTHING
                """
            ),
            {"user_id": str(user_id)},
        )
        row = session.execute(
            text(
                """
                SELECT user_id, plan, context_detail_level, default_retention_seconds,
                       preferred_locale, response_language, timezone, created_at, updated_at
                FROM public.user_profiles
                WHERE user_id = :user_id
                """
            ),
            {"user_id": str(user_id)},
        ).mappings().one()
    return _profile_from_row(row)


def update_profile(
    *,
    user_id: UUID | str,
    context_detail_level: str | None = None,
    default_retention_seconds: int | None = None,
    preferred_locale: str | None = None,
    response_language: str | None = None,
    timezone: str | None = None,
) -> DashboardProfile:
    current = get_profile(user_id)
    limits = get_plan_limits(current.plan)
    detail = context_detail_level or current.context_detail_level
    retention = default_retention_seconds or current.default_retention_seconds
    try:
        validate_detail_level(detail, limits)
    except DetailLevelNotAllowed:
        raise
    try:
        validate_retention_seconds(retention, limits)
    except RetentionNotAllowed:
        raise

    with web_transaction(user_id) as session:
        row = session.execute(
            text(
                """
                UPDATE public.user_profiles
                SET context_detail_level = :context_detail_level,
                    default_retention_seconds = :default_retention_seconds,
                    preferred_locale = :preferred_locale,
                    response_language = :response_language,
                    timezone = :timezone
                WHERE user_id = :user_id
                RETURNING user_id, plan, context_detail_level, default_retention_seconds,
                          preferred_locale, response_language, timezone, created_at, updated_at
                """
            ),
            {
                "user_id": str(user_id),
                "context_detail_level": detail,
                "default_retention_seconds": retention,
                "preferred_locale": preferred_locale or current.preferred_locale,
                "response_language": response_language or current.response_language,
                "timezone": timezone or current.timezone,
            },
        ).mappings().one()
    return _profile_from_row(row)


def list_contexts(user_id: UUID | str) -> list[DashboardContext]:
    config = get_web_config()
    with web_transaction(user_id) as session:
        rows = session.execute(
            text(
                """
                SELECT slot_name, slot_number, created_at, updated_at, expires_at,
                       size_bytes, compressed_tokens, saved_tokens, detail_level,
                       model_source, load_count, encryption_mode
                FROM public.contexts
                WHERE user_id = :user_id
                  AND expires_at > now()
                  AND encryption_mode = 'client'
                ORDER BY slot_number ASC, updated_at DESC
                """
            ),
            {"user_id": str(user_id)},
        ).mappings().all()
    return [
        DashboardContext(
            slot_name=row.slot_name,
            slot_number=row.slot_number,
            created_at=row.created_at,
            updated_at=row.updated_at,
            expires_at=row.expires_at,
            size_bytes=row.size_bytes,
            compressed_tokens=row.compressed_tokens,
            saved_tokens=row.saved_tokens,
            detail_level=row.detail_level,
            model_source=row.model_source,
            load_count=row.load_count,
            resume_context_call=build_resume_context_call(row.slot_name),
            resume_prompt=build_resume_prompt(service_url=config.a2cr_service_url, slot_name=row.slot_name),
            encryption_mode=row.encryption_mode,
        )
        for row in rows
    ]


def get_stats(user_id: UUID | str) -> DashboardStats:
    with web_transaction(user_id) as session:
        row = session.execute(
            text(
                """
                SELECT s.total_saves, s.total_loads, s.total_deletes, s.total_tokens_saved,
                       (
                         SELECT count(*)
                         FROM public.contexts c
                         WHERE c.user_id = :user_id
                           AND c.expires_at > now()
                           AND c.encryption_mode = 'client'
                       ) AS active_slots
                FROM public.stats s
                WHERE s.user_id = :user_id
                """
            ),
            {"user_id": str(user_id)},
        ).mappings().first()
    if row is None:
        return DashboardStats(0, 0, 0, 0, 0)
    return DashboardStats(
        total_saves=row.total_saves,
        total_loads=row.total_loads,
        total_deletes=row.total_deletes,
        total_tokens_saved=row.total_tokens_saved,
        active_slots=row.active_slots,
    )


def list_access_logs(user_id: UUID | str, limit: int = 100) -> list[DashboardAccessLog]:
    safe_limit = min(max(limit, 1), 100)
    with web_transaction(user_id) as session:
        rows = session.execute(
            text(
                """
                SELECT action, slot_name, client_type, result, error_code,
                       size_bytes, request_id, created_at
                FROM public.access_logs
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            {"user_id": str(user_id), "limit": safe_limit},
        ).mappings().all()
    return [
        DashboardAccessLog(
            action=row.action,
            slot_name=row.slot_name,
            client_type=row.client_type,
            result=row.result,
            error_code=row.error_code,
            size_bytes=row.size_bytes,
            request_id=row.request_id,
            created_at=row.created_at,
        )
        for row in rows
    ]


def get_api_key(user_id: UUID | str) -> DashboardApiKey | None:
    with web_transaction(user_id) as session:
        row = session.execute(
            text(
                """
                SELECT key_prefix, created_at, last_used_at, revoked_at
                FROM public.api_keys
                WHERE user_id = :user_id
                """
            ),
            {"user_id": str(user_id)},
        ).mappings().first()
    if row is None:
        return None
    return DashboardApiKey(
        key_prefix=row.key_prefix,
        created_at=row.created_at,
        last_used_at=row.last_used_at,
        revoked_at=row.revoked_at,
    )


def create_api_key(user_id: UUID | str) -> CreatedApiKey:
    config = get_web_config()
    api_key = f"{config.public_api_key_prefix}-{secrets.token_urlsafe(32)}"
    key_prefix = api_key[:12]
    key_hash = hash_api_key(api_key, config.api_key_hash_secret)
    with web_transaction(user_id) as session:
        row = session.execute(
            text(
                """
                INSERT INTO public.api_keys (user_id, key_hash, key_prefix, revoked_at)
                VALUES (:user_id, :key_hash, :key_prefix, NULL)
                ON CONFLICT (user_id) DO UPDATE
                SET key_hash = EXCLUDED.key_hash,
                    key_prefix = EXCLUDED.key_prefix,
                    created_at = now(),
                    last_used_at = NULL,
                    last_used_ip_hash = NULL,
                    revoked_at = NULL
                RETURNING key_prefix, created_at
                """
            ),
            {"user_id": str(user_id), "key_hash": key_hash, "key_prefix": key_prefix},
        ).mappings().one()
    return CreatedApiKey(api_key=api_key, key_prefix=row.key_prefix, created_at=row.created_at)


def revoke_api_key(user_id: UUID | str) -> None:
    with web_transaction(user_id) as session:
        session.execute(
            text(
                """
                UPDATE public.api_keys
                SET revoked_at = now()
                WHERE user_id = :user_id
                  AND revoked_at IS NULL
                """
            ),
            {"user_id": str(user_id)},
        )
