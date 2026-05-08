from __future__ import annotations

from contextlib import contextmanager
from typing import Generator
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from services.config import get_db_config, get_web_config

_web_engine = None


def get_web_engine():
    global _web_engine
    if _web_engine is None:
        config = get_db_config()
        _web_engine = create_engine(
            config.database_url,
            pool_pre_ping=True,
            pool_size=config.db_pool_size,
            max_overflow=config.db_max_overflow,
            pool_timeout=config.db_pool_timeout_seconds,
            pool_recycle=config.db_pool_recycle_seconds,
        )
    return _web_engine


def set_transaction_timeouts(session: Session) -> None:
    config = get_web_config()
    timeout_values = {
        "statement_timeout": f"{config.db_statement_timeout_ms}ms",
        "lock_timeout": f"{config.db_lock_timeout_ms}ms",
        "idle_in_transaction_session_timeout": f"{config.db_idle_transaction_timeout_ms}ms",
    }
    for name, value in timeout_values.items():
        session.execute(
            text("SELECT set_config(:name, :value, true)"),
            {"name": name, "value": value},
        )


def set_rls_user_context(session: Session, user_id: UUID | str) -> None:
    session.execute(
        text("SELECT set_config('app.user_id', :user_id, true)"),
        {"user_id": str(user_id)},
    )


def acquire_user_mutation_lock(session: Session, user_id: UUID | str) -> None:
    session.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
        {"lock_key": f"workbaton:{user_id}"},
    )


@contextmanager
def web_transaction(user_id: UUID | str) -> Generator[Session, None, None]:
    session = Session(get_web_engine())
    try:
        with session.begin():
            set_transaction_timeouts(session)
            set_rls_user_context(session, user_id)
            yield session
    finally:
        session.close()


def reset_web_engine() -> None:
    global _web_engine
    if _web_engine is not None:
        dispose = getattr(_web_engine, "dispose", None)
        if dispose is not None:
            dispose()
    _web_engine = None


