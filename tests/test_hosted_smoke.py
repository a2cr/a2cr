from __future__ import annotations

from uuid import UUID

import scripts.smoke_rls_pooler as smoke


USER_A = "00000000-0000-0000-0000-0000000000a1"
USER_B = "00000000-0000-0000-0000-0000000000b2"


class FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value

    def scalar_one_or_none(self):
        return self.value


class FakeConnection:
    def __init__(self, *, reset_check: bool = False):
        self.reset_check = reset_check
        self.app_user_id = None
        self.executed = []

    def execute(self, statement, params=None):
        statement_text = str(statement)
        self.executed.append((statement_text, params or {}))
        if "set_config('app.user_id'" in statement_text:
            self.app_user_id = params["user_id"]
            return FakeResult(self.app_user_id)
        if "app.current_user_id()" in statement_text:
            return FakeResult(None if self.reset_check else self.app_user_id)
        if "current_setting('app.user_id', true)" in statement_text:
            return FakeResult("")
        if "count(*)" in statement_text:
            return FakeResult(0)
        return FakeResult(None)


class FakeContext:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeEngine:
    def __init__(self):
        self.begin_connections = []
        self.reset_connections = []
        self.disposed = False

    def begin(self):
        conn = FakeConnection()
        self.begin_connections.append(conn)
        return FakeContext(conn)

    def connect(self):
        conn = FakeConnection(reset_check=True)
        self.reset_connections.append(conn)
        return FakeContext(conn)

    def dispose(self):
        self.disposed = True


def test_load_config_requires_distinct_uuid_users(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:secret@example/db")
    monkeypatch.setenv("A2CR_SMOKE_USER_A_ID", USER_A)
    monkeypatch.setenv("A2CR_SMOKE_USER_B_ID", USER_B)

    config = smoke.load_config()

    assert config.database_url.startswith("postgresql+psycopg://")
    assert config.user_a_id == str(UUID(USER_A))
    assert config.user_b_id == str(UUID(USER_B))


def test_run_smoke_sets_transaction_local_rls_and_checks_reset(monkeypatch):
    engine = FakeEngine()
    monkeypatch.setattr(smoke, "create_engine", lambda *args, **kwargs: engine)

    smoke.run_smoke(smoke.SmokeConfig(database_url="postgresql+psycopg://secret", user_a_id=USER_A, user_b_id=USER_B))

    assert engine.disposed is True
    assert len(engine.begin_connections) == 2
    assert len(engine.reset_connections) == 2
    first = engine.begin_connections[0].executed
    assert "SELECT set_config('app.user_id', :user_id, true)" in first[0][0]
    assert "public.contexts" in first[2][0]
    assert "public.work_threads" in first[3][0]
    assert first[2][1]["victim_user_id"] == USER_B


def test_smoke_failure_output_does_not_print_database_url(monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:super-secret@example/db")
    monkeypatch.setenv("A2CR_SMOKE_USER_A_ID", USER_A)
    monkeypatch.setenv("A2CR_SMOKE_USER_B_ID", USER_B)

    def fail(config):
        raise ValueError("postgresql+psycopg://user:super-secret@example/db")

    monkeypatch.setattr(smoke, "run_smoke", fail)

    assert smoke.main() == 1
    output = capsys.readouterr().out
    assert "RLS/pooler smoke: FAIL (ValueError)" in output
    assert "super-secret" not in output
    assert "postgresql+psycopg" not in output
