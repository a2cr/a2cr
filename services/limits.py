from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from services.exceptions import (
    BodyTooLarge,
    DetailLevelNotAllowed,
    PlanLimitExceeded,
    RetentionNotAllowed,
)

PlanName = Literal["free", "pro"]
DetailLevel = Literal["compact", "detailed"]

FREE_RETENTION_SECONDS = (900, 1800, 3600, 10800, 21600, 43200, 86400)
PRO_RETENTION_SECONDS = (
    900,
    1800,
    3600,
    10800,
    21600,
    43200,
    86400,
    259200,
    604800,
    864000,
    1209600,
    2592000,
)


@dataclass(frozen=True)
class PlanLimits:
    plan: PlanName
    active_slots: int
    allowed_retention_seconds: tuple[int, ...]
    default_retention_seconds: int
    max_body_bytes: int
    allowed_detail_levels: tuple[DetailLevel, ...]
    saves_per_hour: int
    loads_per_hour: int
    access_log_retention_seconds: int
    api_keys: int = 1


FREE_LIMITS = PlanLimits(
    plan="free",
    active_slots=5,
    allowed_retention_seconds=FREE_RETENTION_SECONDS,
    default_retention_seconds=86400,
    max_body_bytes=24 * 1024,
    allowed_detail_levels=("compact",),
    saves_per_hour=100,
    loads_per_hour=300,
    access_log_retention_seconds=86400,
)

PRO_LIMITS = PlanLimits(
    plan="pro",
    active_slots=100,
    allowed_retention_seconds=PRO_RETENTION_SECONDS,
    default_retention_seconds=2592000,
    max_body_bytes=64 * 1024,
    allowed_detail_levels=("compact", "detailed"),
    saves_per_hour=1000,
    loads_per_hour=3000,
    access_log_retention_seconds=2592000,
)


def get_plan_limits(plan: str | None) -> PlanLimits:
    if plan == "pro":
        return PRO_LIMITS
    return FREE_LIMITS


def validate_retention_seconds(requested: int | None, limits: PlanLimits) -> int:
    retention = requested or limits.default_retention_seconds
    if retention not in limits.allowed_retention_seconds:
        raise RetentionNotAllowed()
    return retention


def validate_detail_level(requested: str | None, limits: PlanLimits) -> DetailLevel:
    detail_level = requested or "compact"
    if detail_level not in limits.allowed_detail_levels:
        raise DetailLevelNotAllowed()
    return detail_level  # type: ignore[return-value]


def validate_body_size(size_bytes: int, limits: PlanLimits) -> None:
    if size_bytes > limits.max_body_bytes:
        raise BodyTooLarge()


def ensure_hourly_limit(
    session: Session,
    *,
    user_id: UUID | str,
    action: str,
    limit: int,
    code: str,
) -> None:
    count = session.execute(
        text(
            """
            SELECT count(*)
            FROM public.access_logs
            WHERE user_id = :user_id
              AND action = :action
              AND created_at >= now() - interval '1 hour'
            """
        ),
        {"user_id": str(user_id), "action": action},
    ).scalar_one()
    if int(count) >= limit:
        raise PlanLimitExceeded(code, "Hourly plan limit exceeded")


def ensure_active_slot_capacity(
    session: Session,
    *,
    user_id: UUID | str,
    slot_name: str,
    slot_number: int | None,
    limits: PlanLimits,
) -> None:
    existing = session.execute(
        text(
            """
            SELECT id
            FROM public.contexts
            WHERE user_id = :user_id
              AND expires_at > now()
              AND encryption_mode = 'client'
              AND (slot_name = :slot_name OR (CAST(:slot_number AS integer) IS NOT NULL AND slot_number = CAST(:slot_number AS integer)))
            LIMIT 1
            """
        ),
        {"user_id": str(user_id), "slot_name": slot_name, "slot_number": slot_number},
    ).scalar_one_or_none()
    if existing is not None:
        return

    count = session.execute(
        text(
            """
            SELECT count(*)
            FROM public.contexts
            WHERE user_id = :user_id
              AND expires_at > now()
              AND encryption_mode = 'client'
            """
        ),
        {"user_id": str(user_id)},
    ).scalar_one()
    if int(count) >= limits.active_slots:
        raise PlanLimitExceeded("slot_limit_exceeded", "Active slot limit exceeded")
