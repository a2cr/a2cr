from __future__ import annotations

import os
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import create_engine, text


@dataclass(frozen=True)
class SmokeConfig:
    database_url: str
    user_a_id: str
    user_b_id: str


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def load_config() -> SmokeConfig:
    user_a_id = str(UUID(_required_env("A2CR_SMOKE_USER_A_ID")))
    user_b_id = str(UUID(_required_env("A2CR_SMOKE_USER_B_ID")))
    if user_a_id == user_b_id:
        raise RuntimeError("A2CR_SMOKE_USER_A_ID and A2CR_SMOKE_USER_B_ID must be different")
    return SmokeConfig(
        database_url=_required_env("DATABASE_URL"),
        user_a_id=user_a_id,
        user_b_id=user_b_id,
    )


def _set_rls_user(conn, user_id: str) -> None:
    conn.execute(
        text("SELECT set_config('app.user_id', :user_id, true)"),
        {"user_id": user_id},
    )


def _current_user_id(conn) -> str | None:
    value = conn.execute(text("SELECT app.current_user_id()")).scalar_one_or_none()
    return str(value) if value is not None else None


def _count_visible_rows(conn, *, table: str, victim_user_id: str) -> int:
    if table not in {"contexts", "work_threads"}:
        raise ValueError("unsupported smoke table")
    return int(
        conn.execute(
            text(f"SELECT count(*) FROM public.{table} WHERE user_id = :victim_user_id"),
            {"victim_user_id": victim_user_id},
        ).scalar_one()
    )


def _assert_isolated(conn, *, actor_user_id: str, victim_user_id: str, label: str) -> None:
    _set_rls_user(conn, actor_user_id)
    if _current_user_id(conn) != actor_user_id:
        raise RuntimeError(f"{label}: transaction-local app.user_id was not set")

    visible_contexts = _count_visible_rows(conn, table="contexts", victim_user_id=victim_user_id)
    visible_threads = _count_visible_rows(conn, table="work_threads", victim_user_id=victim_user_id)
    if visible_contexts != 0 or visible_threads != 0:
        raise RuntimeError(f"{label}: cross-user rows were visible")


def _assert_context_reset(engine) -> None:
    with engine.connect() as conn:
        value = conn.execute(text("SELECT current_setting('app.user_id', true)")).scalar_one_or_none()
        current_user_id = _current_user_id(conn)
    if value not in (None, "") or current_user_id is not None:
        raise RuntimeError("transaction-local app.user_id leaked after transaction")


def run_smoke(config: SmokeConfig) -> None:
    engine = create_engine(config.database_url, pool_pre_ping=True)
    try:
        with engine.begin() as conn:
            _assert_isolated(
                conn,
                actor_user_id=config.user_a_id,
                victim_user_id=config.user_b_id,
                label="user A",
            )
        _assert_context_reset(engine)

        with engine.begin() as conn:
            _assert_isolated(
                conn,
                actor_user_id=config.user_b_id,
                victim_user_id=config.user_a_id,
                label="user B",
            )
        _assert_context_reset(engine)
    finally:
        engine.dispose()


def main() -> int:
    try:
        run_smoke(load_config())
    except RuntimeError as exc:
        print(f"RLS/pooler smoke: FAIL ({exc})")
        return 1
    except Exception as exc:
        print(f"RLS/pooler smoke: FAIL ({type(exc).__name__})")
        return 1

    print("RLS/pooler smoke: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
