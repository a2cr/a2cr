import json
from pathlib import Path

from a2cr_mcp.local_workspace import cli


def read_json(capsys):
    return json.loads(capsys.readouterr().out)


def test_init_codex_local_dry_run_does_not_write_config(tmp_path, capsys):
    config = tmp_path / "config.toml"
    db = tmp_path / "a2cr.db"

    code = cli.main([
        "init",
        "codex",
        "--local",
        "--dry-run",
        "--config",
        str(config),
        "--db",
        str(db),
    ])

    result = read_json(capsys)
    assert code == 0
    assert result["status"] == "dry_run"
    assert result["action"] == "create"
    assert result["would_write"] is True
    assert result["database_path"] == str(db)
    assert '[mcp_servers."a2cr-local"]' in result["config_block"]
    assert 'command = "a2cr-local-mcp"' in result["config_block"]
    assert not config.exists()


def test_init_codex_local_replaces_existing_a2cr_local_section_with_backup(tmp_path, capsys):
    config = tmp_path / "config.toml"
    db = tmp_path / "a2cr.db"
    config.write_text(
        '[profiles.default]\n'
        'model = "gpt-5"\n\n'
        '[mcp_servers."a2cr-local"]\n'
        'command = "old-a2cr-local"\n\n'
        '[mcp_servers."a2cr-local".env]\n'
        'A2CR_LOCAL_DB = "old.db"\n',
        encoding="utf-8",
    )

    code = cli.main([
        "init",
        "codex",
        "--local",
        "--config",
        str(config),
        "--db",
        str(db),
    ])

    result = read_json(capsys)
    text = config.read_text(encoding="utf-8")
    assert code == 0
    assert result["status"] == "configured"
    assert result["action"] == "replace"
    assert result["backup_path"]
    assert 'model = "gpt-5"' in text
    assert '[mcp_servers."a2cr-local"]' in text
    assert 'command = "a2cr-local-mcp"' in text
    assert "old-a2cr-local" not in text
    assert "old-a2cr-local" in Path(result["backup_path"]).read_text(encoding="utf-8")


def test_init_codex_cloud_flag_is_discontinued(tmp_path, capsys):
    config = tmp_path / "config.toml"

    try:
        cli.main([
            "init",
            "codex",
            "--cloud",
            "--dry-run",
            "--config",
            str(config),
            "--base-url",
            "https://a2cr.example",
        ])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("--cloud should exit through argparse")

    assert "cloud/SaaS setup has been discontinued" in capsys.readouterr().err
    assert not config.exists()


def test_doctor_reports_ready_after_codex_local_init(tmp_path, capsys, monkeypatch):
    config = tmp_path / "config.toml"
    db = tmp_path / "a2cr.db"
    cli.main([
        "init",
        "codex",
        "--local",
        "--config",
        str(config),
        "--db",
        str(db),
    ])
    capsys.readouterr()
    monkeypatch.setattr(cli.shutil, "which", lambda command: "/bin/a2cr-local-mcp" if command == "a2cr-local-mcp" else None)

    code = cli.main(["doctor", "--config", str(config), "--db", str(db)])

    result = read_json(capsys)
    checks = {check["name"]: check for check in result["checks"]}
    assert code == 0
    assert result["ok"] is True
    assert result["ready"] is True
    assert checks["database"]["status"] == "ok"
    assert checks["codex_local_config"]["status"] == "ok"
    assert checks["codex_local_config"]["server_name"] == "a2cr-local"
    assert checks["local_mode_selection"]["status"] == "ok"


def test_status_creates_and_reports_local_database(tmp_path, capsys):
    db = tmp_path / "a2cr.db"

    code = cli.main(["status", "--db", str(db)])

    result = read_json(capsys)
    assert code == 0
    assert result["status"] == "ok"
    assert result["database_path"] == str(db)
    assert result["counts"] == {
        "workbatons": 0,
        "workstash_entries": 0,
        "workthreads": 0,
    }
    assert db.exists()
