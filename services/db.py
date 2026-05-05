from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Generator, Optional
from uuid import UUID

from sqlalchemy import create_engine, Integer, String, DateTime, Text, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

from services.config import get_config, get_web_config

_engine = None
_web_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            f"sqlite:///{get_config().db_path}",
            connect_args={"check_same_thread": False},
        )
    return _engine


def get_web_engine():
    global _web_engine
    if _web_engine is None:
        _web_engine = create_engine(get_web_config().database_url, pool_pre_ping=True)
    return _web_engine


def set_rls_user_context(session: Session, user_id: UUID | str) -> None:
    session.execute(text("SET LOCAL app.user_id = :user_id"), {"user_id": str(user_id)})


@contextmanager
def web_transaction(user_id: UUID | str) -> Generator[Session, None, None]:
    session = Session(get_web_engine())
    try:
        with session.begin():
            set_rls_user_context(session, user_id)
            yield session
    finally:
        session.close()


def reset_web_engine() -> None:
    global _web_engine
    if _web_engine is not None:
        _web_engine.dispose()
    _web_engine = None


class Base(DeclarativeBase):
    pass


class Context(Base):
    __tablename__ = "contexts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    slot_name: Mapped[str] = mapped_column(String, unique=True, index=True)
    slot_number: Mapped[Optional[int]] = mapped_column(Integer, unique=True, index=True, nullable=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    size_bytes: Mapped[int] = mapped_column(Integer)
    original_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    compressed_tokens: Mapped[int] = mapped_column(Integer)
    load_count: Mapped[int] = mapped_column(Integer, default=0)
    model_source: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class Stats(Base):
    __tablename__ = "stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    total_saves: Mapped[int] = mapped_column(Integer, default=0)
    total_loads: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens_saved: Mapped[int] = mapped_column(Integer, default=0)


def init_db() -> None:
    engine = get_engine()
    Base.metadata.create_all(engine)
    _migrate_slot_number(engine)
    with Session(engine) as session:
        if session.get(Stats, 1) is None:
            session.add(Stats(id=1, total_saves=0, total_loads=0, total_tokens_saved=0))
            session.commit()


def _migrate_slot_number(engine) -> None:
    with engine.begin() as conn:
        columns = {
            row[1]
            for row in conn.exec_driver_sql("PRAGMA table_info(contexts)").fetchall()
        }
        if "slot_number" not in columns:
            conn.exec_driver_sql("ALTER TABLE contexts ADD COLUMN slot_number INTEGER")
        conn.exec_driver_sql(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_contexts_slot_number ON contexts(slot_number)"
        )

        used = {
            row[0]
            for row in conn.exec_driver_sql(
                "SELECT slot_number FROM contexts WHERE slot_number IS NOT NULL"
            ).fetchall()
        }
        available = [n for n in range(1, 4) if n not in used]
        unassigned = conn.exec_driver_sql(
            "SELECT id FROM contexts WHERE slot_number IS NULL ORDER BY updated_at DESC"
        ).fetchall()
        for row, slot_number in zip(unassigned, available):
            conn.exec_driver_sql(
                "UPDATE contexts SET slot_number = ? WHERE id = ?",
                (slot_number, row[0]),
            )
