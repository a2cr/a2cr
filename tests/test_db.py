from sqlalchemy.orm import Session
from services.db import get_engine, Stats, Context, init_db


def test_init_db_creates_stats_row():
    engine = get_engine()
    with Session(engine) as session:
        stats = session.get(Stats, 1)
    assert stats is not None
    assert stats.total_saves == 0
    assert stats.total_loads == 0
    assert stats.total_tokens_saved == 0


def test_init_db_idempotent():
    init_db()
    init_db()  # should not raise
    engine = get_engine()
    with Session(engine) as session:
        from sqlalchemy import select, func
        count = session.scalar(select(func.count()).select_from(Stats))
    assert count == 1
