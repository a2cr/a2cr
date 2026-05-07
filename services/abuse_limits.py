from __future__ import annotations

import time
from dataclasses import dataclass
from math import ceil
from uuid import UUID

from services.exceptions import RateLimitExceeded


@dataclass(frozen=True)
class RateLimitRule:
    limit: int
    window_seconds: int
    code: str
    message: str = "Too many requests"


AUTH_FAILURE_RULE = RateLimitRule(
    limit=10,
    window_seconds=300,
    code="invalid_auth_rate_limited",
    message="Too many invalid authentication attempts",
)

AUTHENTICATED_RULES = {
    "dashboard.read": RateLimitRule(300, 60, "dashboard_rate_limited"),
    "dashboard.mutate": RateLimitRule(60, 3600, "dashboard_mutation_rate_limited"),
    "dashboard.api_key.mutate": RateLimitRule(10, 3600, "api_key_rate_limited"),
    "context.read": RateLimitRule(600, 60, "context_read_rate_limited"),
    "context.write": RateLimitRule(300, 60, "context_write_rate_limited"),
    "context.delete": RateLimitRule(120, 3600, "context_delete_rate_limited"),
    "workthreads.read": RateLimitRule(600, 60, "workthread_read_rate_limited"),
    "workthreads.write": RateLimitRule(300, 60, "workthread_write_rate_limited"),
    "workthreads.wait": RateLimitRule(30, 60, "workthread_wait_rate_limited"),
    "workthreads.task": RateLimitRule(300, 60, "workthread_task_rate_limited"),
}

_events: dict[tuple[str, str, str], list[float]] = {}


def _now() -> float:
    return time.time()


def _subject(value: UUID | str | None) -> str:
    return str(value or "unknown")


def _bucket(kind: str, action: str, subject: UUID | str | None) -> tuple[str, str, str]:
    return kind, action, _subject(subject)


def _prune(events: list[float], *, now: float, window_seconds: int) -> list[float]:
    cutoff = now - window_seconds
    return [event for event in events if event > cutoff]


def _retry_after(events: list[float], *, now: float, window_seconds: int) -> int:
    if not events:
        return window_seconds
    return max(1, ceil(window_seconds - (now - min(events))))


def _check(key: tuple[str, str, str], rule: RateLimitRule, *, add_event: bool, now: float | None = None) -> None:
    current_time = _now() if now is None else now
    events = _prune(_events.get(key, []), now=current_time, window_seconds=rule.window_seconds)
    if len(events) >= rule.limit:
        _events[key] = events
        raise RateLimitExceeded(
            rule.code,
            rule.message,
            retry_after=_retry_after(events, now=current_time, window_seconds=rule.window_seconds),
        )
    if add_event:
        events.append(current_time)
    _events[key] = events


def ensure_auth_attempt_allowed(action: str, ip_hash: str | None, *, now: float | None = None) -> None:
    _check(_bucket("auth_failure", action, ip_hash), AUTH_FAILURE_RULE, add_event=False, now=now)


def record_auth_failure(action: str, ip_hash: str | None, *, now: float | None = None) -> None:
    _check(_bucket("auth_failure", action, ip_hash), AUTH_FAILURE_RULE, add_event=True, now=now)


def enforce_authenticated_rate_limit(user_id: UUID | str, action: str, *, now: float | None = None) -> None:
    rule = AUTHENTICATED_RULES[action]
    _check(_bucket("authenticated", action, user_id), rule, add_event=True, now=now)


def reset_abuse_limit_state() -> None:
    _events.clear()
