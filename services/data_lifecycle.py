from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text

from services.db import web_transaction
from services.limits import FREE_LIMITS


ACCOUNT_DELETE_TABLES = (
    "work_thread_runs",
    "work_thread_tasks",
    "work_thread_messages",
    "work_threads",
    "access_logs",
    "api_keys",
    "contexts",
    "stats",
    "user_profiles",
)


@dataclass(frozen=True)
class DowngradeToFreeDryRun:
    user_id: str
    active_contexts: int
    active_slot_limit: int
    contexts_over_slot_limit: int
    oversized_contexts: int
    detailed_contexts: int
    pro_retention_contexts: int
    old_access_logs: int
    profile_updates_needed: int
    would_delete_rows: bool = False


@dataclass(frozen=True)
class AccountDeleteDryRun:
    user_id: str
    table_counts: dict[str, int]
    total_rows: int
    dry_run: bool = True


def _int(row, key: str) -> int:
    return int(row[key] or 0)


def downgrade_to_free_dry_run(*, user_id: UUID | str) -> DowngradeToFreeDryRun:
    with web_transaction(user_id) as session:
        row = session.execute(
            text(
                """
                SELECT
                  (
                    SELECT count(*)
                    FROM public.contexts
                    WHERE user_id = :user_id
                      AND expires_at > now()
                      AND encryption_mode = 'client'
                  ) AS active_contexts,
                  (
                    SELECT count(*)
                    FROM public.contexts
                    WHERE user_id = :user_id
                      AND expires_at > now()
                      AND encryption_mode = 'client'
                      AND slot_number > :active_slot_limit
                  ) AS contexts_over_slot_limit,
                  (
                    SELECT count(*)
                    FROM public.contexts
                    WHERE user_id = :user_id
                      AND expires_at > now()
                      AND encryption_mode = 'client'
                      AND size_bytes > :max_body_bytes
                  ) AS oversized_contexts,
                  (
                    SELECT count(*)
                    FROM public.contexts
                    WHERE user_id = :user_id
                      AND expires_at > now()
                      AND encryption_mode = 'client'
                      AND detail_level <> 'compact'
                  ) AS detailed_contexts,
                  (
                    SELECT count(*)
                    FROM public.contexts
                    WHERE user_id = :user_id
                      AND expires_at > now()
                      AND encryption_mode = 'client'
                      AND expires_at > now() + (:max_retention_seconds * interval '1 second')
                  ) AS pro_retention_contexts,
                  (
                    SELECT count(*)
                    FROM public.access_logs
                    WHERE user_id = :user_id
                      AND created_at < now() - (:access_log_retention_seconds * interval '1 second')
                  ) AS old_access_logs,
                  (
                    SELECT count(*)
                    FROM public.user_profiles
                    WHERE user_id = :user_id
                      AND (
                        plan <> 'free'
                        OR context_detail_level <> 'compact'
                        OR default_retention_seconds > :max_retention_seconds
                      )
                  ) AS profile_updates_needed
                """
            ),
            {
                "user_id": str(user_id),
                "active_slot_limit": FREE_LIMITS.active_slots,
                "max_body_bytes": FREE_LIMITS.max_body_bytes,
                "max_retention_seconds": max(FREE_LIMITS.allowed_retention_seconds),
                "access_log_retention_seconds": FREE_LIMITS.access_log_retention_seconds,
            },
        ).mappings().one()

    return DowngradeToFreeDryRun(
        user_id=str(user_id),
        active_contexts=_int(row, "active_contexts"),
        active_slot_limit=FREE_LIMITS.active_slots,
        contexts_over_slot_limit=_int(row, "contexts_over_slot_limit"),
        oversized_contexts=_int(row, "oversized_contexts"),
        detailed_contexts=_int(row, "detailed_contexts"),
        pro_retention_contexts=_int(row, "pro_retention_contexts"),
        old_access_logs=_int(row, "old_access_logs"),
        profile_updates_needed=_int(row, "profile_updates_needed"),
    )


def _count_user_owned_rows(*, user_id: UUID | str) -> AccountDeleteDryRun:
    select_list = ",\n".join(
        f"(SELECT count(*) FROM public.{table_name} WHERE user_id = :user_id) AS {table_name}"
        for table_name in ACCOUNT_DELETE_TABLES
    )
    with web_transaction(user_id) as session:
        row = session.execute(text(f"SELECT {select_list}"), {"user_id": str(user_id)}).mappings().one()

    table_counts = {table_name: _int(row, table_name) for table_name in ACCOUNT_DELETE_TABLES}
    return AccountDeleteDryRun(
        user_id=str(user_id),
        table_counts=table_counts,
        total_rows=sum(table_counts.values()),
    )


def account_delete_dry_run(*, user_id: UUID | str) -> AccountDeleteDryRun:
    return _count_user_owned_rows(user_id=user_id)


def account_delete_orphan_scan(*, user_id: UUID | str) -> AccountDeleteDryRun:
    return _count_user_owned_rows(user_id=user_id)
