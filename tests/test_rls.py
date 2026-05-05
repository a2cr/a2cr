from pathlib import Path
import re


MIGRATION = Path(__file__).resolve().parents[1] / "supabase" / "migrations" / "001_base_schema.sql"


def sql() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def normalized_sql() -> str:
    return re.sub(r"\s+", " ", sql().lower())


def test_base_schema_file_exists():
    assert MIGRATION.exists()


def test_runtime_role_and_current_user_context_are_defined():
    text = normalized_sql()
    assert "create role a2cr_app login" in text
    assert "create or replace function app.current_user_id()" in text
    assert "current_setting('app.user_id', true)" in text
    assert "grant usage on schema public, app to a2cr_app" in text


def test_core_tables_have_user_scoped_uniqueness_and_constraints():
    text = normalized_sql()
    for table in ("contexts", "stats", "user_profiles", "api_keys", "access_logs"):
        assert f"create table if not exists public.{table}" in text
        assert f"alter table public.{table} enable row level security" in text

    assert "unique (user_id, slot_name)" in text
    assert "unique (user_id, slot_number)" in text
    assert "check (slot_number >= 1)" in text
    assert "check (plan in ('free', 'pro'))" in text
    assert "check (plan = 'pro' or context_detail_level = 'compact')" in text
    assert "plan = 'free' and default_retention_seconds in (900, 1800, 3600, 10800, 21600, 43200, 86400)" in text
    assert "plan = 'pro' and default_retention_seconds in (900, 1800, 3600, 10800, 21600, 43200, 86400, 259200, 604800, 864000, 1209600, 2592000)" in text
    assert "create unique index if not exists api_keys_hash_idx on public.api_keys(key_hash)" in text


def test_rls_policies_use_current_user_id_for_all_user_tables():
    text = normalized_sql()
    expected_policies = {
        "user_profiles": ("users_read_profile", "users_create_free_profile", "users_update_profile"),
        "contexts": ("users_own_slots",),
        "stats": ("users_own_stats",),
        "api_keys": ("users_own_api_key",),
        "access_logs": ("users_own_access_logs",),
    }

    for table, policies in expected_policies.items():
        for policy in policies:
            assert f"create policy {policy} on public.{table}" in text

    assert text.count("user_id = app.current_user_id()") >= 9


def test_api_key_resolution_is_security_definer_and_secret_safe():
    text = normalized_sql()
    assert "create or replace function app.resolve_api_key(p_key_hash text, p_ip_hash text)" in text
    assert "security definer" in text
    assert "revoked_at is null" in text
    assert "returns uuid" in text
    assert "return v_user_id" in text
    assert "revoke all on function app.resolve_api_key(text, text) from public" in text
    assert "grant execute on function app.resolve_api_key(text, text) to a2cr_app" in text


def test_expiration_logs_before_delete_semantics():
    text = normalized_sql()
    assert "create or replace function app.expire_contexts()" in text
    assert "returns integer language plpgsql security definer set search_path = pg_catalog, pg_temp" in text
    assert "delete from public.contexts" in text
    assert "select id, user_id, slot_name from public.contexts where expires_at <= now()" in text
    assert "insert into public.access_logs" in text
    assert "using expired" in text
    assert "'context.expire'" in text
    assert "'system'" in text
    assert "'success'" in text
    assert "grant execute on function app.expire_contexts() to a2cr_app" in text


def test_migration_does_not_reference_runtime_service_role_or_log_secret_fields():
    text = normalized_sql()
    forbidden = (
        "supabase_service_role_key",
        "authorization",
        "bearer",
        "raw_ip",
        "user_agent text",
        "request_body",
        "content_hash",
    )
    for term in forbidden:
        assert term not in text
