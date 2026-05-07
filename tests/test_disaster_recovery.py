from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "docs" / "runbooks" / "disaster-recovery.md"


def read_runbook() -> str:
    return RUNBOOK.read_text(encoding="utf-8")


def normalized_runbook() -> str:
    return " ".join(read_runbook().split())


def test_disaster_recovery_runbook_defines_rto_rpo_and_backup_source():
    text = read_runbook()
    normalized = normalized_runbook()

    assert "RTO/RPO Targets" in text
    assert "Beta target" in text
    assert "Paid-production target" in text
    assert "Bad frontend/backend deploy | 30 minutes | RPO 0 | Railway rollback" in text
    assert "Missed migration or schema drift | 1 hour | RPO 0 | Forward-fix migration" in text
    assert "DB data corruption | 24 hours | 24 hours or provider backup window" in text
    assert "DB restore from backup | 4 hours | 1 hour to 24 hours depending on plan" in text
    assert "Supabase managed backups and/or scheduled exports depending on plan" in normalized
    assert "scheduled exports before beta" in text
    assert "Current status: testing / early beta. No production SLA." in text


def test_disaster_recovery_runbook_defines_recoverable_and_nonrecoverable_data():
    text = read_runbook()

    assert "WorkBaton ciphertext and metadata" in text
    assert "API key hashes and prefixes" in text
    assert "WorkThreads metadata, messages, tasks, and runs" in text
    assert "WorkBaton plaintext without the user's local client key" in text
    assert "lost local client key" in text
    assert "expired or was pruned before the backup point" in text
    assert "A2CR cannot recover client-encrypted WorkBaton bodies" in text


def test_disaster_recovery_runbook_defines_restore_drill_and_smoke_gates():
    text = read_runbook()

    assert "Restore Drill" in text
    assert "python scripts/check_migrations.py" in text
    assert "GET https://a2cr.app/api/v1/health/readiness" in text
    assert "python scripts/smoke_rls_pooler.py" in text
    assert "A2CR_SMOKE_USER_A_ID" in text
    assert "A2CR_SMOKE_USER_B_ID" in text
    assert "no DB URL, token, API key, password, or row content is printed" in text
    assert "dashboard/API/MCP smoke" in text
    assert "MCP save, resume, load, and delete with test data" in text
    assert "restored WorkBaton ciphertext can be loaded and locally decrypted" in text
    assert "RTO achieved" in text
    assert "RPO achieved" in text


def test_disaster_recovery_runbook_defines_rollback_and_forward_fix_rules():
    text = read_runbook()
    normalized = normalized_runbook()

    assert "Use Railway rollback when code or frontend assets are faulty" in text
    assert "Prefer forward-fix over rolling back database migrations" in text
    assert "backup point" in text
    assert "affected row count" in text
    assert "forward-fix plan" in text
    assert "run inside an explicit transaction where possible" in text
    assert "After migration recovery" in text
    assert "before reopening traffic" in normalized


def test_disaster_recovery_runbook_does_not_store_secret_values():
    text = read_runbook()
    forbidden = (
        "DATABASE_URL=",
        "postgresql://",
        "postgresql+psycopg://",
        "A2CR_APP_DB_PASSWORD",
        "SUPABASE_SERVICE_ROLE_KEY=",
        "Bearer sk-",
    )

    for snippet in forbidden:
        assert snippet not in text

    assert "Never commit or paste secrets" in text
    assert "`DATABASE_URL`" in text
    assert "`SUPABASE_SERVICE_ROLE_KEY`" in text
    assert "Authorization headers" in text
    assert "local client key material" in text
    assert "Do not record DB URLs, passwords, tokens, Authorization headers" in text
