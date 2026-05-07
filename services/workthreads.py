from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text

from services.config import get_web_config
from services.crypto import decrypt, encrypt
from services.db import web_transaction
from services.exceptions import AppError
from services.web_context import RequestMeta
import services.web_context as web_context_service


FINAL_MESSAGE_TYPES = {"decision", "handoff", "blocked", "result"}
MAX_CONSULTATION_MESSAGES = 6
MAX_CONSULTATION_QUESTIONS = 3
MAX_UNRESOLVED_QUESTIONS = 3
MAX_REPEATED_WAITS = 3


@dataclass(frozen=True)
class WorkThread:
    thread_id: str
    title: str
    purpose: str | None
    status: str
    loop_status: str
    final_slot_name: str | None
    message_count: int
    task_count: int
    task_status_counts: dict[str, int]
    agent_names: list[str]
    last_activity_at: datetime
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class WorkThreadMessage:
    message_id: str
    thread_id: str
    message_type: str
    content: dict
    consultation_id: str | None
    requires_response: bool
    target_agent_name: str | None
    agent_name: str | None
    created_at: datetime
    loop_warning: str | None = None


@dataclass(frozen=True)
class WorkThreadTask:
    task_id: str
    thread_id: str
    title: str
    status: str
    lease_owner: str | None
    lease_expires_at: datetime | None
    result_message_id: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class WorkThreadResult:
    thread_id: str
    final_slot_name: str
    resume_context_call: str
    resume_prompt: str


@dataclass(frozen=True)
class WorkThreadUpdateCheck:
    thread_id: str
    has_updates: bool
    message_count: int
    latest_message_at: datetime | None


def _content_hash(content_dict: dict) -> str:
    canonical = json.dumps(content_dict, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _ensure_pro(session, user_id: UUID | str) -> None:
    plan = session.execute(
        text("SELECT plan FROM public.user_profiles WHERE user_id = :user_id"),
        {"user_id": str(user_id)},
    ).scalar_one_or_none() or "free"
    if plan != "pro":
        raise AppError("pro_plan_required", "WorkThreads require a Pro plan", 403)


def _thread_row_to_model(row) -> WorkThread:
    agent_names = row.agent_names or []
    task_status_counts = row.task_status_counts or {}
    return WorkThread(
        thread_id=str(row.thread_id),
        title=row.title,
        purpose=row.purpose,
        status=row.status,
        loop_status=row.loop_status,
        final_slot_name=row.final_slot_name,
        message_count=row.message_count,
        task_count=row.task_count,
        task_status_counts=dict(task_status_counts),
        agent_names=list(agent_names),
        last_activity_at=row.last_activity_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _thread_select_sql(where_clause: str) -> str:
    return f"""
        SELECT wt.id AS thread_id, wt.title, wt.purpose, wt.status, wt.loop_status, wt.final_slot_name,
               wt.created_at, wt.updated_at,
               COALESCE(count(DISTINCT wtm.id), 0) AS message_count,
               COALESCE(count(DISTINCT wtt.id), 0) AS task_count,
               COALESCE(
                 (
                   SELECT jsonb_object_agg(status_counts.status, status_counts.status_count)
                   FROM (
                     SELECT status, count(*) AS status_count
                     FROM public.work_thread_tasks
                     WHERE thread_id = wt.id
                     GROUP BY status
                   ) status_counts
                 ),
                 '{{}}'::jsonb
               ) AS task_status_counts,
               COALESCE(array_remove(array_agg(DISTINCT wtm.agent_name), NULL), ARRAY[]::text[]) AS agent_names,
               GREATEST(
                 wt.updated_at,
                 COALESCE(max(wtm.created_at), wt.updated_at),
                 COALESCE(max(wtt.updated_at), wt.updated_at)
               ) AS last_activity_at
        FROM public.work_threads wt
        LEFT JOIN public.work_thread_messages wtm ON wtm.thread_id = wt.id
        LEFT JOIN public.work_thread_tasks wtt ON wtt.thread_id = wt.id
        WHERE {where_clause}
        GROUP BY wt.id
    """


def create_workthread(
    *,
    user_id: UUID | str,
    title: str,
    purpose: str | None = None,
    initial_message: dict | None = None,
    agent_name: str | None = None,
    idempotency_key: str | None = None,
) -> WorkThread:
    with web_transaction(user_id) as session:
        _ensure_pro(session, user_id)
        row = session.execute(
            text(
                """
                INSERT INTO public.work_threads (user_id, title, purpose)
                VALUES (:user_id, :title, :purpose)
                RETURNING id
                """
            ),
            {"user_id": str(user_id), "title": title, "purpose": purpose},
        ).mappings().one()
        thread_id = str(row.id)
        if initial_message is not None:
            _insert_message(
                session,
                user_id=user_id,
                thread_id=thread_id,
                content_dict=initial_message,
                message_type="note",
                agent_name=agent_name,
                idempotency_key=idempotency_key,
            )
        return _thread_row_to_model(
            session.execute(
                text(_thread_select_sql("wt.user_id = :user_id AND wt.id = :thread_id")),
                {"user_id": str(user_id), "thread_id": thread_id},
            ).mappings().one()
        )


def list_workthreads(*, user_id: UUID | str) -> list[WorkThread]:
    with web_transaction(user_id) as session:
        _ensure_pro(session, user_id)
        rows = session.execute(
            text(_thread_select_sql("wt.user_id = :user_id") + " ORDER BY last_activity_at DESC"),
            {"user_id": str(user_id)},
        ).mappings().all()
    return [_thread_row_to_model(row) for row in rows]


def _insert_message(
    session,
    *,
    user_id: UUID | str,
    thread_id: str,
    content_dict: dict,
    message_type: str,
    parent_message_id: str | None = None,
    consultation_id: str | None = None,
    requires_response: bool = False,
    target_agent_name: str | None = None,
    response_deadline: datetime | None = None,
    idempotency_key: str | None = None,
    agent_name: str | None = None,
):
    config = get_web_config()
    content_json = json.dumps(content_dict, ensure_ascii=False, separators=(",", ":"))
    content_hash = _content_hash(content_dict)
    loop_warning = _enforce_loop_guard(
        session,
        user_id=user_id,
        thread_id=thread_id,
        content_hash=content_hash,
        message_type=message_type,
        consultation_id=consultation_id,
        requires_response=requires_response,
        idempotency_key=idempotency_key,
    )
    row = session.execute(
        text(
            """
            INSERT INTO public.work_thread_messages (
              thread_id, user_id, content, content_hash, message_type, parent_message_id,
              consultation_id, requires_response, target_agent_name, response_deadline,
              idempotency_key, agent_name
            )
            VALUES (
              :thread_id, :user_id, :content, :content_hash, :message_type, :parent_message_id,
              :consultation_id, :requires_response, :target_agent_name, :response_deadline,
              :idempotency_key, :agent_name
            )
            RETURNING id, thread_id, message_type, content, consultation_id, requires_response,
                      target_agent_name, agent_name, created_at
            """
        ),
        {
            "thread_id": thread_id,
            "user_id": str(user_id),
            "content": encrypt(content_json, config.fernet_key),
            "content_hash": content_hash,
            "message_type": message_type,
            "parent_message_id": parent_message_id,
            "consultation_id": consultation_id,
            "requires_response": requires_response,
            "target_agent_name": target_agent_name,
            "response_deadline": response_deadline,
            "idempotency_key": idempotency_key,
            "agent_name": agent_name,
        },
    ).mappings().one()
    session.execute(
        text("UPDATE public.work_threads SET updated_at = now() WHERE id = :thread_id AND user_id = :user_id"),
        {"thread_id": thread_id, "user_id": str(user_id)},
    )
    return row, loop_warning


def _enforce_loop_guard(
    session,
    *,
    user_id: UUID | str,
    thread_id: str,
    content_hash: str,
    message_type: str,
    consultation_id: str | None,
    requires_response: bool,
    idempotency_key: str | None,
) -> str | None:
    loop_status = session.execute(
        text(
            """
            SELECT loop_status
            FROM public.work_threads
            WHERE id = :thread_id
              AND user_id = :user_id
            FOR UPDATE
            """
        ),
        {"thread_id": thread_id, "user_id": str(user_id)},
    ).scalar_one_or_none()
    if loop_status == "blocked" and message_type not in FINAL_MESSAGE_TYPES:
        raise AppError("loop_guard_triggered", "Only decision, handoff, blocked, or result messages are allowed", 409)

    duplicate = session.execute(
        text(
            """
            SELECT 1
            FROM public.work_thread_messages
            WHERE thread_id = :thread_id
              AND (
                content_hash = :content_hash OR
                (:idempotency_key IS NOT NULL AND idempotency_key = :idempotency_key)
              )
            LIMIT 1
            """
        ),
        {"thread_id": thread_id, "content_hash": content_hash, "idempotency_key": idempotency_key},
    ).scalar_one_or_none()
    if duplicate is not None:
        raise AppError("duplicate_workthread_message", "Duplicate WorkThread message", 409)

    if message_type in FINAL_MESSAGE_TYPES:
        return None

    warning = None
    unresolved = session.execute(
        text(
            """
            SELECT count(*)
            FROM public.work_thread_messages
            WHERE thread_id = :thread_id
              AND requires_response = true
            """
        ),
        {"thread_id": thread_id},
    ).scalar_one()
    if requires_response and unresolved >= MAX_UNRESOLVED_QUESTIONS:
        _block_loop(session, user_id=user_id, thread_id=thread_id, reason="unresolved_questions")
        raise AppError("loop_guard_triggered", "Too many unresolved WorkThread questions", 409)
    if requires_response and unresolved == MAX_UNRESOLVED_QUESTIONS - 1:
        warning = "unresolved_question_limit_approaching"

    if consultation_id:
        stats = session.execute(
            text(
                """
                SELECT count(*) AS message_count,
                       count(*) FILTER (WHERE message_type IN ('question', 'answer')) AS qa_count,
                       count(*) FILTER (WHERE message_type = 'question') AS question_count
                FROM public.work_thread_messages
                WHERE thread_id = :thread_id
                  AND consultation_id = :consultation_id
                """
            ),
            {"thread_id": thread_id, "consultation_id": consultation_id},
        ).mappings().one()
        if stats.message_count >= MAX_CONSULTATION_MESSAGES or stats.question_count >= MAX_CONSULTATION_QUESTIONS:
            _block_loop(session, user_id=user_id, thread_id=thread_id, reason="consultation_limit")
            raise AppError("loop_guard_triggered", "WorkThread consultation limit reached", 409)
        if stats.message_count >= MAX_CONSULTATION_MESSAGES - 1 or stats.question_count >= MAX_CONSULTATION_QUESTIONS - 1:
            warning = warning or "consultation_limit_approaching"

    if warning:
        session.execute(
            text(
                """
                UPDATE public.work_threads
                SET loop_status = 'warning'
                WHERE id = :thread_id
                  AND user_id = :user_id
                  AND loop_status = 'ok'
                """
            ),
            {"thread_id": thread_id, "user_id": str(user_id)},
        )
    return warning


def _block_loop(session, *, user_id: UUID | str, thread_id: str, reason: str) -> None:
    session.execute(
        text(
            """
            UPDATE public.work_threads
            SET loop_status = 'blocked'
            WHERE id = :thread_id
              AND user_id = :user_id
            """
        ),
        {"thread_id": thread_id, "user_id": str(user_id)},
    )
    session.execute(
        text(
            """
            INSERT INTO public.work_thread_runs (thread_id, user_id, status, reason)
            VALUES (:thread_id, :user_id, 'failed', :reason)
            """
        ),
        {"thread_id": thread_id, "user_id": str(user_id), "reason": reason},
    )


def post_workthread_message(
    *,
    user_id: UUID | str,
    thread_id: str,
    content_dict: dict,
    message_type: str = "note",
    parent_message_id: str | None = None,
    consultation_id: str | None = None,
    requires_response: bool = False,
    target_agent_name: str | None = None,
    response_deadline: datetime | None = None,
    idempotency_key: str | None = None,
    agent_name: str | None = None,
) -> WorkThreadMessage:
    with web_transaction(user_id) as session:
        _ensure_pro(session, user_id)
        exists = session.execute(
            text("SELECT 1 FROM public.work_threads WHERE id = :thread_id AND user_id = :user_id"),
            {"thread_id": thread_id, "user_id": str(user_id)},
        ).scalar_one_or_none()
        if exists is None:
            raise AppError("workthread_not_found", "WorkThread not found", 404)
        row, loop_warning = _insert_message(
            session,
            user_id=user_id,
            thread_id=thread_id,
            content_dict=content_dict,
            message_type=message_type,
            parent_message_id=parent_message_id,
            consultation_id=consultation_id,
            requires_response=requires_response,
            target_agent_name=target_agent_name,
            response_deadline=response_deadline,
            idempotency_key=idempotency_key,
            agent_name=agent_name,
        )
    return _message_row_to_model(row, loop_warning=loop_warning)


def _message_row_to_model(row, *, loop_warning: str | None = None) -> WorkThreadMessage:
    content = json.loads(decrypt(row.content, get_web_config().fernet_key))
    return WorkThreadMessage(
        message_id=str(row.id),
        thread_id=str(row.thread_id),
        message_type=row.message_type,
        content=content,
        consultation_id=row.consultation_id,
        requires_response=row.requires_response,
        target_agent_name=row.target_agent_name,
        agent_name=row.agent_name,
        created_at=row.created_at,
        loop_warning=loop_warning,
    )


def read_workthread(*, user_id: UUID | str, thread_id: str, limit: int = 100) -> list[WorkThreadMessage]:
    safe_limit = min(max(limit, 1), 200)
    with web_transaction(user_id) as session:
        _ensure_pro(session, user_id)
        rows = session.execute(
            text(
                """
                SELECT id, thread_id, message_type, content, consultation_id, requires_response,
                       target_agent_name, agent_name, created_at
                FROM public.work_thread_messages
                WHERE user_id = :user_id
                  AND thread_id = :thread_id
                ORDER BY created_at ASC
                LIMIT :limit
                """
            ),
            {"user_id": str(user_id), "thread_id": thread_id, "limit": safe_limit},
        ).mappings().all()
    return [_message_row_to_model(row) for row in rows]


def unread_workthread_messages(
    *,
    user_id: UUID | str,
    thread_id: str,
    target_agent_name: str | None = None,
) -> list[WorkThreadMessage]:
    target_sql = "AND (target_agent_name = :target_agent_name OR target_agent_name IS NULL)" if target_agent_name else ""
    with web_transaction(user_id) as session:
        _ensure_pro(session, user_id)
        rows = session.execute(
            text(
                f"""
                SELECT id, thread_id, message_type, content, consultation_id, requires_response,
                       target_agent_name, agent_name, created_at
                FROM public.work_thread_messages
                WHERE user_id = :user_id
                  AND thread_id = :thread_id
                  AND requires_response = true
                  {target_sql}
                ORDER BY created_at ASC
                """
            ),
            {"user_id": str(user_id), "thread_id": thread_id, "target_agent_name": target_agent_name},
        ).mappings().all()
    return [_message_row_to_model(row) for row in rows]


def _task_row_to_model(row) -> WorkThreadTask:
    return WorkThreadTask(
        task_id=str(row.id),
        thread_id=str(row.thread_id),
        title=row.title,
        status=row.status,
        lease_owner=row.lease_owner,
        lease_expires_at=row.lease_expires_at,
        result_message_id=str(row.result_message_id) if row.result_message_id else None,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def create_workthread_task(*, user_id: UUID | str, thread_id: str, title: str) -> WorkThreadTask:
    with web_transaction(user_id) as session:
        _ensure_pro(session, user_id)
        exists = session.execute(
            text("SELECT 1 FROM public.work_threads WHERE id = :thread_id AND user_id = :user_id"),
            {"thread_id": thread_id, "user_id": str(user_id)},
        ).scalar_one_or_none()
        if exists is None:
            raise AppError("workthread_not_found", "WorkThread not found", 404)
        row = session.execute(
            text(
                """
                INSERT INTO public.work_thread_tasks (thread_id, user_id, title)
                VALUES (:thread_id, :user_id, :title)
                RETURNING id, thread_id, title, status, lease_owner, lease_expires_at,
                          result_message_id, created_at, updated_at
                """
            ),
            {"thread_id": thread_id, "user_id": str(user_id), "title": title},
        ).mappings().one()
    return _task_row_to_model(row)


def claim_workthread_task(
    *,
    user_id: UUID | str,
    lease_owner: str,
    thread_id: str | None = None,
    lease_seconds: int = 300,
) -> WorkThreadTask | None:
    safe_lease_seconds = min(max(lease_seconds, 30), 3600)
    thread_filter = "AND thread_id = :thread_id" if thread_id else ""
    with web_transaction(user_id) as session:
        _ensure_pro(session, user_id)
        row = session.execute(
            text(
                f"""
                WITH candidate AS (
                  SELECT id
                  FROM public.work_thread_tasks
                  WHERE user_id = :user_id
                    {thread_filter}
                    AND (
                      status = 'pending' OR
                      (status = 'claimed' AND lease_expires_at <= now())
                    )
                  ORDER BY created_at ASC
                  FOR UPDATE SKIP LOCKED
                  LIMIT 1
                )
                UPDATE public.work_thread_tasks task
                SET status = 'claimed',
                    lease_owner = :lease_owner,
                    lease_expires_at = now() + (:lease_seconds * interval '1 second')
                FROM candidate
                WHERE task.id = candidate.id
                RETURNING task.id, task.thread_id, task.title, task.status, task.lease_owner,
                          task.lease_expires_at, task.result_message_id, task.created_at, task.updated_at
                """
            ),
            {
                "user_id": str(user_id),
                "thread_id": thread_id,
                "lease_owner": lease_owner,
                "lease_seconds": safe_lease_seconds,
            },
        ).mappings().first()
    return _task_row_to_model(row) if row else None


def complete_workthread_task(
    *,
    user_id: UUID | str,
    task_id: str,
    lease_owner: str,
    result_message_id: str | None = None,
) -> WorkThreadTask:
    with web_transaction(user_id) as session:
        _ensure_pro(session, user_id)
        row = session.execute(
            text(
                """
                UPDATE public.work_thread_tasks
                SET status = 'completed',
                    result_message_id = :result_message_id
                WHERE id = :task_id
                  AND user_id = :user_id
                  AND status = 'claimed'
                  AND lease_owner = :lease_owner
                  AND lease_expires_at > now()
                RETURNING id, thread_id, title, status, lease_owner, lease_expires_at,
                          result_message_id, created_at, updated_at
                """
            ),
            {
                "task_id": task_id,
                "user_id": str(user_id),
                "lease_owner": lease_owner,
                "result_message_id": result_message_id,
            },
        ).mappings().first()
        if row is None:
            raise AppError("task_lease_mismatch", "Task lease is missing, expired, or owned by another agent", 409)
    return _task_row_to_model(row)


def save_workthread_result(
    *,
    user_id: UUID | str,
    thread_id: str,
    slot_name: str,
    content_dict: dict,
    original_length: int | None = None,
    model_source: str | None = None,
    slot_number: int | None = None,
    retention_seconds: int | None = None,
    detail_level: str | None = "compact",
) -> WorkThreadResult:
    saved = web_context_service.save_context(
        user_id=user_id,
        slot_name=slot_name,
        content_dict=content_dict,
        original_length=original_length,
        model_source=model_source,
        slot_number=slot_number,
        retention_seconds=retention_seconds,
        detail_level=detail_level,
        meta=RequestMeta(client_type="api"),
    )
    with web_transaction(user_id) as session:
        _ensure_pro(session, user_id)
        updated = session.execute(
            text(
                """
                UPDATE public.work_threads
                SET status = 'completed',
                    final_slot_name = :slot_name
                WHERE id = :thread_id
                  AND user_id = :user_id
                RETURNING id
                """
            ),
            {"thread_id": thread_id, "user_id": str(user_id), "slot_name": slot_name},
        ).scalar_one_or_none()
        if updated is None:
            raise AppError("workthread_not_found", "WorkThread not found", 404)
    return WorkThreadResult(
        thread_id=thread_id,
        final_slot_name=saved.slot_name,
        resume_context_call=saved.resume_context_call,
        resume_prompt=saved.resume_prompt,
    )


def check_workthread_updates(
    *,
    user_id: UUID | str,
    thread_id: str,
    since: datetime | None = None,
) -> WorkThreadUpdateCheck:
    since_sql = "AND created_at > :since" if since else ""
    with web_transaction(user_id) as session:
        _ensure_pro(session, user_id)
        row = session.execute(
            text(
                f"""
                SELECT count(*) AS message_count, max(created_at) AS latest_message_at
                FROM public.work_thread_messages
                WHERE user_id = :user_id
                  AND thread_id = :thread_id
                  {since_sql}
                """
            ),
            {"user_id": str(user_id), "thread_id": thread_id, "since": since},
        ).mappings().one()
    return WorkThreadUpdateCheck(
        thread_id=thread_id,
        has_updates=row.message_count > 0,
        message_count=row.message_count,
        latest_message_at=row.latest_message_at,
    )


def wait_workthread_updates(
    *,
    user_id: UUID | str,
    thread_id: str,
    since: datetime | None = None,
    timeout_seconds: int = 30,
    poll_interval_seconds: float = 1.0,
) -> WorkThreadUpdateCheck:
    wait_reason = f"wait_updates:{since.isoformat() if since else 'latest'}"
    with web_transaction(user_id) as session:
        _ensure_pro(session, user_id)
        repeated_waits = session.execute(
            text(
                """
                SELECT count(*)
                FROM public.work_thread_runs
                WHERE user_id = :user_id
                  AND thread_id = :thread_id
                  AND status = 'timeout'
                  AND reason = :reason
                  AND created_at > now() - interval '1 hour'
                """
            ),
            {"user_id": str(user_id), "thread_id": thread_id, "reason": wait_reason},
        ).scalar_one()
        if repeated_waits >= MAX_REPEATED_WAITS:
            _block_loop(session, user_id=user_id, thread_id=thread_id, reason="repeated_waits")
            raise AppError("loop_guard_triggered", "Repeated WorkThread wait limit reached", 409)

    deadline = time.monotonic() + min(max(timeout_seconds, 1), 60)
    while True:
        result = check_workthread_updates(user_id=user_id, thread_id=thread_id, since=since)
        if result.has_updates or time.monotonic() >= deadline:
            if not result.has_updates:
                with web_transaction(user_id) as session:
                    session.execute(
                        text(
                            """
                            INSERT INTO public.work_thread_runs (thread_id, user_id, status, reason)
                            VALUES (:thread_id, :user_id, 'timeout', :reason)
                            """
                        ),
                        {"thread_id": thread_id, "user_id": str(user_id), "reason": wait_reason},
                    )
            return result
        time.sleep(max(poll_interval_seconds, 0.1))
