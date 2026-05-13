import pytest

from services.abuse_limits import (
    AUTH_FAILURE_RULE,
    AUTHENTICATED_RULES,
    RateLimitRule,
    enforce_authenticated_rate_limit,
    ensure_auth_attempt_allowed,
    record_auth_failure,
    reset_abuse_limit_state,
)
from services.exceptions import (
    BodyTooLarge,
    PlanLimitExceeded,
    RateLimitExceeded,
    RetentionNotAllowed,
)
from services.limits import (
    FREE_LIMITS,
    PRO_LIMITS,
    ensure_active_slot_capacity,
    ensure_hourly_limit,
    get_plan_limits,
    validate_body_size,
    validate_retention_seconds,
)
from services.plan_constants import FREE_ACTIVE_SLOTS, PRO_ACTIVE_SLOTS


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


def test_plan_slot_limits_match_public_preview_constants():
    assert FREE_LIMITS.active_slots == FREE_ACTIVE_SLOTS == 5
    assert PRO_LIMITS.active_slots == PRO_ACTIVE_SLOTS == 50


def test_plan_hourly_limits_match_public_preview_constants():
    assert FREE_LIMITS.saves_per_hour == 100
    assert FREE_LIMITS.loads_per_hour == 200
    assert PRO_LIMITS.saves_per_hour == 300
    assert PRO_LIMITS.loads_per_hour == 600


def test_validate_retention_allows_free_24h_and_pro_30d():
    assert validate_retention_seconds(86400, FREE_LIMITS) == 86400
    assert validate_retention_seconds(2592000, PRO_LIMITS) == 2592000


def test_validate_retention_rejects_free_30d():
    with pytest.raises(RetentionNotAllowed):
        validate_retention_seconds(2592000, FREE_LIMITS)


def test_validate_body_size_uses_plan_limits():
    validate_body_size(24 * 1024, FREE_LIMITS)
    with pytest.raises(BodyTooLarge):
        validate_body_size(24 * 1024 + 1, FREE_LIMITS)

    validate_body_size(64 * 1024, PRO_LIMITS)
    with pytest.raises(BodyTooLarge):
        validate_body_size(64 * 1024 + 1, PRO_LIMITS)


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


def test_invalid_auth_rate_limit_blocks_after_repeated_failures():
    reset_abuse_limit_state()
    ip_hash = "ip-hash"

    for index in range(AUTH_FAILURE_RULE.limit):
        ensure_auth_attempt_allowed("api.api_key", ip_hash, now=float(index))
        record_auth_failure("api.api_key", ip_hash, now=float(index))

    with pytest.raises(RateLimitExceeded) as exc:
        ensure_auth_attempt_allowed("api.api_key", ip_hash, now=float(AUTH_FAILURE_RULE.limit))

    assert exc.value.code == "invalid_auth_rate_limited"
    assert exc.value.status == 429


def test_authenticated_abuse_limit_uses_action_specific_rule():
    reset_abuse_limit_state()
    original = AUTHENTICATED_RULES["dashboard.read"]
    AUTHENTICATED_RULES["dashboard.read"] = RateLimitRule(2, 60, "dashboard_rate_limited")
    try:
        enforce_authenticated_rate_limit("user-a", "dashboard.read", now=1.0)
        enforce_authenticated_rate_limit("user-a", "dashboard.read", now=2.0)
        with pytest.raises(RateLimitExceeded) as exc:
            enforce_authenticated_rate_limit("user-a", "dashboard.read", now=3.0)
    finally:
        AUTHENTICATED_RULES["dashboard.read"] = original

    assert exc.value.code == "dashboard_rate_limited"
    assert exc.value.headers["Retry-After"] == "58"
