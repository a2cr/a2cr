from __future__ import annotations

from pathlib import Path
from uuid import UUID

import services.data_lifecycle as lifecycle


USER_ID = UUID("00000000-0000-0000-0000-0000000000a1")


class FakeResult:
    def __init__(self, row):
        self.row = row

    def mappings(self):
        return self

    def one(self):
        return self.row


class FakeSession:
    def __init__(self, row):
        self.row = row
        self.executed = []

    def execute(self, statement, params=None):
        self.executed.append((str(statement), params or {}))
        return FakeResult(self.row)


class FakeTransaction:
    def __init__(self, session):
        self.session = session

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc, tb):
        return False


def use_fake_lifecycle_session(monkeypatch, row):
    session = FakeSession(row)
    monkeypatch.setattr(lifecycle, "web_transaction", lambda user_id: FakeTransaction(session))
    return session


def joined_sql(session):
    return "\n".join(statement for statement, _ in session.executed).lower()


def assert_dry_run_sql_is_count_only(session):
    sql = joined_sql(session)
    for forbidden in (
        "select *",
        "delete ",
        "update ",
        "insert ",
        "contexts.content",
        "api_keys.key_hash",
        "last_used_ip_hash",
        "work_thread_messages.content",
        "content_hash",
        "encryption_metadata",
        "authorization",
        "bearer",
        "ip_hash",
        "user_agent_hash",
        "app.expire_contexts",
        "app.resolve_api_key",
    ):
        assert forbidden not in sql


def global_scan_row(**overrides):
    row = {field: 0 for field in lifecycle.GLOBAL_ORPHAN_SCAN_FIELDS}
    row.update(overrides)
    return row


def test_downgrade_dry_run_reports_over_free_slots_without_deleting_rows(monkeypatch):
    session = use_fake_lifecycle_session(
        monkeypatch,
        {
            "active_contexts": 5,
            "contexts_over_slot_limit": 2,
            "oversized_contexts": 0,
            "detailed_contexts": 1,
            "pro_retention_contexts": 1,
            "old_access_logs": 4,
            "profile_updates_needed": 1,
        },
    )

    result = lifecycle.downgrade_to_free_dry_run(user_id=USER_ID)

    assert result.active_contexts == 5
    assert result.active_slot_limit == lifecycle.FREE_LIMITS.active_slots
    assert result.contexts_over_slot_limit == 2
    assert result.detailed_contexts == 1
    assert result.pro_retention_contexts == 1
    assert result.old_access_logs == 4
    assert result.profile_updates_needed == 1
    assert result.would_delete_rows is False
    assert_dry_run_sql_is_count_only(session)


def test_downgrade_dry_run_reports_oversized_contexts_without_selecting_content(monkeypatch):
    session = use_fake_lifecycle_session(
        monkeypatch,
        {
            "active_contexts": 3,
            "contexts_over_slot_limit": 0,
            "oversized_contexts": 2,
            "detailed_contexts": 0,
            "pro_retention_contexts": 0,
            "old_access_logs": 0,
            "profile_updates_needed": 0,
        },
    )

    result = lifecycle.downgrade_to_free_dry_run(user_id=USER_ID)

    assert result.oversized_contexts == 2
    assert "size_bytes > :max_body_bytes" in joined_sql(session)
    assert_dry_run_sql_is_count_only(session)


def test_account_delete_dry_run_counts_user_owned_rows_without_secret_fields(monkeypatch):
    row = {table_name: index for index, table_name in enumerate(lifecycle.ACCOUNT_DELETE_TABLES, start=1)}
    session = use_fake_lifecycle_session(monkeypatch, row)

    result = lifecycle.account_delete_dry_run(user_id=USER_ID)

    assert result.dry_run is True
    assert result.table_counts == row
    assert result.total_rows == sum(row.values())
    assert_dry_run_sql_is_count_only(session)


def test_orphan_scan_queries_all_user_owned_tables(monkeypatch):
    row = {table_name: 0 for table_name in lifecycle.ACCOUNT_DELETE_TABLES}
    session = use_fake_lifecycle_session(monkeypatch, row)

    result = lifecycle.account_delete_orphan_scan(user_id=USER_ID)
    sql = joined_sql(session)

    assert result.total_rows == 0
    for table_name in lifecycle.ACCOUNT_DELETE_TABLES:
        assert f"public.{table_name}" in sql


def test_global_orphan_data_lifecycle_scan_uses_count_only_db_function(monkeypatch):
    session = use_fake_lifecycle_session(
        monkeypatch,
        global_scan_row(
            expired_contexts=2,
            old_access_logs=3,
            work_thread_messages_without_thread=4,
            work_thread_tasks_user_mismatch=5,
        ),
    )

    monkeypatch.setattr(lifecycle, "validate_runtime_environment", lambda: None)
    monkeypatch.setattr(lifecycle, "get_web_engine", lambda: type("FakeEngine", (), {"begin": lambda self: FakeTransaction(session)})())

    result = lifecycle.global_orphan_data_lifecycle_scan(old_access_logs_older_than_seconds=0)
    sql = joined_sql(session)

    assert result.old_access_logs_older_than_seconds == 1
    assert result.counts["expired_contexts"] == 2
    assert result.counts["old_access_logs"] == 3
    assert result.counts["work_thread_messages_without_thread"] == 4
    assert result.counts["work_thread_tasks_user_mismatch"] == 5
    assert result.total_attention_rows == 14
    assert "app.data_lifecycle_scan" in sql
    assert "old_access_logs_older_than_seconds" in session.executed[0][1]
    assert_dry_run_sql_is_count_only(session)


def test_global_orphan_data_lifecycle_scan_migration_is_count_only():
    migration = (
        Path(lifecycle.__file__).resolve().parents[1] / "supabase" / "migrations" / "008_data_lifecycle_scan.sql"
    ).read_text(encoding="utf-8")

    for field in lifecycle.GLOBAL_ORPHAN_SCAN_FIELDS:
        assert field in migration
    assert "CREATE OR REPLACE FUNCTION app.data_lifecycle_scan" in migration
    assert "SECURITY DEFINER" in migration
    assert "SET search_path = pg_catalog, pg_temp" in migration
    assert "GRANT EXECUTE ON FUNCTION app.data_lifecycle_scan(interval) TO a2cr_app" in migration
    assert "008_data_lifecycle_scan" in migration
    for forbidden in (
        "contexts.content",
        "work_thread_messages.content",
        "api_keys.key_hash",
        "last_used_ip_hash",
        "ip_hash",
        "user_agent_hash",
    ):
        assert forbidden not in migration


def test_data_lifecycle_runbook_defines_downgrade_and_account_delete_order():
    runbook = Path(lifecycle.__file__).resolve().parents[1] / "docs" / "runbooks" / "data-lifecycle.md"
    text = runbook.read_text(encoding="utf-8")

    assert "Pro To Free Downgrade" in text
    assert "count-only" in text
    assert "must not delete rows" in text
    assert "access logs older than the Free retention window" in text
    assert "must not select or print" in text
    assert "`contexts.content`" in text
    assert "`api_keys.key_hash`" in text
    assert "`work_thread_messages.content`" in text
    assert "Global Orphan Scan" in text
    assert "python -m services.maintenance data-lifecycle-scan" in text
    assert "app.data_lifecycle_scan" in text
    assert "WorkThread child rows whose `user_id` does not match the parent thread" in text
    assert "Delete the Supabase Auth user only after product cleanup and orphan scan" in text
    assert "succeed" in text
