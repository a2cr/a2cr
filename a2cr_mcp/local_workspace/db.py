from __future__ import annotations

import sqlite3
from pathlib import Path

from .config import local_db_path
from .schema import SCHEMA_VERSION, apply_schema


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or local_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    apply_schema(conn)
    current = conn.execute(
        "SELECT value FROM settings WHERE key = 'schema_version'"
    ).fetchone()
    if current is None:
        conn.execute(
            "INSERT INTO settings(key, value) VALUES('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
    elif current["value"] != str(SCHEMA_VERSION):
        conn.execute(
            "UPDATE settings SET value = ? WHERE key = 'schema_version'",
            (str(SCHEMA_VERSION),),
        )
    return conn
