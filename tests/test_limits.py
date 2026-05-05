import pytest

from services.exceptions import BodyTooLarge, DetailLevelNotAllowed, PlanLimitExceeded, RetentionNotAllowed
from services.limits import (
    FREE_LIMITS,
    PRO_LIMITS,
    ensure_active_slot_capacity,
    ensure_hourly_limit,
    get_plan_limits,
    validate_body_size,
    validate_detail_level,
    validate_retention_seconds,
)


class FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value

    def scalar_one_or_none(self):
        return self.value


class FakeSession:
    def __init__(self, values):
        self.values = list(values)
        self.executed = []

    def execute(self, statement, params=None):
        self.executed.append((str(statement), params or {}))
        return FakeResult(self.values.pop(0))


def test_get_plan_limits_defaults_to_free():
    assert get_plan_limits(None) == FREE_LIMITS
    assert get_plan_limits("free") == FREE_LIMITS
    assert get_plan_limits("pro") == PRO_LIMITS


def test_validate_retention_allows_free_24h_and_pro_30d():
    assert validate_retention_seconds(86400, FREE_LIMITS) == 86400
    assert validate_retention_seconds(2592000, PRO_LIMITS) == 2592000


def test_validate_retention_rejects_free_30d():
    with pytest.raises(RetentionNotAllowed):
        validate_retention_seconds(2592000, FREE_LIMITS)


def test_validate_detail_level_rejects_free_detailed():
    with pytest.raises(DetailLevelNotAllowed):
        validate_detail_level("detailed", FREE_LIMITS)


def test_validate_body_size_uses_plan_limits():
    validate_body_size(32 * 1024, FREE_LIMITS)
    with pytest.raises(BodyTooLarge):
        validate_body_size(32 * 1024 + 1, FREE_LIMITS)


def test_ensure_hourly_limit_raises_with_retry_after():
    session = FakeSession([FREE_LIMITS.saves_per_hour])

    with pytest.raises(PlanLimitExceeded) as exc:
        ensure_hourly_limit(
            session,
            user_id="00000000-0000-0000-0000-0000000000a1",
            action="context.save",
            limit=FREE_LIMITS.saves_per_hour,
            code="save_rate_limit_exceeded",
        )

    assert exc.value.status == 429
    assert exc.value.extra["retry_after"] == 3600


def test_ensure_active_slot_capacity_allows_existing_slot():
    session = FakeSession(["existing-id"])

    ensure_active_slot_capacity(
        session,
        user_id="00000000-0000-0000-0000-0000000000a1",
        slot_name="slot-a",
        slot_number=1,
        limits=FREE_LIMITS,
    )

    assert len(session.executed) == 1


def test_ensure_active_slot_capacity_rejects_new_slot_over_limit():
    session = FakeSession([None, FREE_LIMITS.active_slots])

    with pytest.raises(PlanLimitExceeded) as exc:
        ensure_active_slot_capacity(
            session,
            user_id="00000000-0000-0000-0000-0000000000a1",
            slot_name="slot-overflow",
            slot_number=None,
            limits=FREE_LIMITS,
        )

    assert exc.value.code == "slot_limit_exceeded"
