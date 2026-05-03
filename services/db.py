from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, Integer, String, DateTime, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

from services.config import get_config

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            f"sqlite:///{get_config().db_path}",
            connect_args={"check_same_thread": False},
        )
    return _engine


class Base(DeclarativeBase):
    pass


class Context(Base):
    __tablename__ = "contexts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    slot_name: Mapped[str] = mapped_column(String, unique=True, index=True)
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
    with Session(engine) as session:
        if session.get(Stats, 1) is None:
            session.add(Stats(id=1, total_saves=0, total_loads=0, total_tokens_saved=0))
            session.commit()
