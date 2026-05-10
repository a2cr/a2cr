from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text


REQUIRED_TABLES = {
    "user_profiles",
    "contexts",
    "stats",
    "api_keys",
    "access_logs",
    "work_threads",
    "work_thread_messages",
    "work_thread_tasks",
    "work_thread_runs",
}

REQUIRED_APP_TABLES = {
    "schema_migrations",
}

REQUIRED_COLUMNS = {
    "contexts": {
        "user_id",
        "slot_name",
        "slot_number",
        "content",
        "detail_level",
        "expires_at",
        "size_bytes",
        "compressed_tokens",
        "load_count",
        "encryption_mode",
        "encryption_version",
        "encryption_metadata",
    },
    "stats": {"user_id", "total_saves", "total_loads", "total_deletes", "total_tokens_saved"},
    "work_thread_messages": {"resolved_at", "resolved_by_message_id"},
    "work_thread_tasks": {"failure_reason"},
}

REQUIRED_FUNCTIONS = {
    "current_user_id",
    "resolve_api_key",
    "record_context_save",
    "record_context_load",
    "record_context_delete",
    "expire_contexts",
    "prune_access_logs",
    "data_lifecycle_scan",
}

REQUIRED_USER_OWNED_TABLES = {
    "user_profiles",
    "contexts",
    "stats",
    "api_keys",
    "access_logs",
    "work_threads",
    "work_thread_messages",
    "work_thread_tasks",
    "work_thread_runs",
}

REQUIRED_CONTEXT_UNIQUES = {
    ("user_id", "slot_name"),
    ("user_id", "slot_number"),
}


@dataclass(frozen=True)
class SchemaReadinessResult:
    ready: bool
    checks: dict[str, bool]
    missing: dict[str, list[str]]


def check_schema_readiness(engine) -> SchemaReadinessResult:
    with engine.begin() as conn:
        tables = set(
            conn.execute(
                text(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    """
                )
            ).scalars()
        )
        app_tables = set(
            conn.execute(
                text(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'app'
                    """
                )
            ).scalars()
        )
        column_rows = conn.execute(
            text(
                """
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                """
            )
        ).all()
        columns_by_table: dict[str, set[str]] = {}
        for table_name, column_name in column_rows:
            columns_by_table.setdefault(table_name, set()).add(column_name)

        functions = set(
            conn.execute(
                text(
                    """
                    SELECT routine_name
                    FROM information_schema.routines
                    WHERE specific_schema = 'app'
                    """
                )
            ).scalars()
        )
        rls_enabled = set(
            conn.execute(
                text(
                    """
                    SELECT relname
                    FROM pg_class
                    JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace
                    WHERE pg_namespace.nspname = 'public'
                      AND relrowsecurity
                    """
                )
            ).scalars()
        )
        unique_constraints = {
            tuple(row[0])
            for row in conn.execute(
                text(
                    """
                    SELECT array_agg(att.attname ORDER BY cols.ordinality) AS columns
                    FROM pg_constraint con
                    JOIN pg_class cls ON cls.oid = con.conrelid
                    JOIN pg_namespace ns ON ns.oid = cls.relnamespace
                    JOIN unnest(con.conkey) WITH ORDINALITY AS cols(attnum, ordinality) ON true
                    JOIN pg_attribute att
                      ON att.attrelid = con.conrelid
                     AND att.attnum = cols.attnum
                    WHERE ns.nspname = 'public'
                      AND cls.relname = 'contexts'
                      AND con.contype = 'u'
                    GROUP BY con.oid
                    """
                )
            )
        }

    missing_tables = sorted(REQUIRED_TABLES - tables)
    missing_app_tables = sorted(f"app.{table}" for table in REQUIRED_APP_TABLES - app_tables)
    missing_columns = sorted(
        f"{table}.{column}"
        for table, required_columns in REQUIRED_COLUMNS.items()
        for column in required_columns - columns_by_table.get(table, set())
    )
    missing_functions = sorted(REQUIRED_FUNCTIONS - functions)
    missing_rls = sorted(REQUIRED_USER_OWNED_TABLES - rls_enabled)
    missing_uniques = sorted(
        ", ".join(columns)
        for columns in REQUIRED_CONTEXT_UNIQUES - unique_constraints
    )

    checks = {
        "tables": not missing_tables,
        "app_tables": not missing_app_tables,
        "columns": not missing_columns,
        "functions": not missing_functions,
        "rls": not missing_rls,
        "context_uniques": not missing_uniques,
    }
    missing = {
        "tables": missing_tables,
        "app_tables": missing_app_tables,
        "columns": missing_columns,
        "functions": missing_functions,
        "rls": missing_rls,
        "context_uniques": missing_uniques,
    }
    return SchemaReadinessResult(ready=all(checks.values()), checks=checks, missing=missing)
