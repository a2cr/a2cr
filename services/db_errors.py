from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.exc import DBAPIError, OperationalError, SQLAlchemyError, TimeoutError


@dataclass(frozen=True)
class DbErrorClassification:
    code: str
    message: str
    status: int
    retry_after: int | None = None
    sqlstate: str | None = None


_SQLSTATE_MAP = {
    "40P01": DbErrorClassification("db_deadlock_retry", "Database contention. Retry shortly.", 503, 2, "40P01"),
    "40001": DbErrorClassification("db_serialization_retry", "Database contention. Retry shortly.", 503, 2, "40001"),
    "55P03": DbErrorClassification("db_lock_timeout", "Database is busy. Retry shortly.", 503, 2, "55P03"),
    "57014": DbErrorClassification("db_statement_timeout", "Database request timed out. Retry shortly.", 503, 2, "57014"),
    "23505": DbErrorClassification("db_unique_conflict", "The requested item conflicts with an existing item.", 409, None, "23505"),
}


def sqlstate_from_exception(exc: BaseException) -> str | None:
    current: BaseException | None = exc
    while current is not None:
        code = getattr(current, "sqlstate", None) or getattr(current, "pgcode", None)
        if code:
            return str(code)
        current = getattr(current, "orig", None) or getattr(current, "__cause__", None)
    return None


def classify_db_error(exc: BaseException) -> DbErrorClassification:
    if isinstance(exc, TimeoutError):
        return DbErrorClassification("db_pool_timeout", "Database is busy. Retry shortly.", 503, 2)

    sqlstate = sqlstate_from_exception(exc)
    if sqlstate in _SQLSTATE_MAP:
        return _SQLSTATE_MAP[sqlstate]

    if isinstance(exc, OperationalError):
        return DbErrorClassification("db_unavailable", "Database is temporarily unavailable.", 503, 2, sqlstate)

    if isinstance(exc, (DBAPIError, SQLAlchemyError)):
        return DbErrorClassification("db_error", "Database request failed.", 500, None, sqlstate)

    return DbErrorClassification("internal_error", "Request failed.", 500, None, sqlstate)
