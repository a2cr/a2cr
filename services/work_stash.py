from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text

from services.db import acquire_user_mutation_lock, web_transaction
from services.exceptions import AppError, PlanLimitExceeded
from services.limits import ensure_hourly_limit, get_stash_limits
from services.logs import build_access_log_row, write_access_log
from services.web_context import RequestMeta, _get_profile


@dataclass(frozen=True)
class WorkStashEntry:
    entry_key: str
    encrypted_value: str
    size_bytes: int
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    expires_at: datetime


@dataclass(frozen=True)
class WorkStashEntryMeta:
    entry_key: str
    size_bytes: int
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    expires_at: datetime


@dataclass(frozen=True)
class WorkStashStoreResult:
    entry_key: str
    expires_at: datetime
    size_bytes: int
    quota_used_bytes: int
    quota_bytes: int
    entry_count: int
    entry_limit: int | None


@dataclass(frozen=True)
class WorkStashListResult:
    entries: list[WorkStashEntryMeta]
    total_size_bytes: int
    quota_bytes: int
    entry_count: int
    entry_limit: int | None


_ENTRY_KEY_PATTERN = r"^[A-Za-z0-9_.:-]{1,256}$"


def _validate_entry_key(entry_key: str) -> None:
    import re
    if not re.fullmatch(_ENTRY_KEY_PATTERN[1:-1], entry_key):
        raise AppError(
            "invalid_entry_key",
            "entry_key must match ^[A-Za-z0-9_.:-]{1,256}$",
            422,
        )


def _tags_to_pg(tags: list[str]) -> str:
    # psycopg3 + SQLAlchemy does not auto-adapt Python lists to pg arrays.
    # Format as a PostgreSQL array literal: {"tag1","tag2"}
    escaped = ['"' + t.replace('"', '\\"') + '"' for t in tags]
    return "{" + ",".join(escaped) + "}"


def store_work_stash(
    *,
    user_id: UUID | str,
    entry_key: str,
    encrypted_value: str,
    size_bytes: int,
    tags: list[str] | None = None,
    meta: RequestMeta | None = None,
) -> WorkStashStoreResult:
    meta = meta or RequestMeta()
    tags = tags or []
    _validate_entry_key(entry_key)

    with web_transaction(user_id) as session:
        acquire_user_mutation_lock(session, user_id)
        session.execute(text("SELECT app.expire_work_stash()"))
        plan, _ = _get_profile(session, user_id)
        limits = get_stash_limits(plan)

        if size_bytes > limits.max_entry_bytes:
            raise AppError(
                "entry_too_large",
                f"Entry exceeds {limits.max_entry_bytes // 1024}KB per-entry limit for this plan",
                413,
            )

        ensure_hourly_limit(
            session,
            user_id=user_id,
            action="work_stash.store",
            limit=limits.writes_per_hour,
            code="stash_write_rate_limit_exceeded",
        )

        existing = session.execute(
            text(
                """
                SELECT id, size_bytes
                FROM public.work_stash_entries
                WHERE user_id = :user_id AND entry_key = :entry_key
                """
            ),
            {"user_id": str(user_id), "entry_key": entry_key},
        ).mappings().first()

        quota_row = session.execute(
            text(
                """
                SELECT COALESCE(SUM(size_bytes), 0) AS used_bytes, COUNT(*) AS entry_count
                FROM public.work_stash_entries
                WHERE user_id = :user_id AND expires_at > now()
                """
            ),
            {"user_id": str(user_id)},
        ).mappings().one()

        current_used = int(quota_row["used_bytes"])
        current_count = int(quota_row["entry_count"])
        existing_size = int(existing["size_bytes"]) if existing else 0
        projected_used = current_used - existing_size + size_bytes

        if projected_used > limits.quota_bytes:
            raise PlanLimitExceeded(
                "stash_quota_exceeded",
                f"WorkStash quota exceeded. Used {current_used} / {limits.quota_bytes} bytes.",
            )

        if limits.max_entries is not None and existing is None and current_count >= limits.max_entries:
            raise PlanLimitExceeded(
                "stash_entry_limit_exceeded",
                f"WorkStash entry limit of {limits.max_entries} reached for this plan.",
            )

        if existing is not None:
            row = session.execute(
                text(
                    """
                    UPDATE public.work_stash_entries
                    SET encrypted_value = :encrypted_value,
                        size_bytes = :size_bytes,
                        tags = CAST(:tags AS text[]),
                        expires_at = now() + (:ttl_seconds * interval '1 second')
                    WHERE user_id = :user_id AND entry_key = :entry_key
                    RETURNING entry_key, expires_at, size_bytes
                    """
                ),
                {
                    "user_id": str(user_id),
                    "entry_key": entry_key,
                    "encrypted_value": encrypted_value,
                    "size_bytes": size_bytes,
                    "tags": _tags_to_pg(tags),
                    "ttl_seconds": limits.ttl_seconds,
                },
            ).mappings().one()
        else:
            row = session.execute(
                text(
                    """
                    INSERT INTO public.work_stash_entries
                      (user_id, entry_key, encrypted_value, size_bytes, tags, expires_at)
                    VALUES
                      (:user_id, :entry_key, :encrypted_value, :size_bytes,
                       CAST(:tags AS text[]), now() + (:ttl_seconds * interval '1 second'))
                    RETURNING entry_key, expires_at, size_bytes
                    """
                ),
                {
                    "user_id": str(user_id),
                    "entry_key": entry_key,
                    "encrypted_value": encrypted_value,
                    "size_bytes": size_bytes,
                    "tags": _tags_to_pg(tags),
                    "ttl_seconds": limits.ttl_seconds,
                },
            ).mappings().one()

        write_access_log(
            session,
            build_access_log_row(
                user_id=user_id,
                action="work_stash.store",
                slot_name=entry_key,
                client_type=meta.client_type,
                result="success",
                size_bytes=size_bytes,
                request_id=meta.request_id,
                ip=meta.ip,
                user_agent=meta.user_agent,
            ),
        )

    return WorkStashStoreResult(
        entry_key=row["entry_key"],
        expires_at=row["expires_at"],
        size_bytes=row["size_bytes"],
        quota_used_bytes=projected_used,
        quota_bytes=limits.quota_bytes,
        entry_count=current_count if existing else current_count + 1,
        entry_limit=limits.max_entries,
    )


def get_work_stash(
    *,
    user_id: UUID | str,
    entry_key: str,
    meta: RequestMeta | None = None,
) -> WorkStashEntry:
    meta = meta or RequestMeta()
    _validate_entry_key(entry_key)

    with web_transaction(user_id) as session:
        plan, _ = _get_profile(session, user_id)
        limits = get_stash_limits(plan)
        ensure_hourly_limit(
            session,
            user_id=user_id,
            action="work_stash.get",
            limit=limits.reads_per_hour,
            code="stash_read_rate_limit_exceeded",
        )
        row = session.execute(
            text(
                """
                SELECT entry_key, encrypted_value, size_bytes, tags,
                       created_at, updated_at, expires_at
                FROM public.work_stash_entries
                WHERE user_id = :user_id AND entry_key = :entry_key AND expires_at > now()
                """
            ),
            {"user_id": str(user_id), "entry_key": entry_key},
        ).mappings().first()

        if row is None:
            raise AppError("stash_entry_not_found", "WorkStash entry not found or expired", 404)

        session.execute(
            text(
                """
                UPDATE public.work_stash_entries
                SET last_accessed_at = now()
                WHERE user_id = :user_id AND entry_key = :entry_key
                """
            ),
            {"user_id": str(user_id), "entry_key": entry_key},
        )

        write_access_log(
            session,
            build_access_log_row(
                user_id=user_id,
                action="work_stash.get",
                slot_name=entry_key,
                client_type=meta.client_type,
                result="success",
                request_id=meta.request_id,
                ip=meta.ip,
                user_agent=meta.user_agent,
            ),
        )

    return WorkStashEntry(
        entry_key=row["entry_key"],
        encrypted_value=row["encrypted_value"],
        size_bytes=row["size_bytes"],
        tags=list(row["tags"] or []),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        expires_at=row["expires_at"],
    )


def list_work_stash(
    *,
    user_id: UUID | str,
    tag_filter: list[str] | None = None,
) -> WorkStashListResult:
    with web_transaction(user_id) as session:
        plan, _ = _get_profile(session, user_id)
        limits = get_stash_limits(plan)

        if tag_filter:
            rows = session.execute(
                text(
                    """
                    SELECT entry_key, size_bytes, tags, created_at, updated_at, expires_at
                    FROM public.work_stash_entries
                    WHERE user_id = :user_id AND expires_at > now()
                      AND tags && CAST(:tags AS text[])
                    ORDER BY updated_at DESC
                    """
                ),
                {"user_id": str(user_id), "tags": _tags_to_pg(tag_filter)},
            ).mappings().all()
        else:
            rows = session.execute(
                text(
                    """
                    SELECT entry_key, size_bytes, tags, created_at, updated_at, expires_at
                    FROM public.work_stash_entries
                    WHERE user_id = :user_id AND expires_at > now()
                    ORDER BY updated_at DESC
                    """
                ),
                {"user_id": str(user_id)},
            ).mappings().all()

        total_size = sum(int(r["size_bytes"]) for r in rows)
        entries = [
            WorkStashEntryMeta(
                entry_key=r["entry_key"],
                size_bytes=r["size_bytes"],
                tags=list(r["tags"] or []),
                created_at=r["created_at"],
                updated_at=r["updated_at"],
                expires_at=r["expires_at"],
            )
            for r in rows
        ]

    return WorkStashListResult(
        entries=entries,
        total_size_bytes=total_size,
        quota_bytes=limits.quota_bytes,
        entry_count=len(entries),
        entry_limit=limits.max_entries,
    )


def delete_work_stash(
    *,
    user_id: UUID | str,
    entry_key: str,
    meta: RequestMeta | None = None,
) -> None:
    meta = meta or RequestMeta()
    _validate_entry_key(entry_key)

    with web_transaction(user_id) as session:
        acquire_user_mutation_lock(session, user_id)
        deleted = session.execute(
            text(
                """
                DELETE FROM public.work_stash_entries
                WHERE user_id = :user_id AND entry_key = :entry_key
                RETURNING entry_key
                """
            ),
            {"user_id": str(user_id), "entry_key": entry_key},
        ).scalar_one_or_none()

        if deleted is None:
            raise AppError("stash_entry_not_found", "WorkStash entry not found or expired", 404)

        write_access_log(
            session,
            build_access_log_row(
                user_id=user_id,
                action="work_stash.delete",
                slot_name=entry_key,
                client_type=meta.client_type,
                result="success",
                request_id=meta.request_id,
                ip=meta.ip,
                user_agent=meta.user_agent,
            ),
        )


def delete_all_work_stash(
    *,
    user_id: UUID | str,
    meta: RequestMeta | None = None,
) -> int:
    meta = meta or RequestMeta()

    with web_transaction(user_id) as session:
        acquire_user_mutation_lock(session, user_id)
        count = session.execute(
            text(
                """
                WITH deleted AS (
                    DELETE FROM public.work_stash_entries
                    WHERE user_id = :user_id
                    RETURNING 1
                )
                SELECT count(*) FROM deleted
                """
            ),
            {"user_id": str(user_id)},
        ).scalar_one()

        if int(count) > 0:
            write_access_log(
                session,
                build_access_log_row(
                    user_id=user_id,
                    action="work_stash.delete_all",
                    slot_name=None,
                    client_type=meta.client_type,
                    result="success",
                    request_id=meta.request_id,
                    ip=meta.ip,
                    user_agent=meta.user_agent,
                ),
            )

    return int(count)
