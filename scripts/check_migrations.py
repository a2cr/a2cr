from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = ROOT / "supabase" / "migrations"


def expected_migration_ids() -> list[str]:
    return [path.stem for path in sorted(MIGRATIONS_DIR.glob("*.sql"))]


def applied_migration_ids(database_url: str) -> set[str]:
    engine = create_engine(database_url, pool_pre_ping=True)
    with engine.begin() as conn:
        return set(
            conn.execute(
                text(
                    """
                    SELECT migration_id
                    FROM app.schema_migrations
                    ORDER BY migration_id
                    """
                )
            ).scalars()
        )


def main() -> int:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is required")
        return 2

    expected = expected_migration_ids()
    applied = applied_migration_ids(database_url)
    pending = [migration_id for migration_id in expected if migration_id not in applied]

    if pending:
        print("Pending migrations:")
        for migration_id in pending:
            print(f"- {migration_id}")
        return 1

    print(f"All migrations applied ({len(expected)} total).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
