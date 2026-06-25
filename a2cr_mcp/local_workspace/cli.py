from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path

from .codex_config import (
    LOCAL_COMMAND,
    init_codex_local_config,
    inspect_codex_config,
    render_codex_local_config,
)
from .config import local_db_path
from .db import connect
from .store import LocalWorkspaceStore, get_store
from .ui import serve_ui


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="a2cr")
    sub = parser.add_subparsers(dest="command", required=True)

    status = sub.add_parser("status")
    status.add_argument("--db", type=Path)

    doctor = sub.add_parser("doctor")
    doctor.add_argument("--config", type=Path, help="Codex config.toml path.")
    doctor.add_argument("--db", type=Path, help="Local SQLite database path.")
    doctor.add_argument("--target", choices=["local"], default="local")

    init = sub.add_parser("init")
    init_sub = init.add_subparsers(dest="client", required=True)
    init_codex = init_sub.add_parser("codex")
    init_codex.add_argument("--local", action="store_true", help="Configure Codex to use local A2CR.")
    init_codex.add_argument("--cloud", action="store_true", help=argparse.SUPPRESS)
    init_codex.add_argument("--dry-run", action="store_true", help="Show planned changes without writing files.")
    init_codex.add_argument("--print-config", action="store_true", help="Print only the Codex TOML block.")
    init_codex.add_argument("--config", type=Path, help="Codex config.toml path.")
    init_codex.add_argument("--db", type=Path, help="Local SQLite database path.")
    init_codex.add_argument("--base-url", help=argparse.SUPPRESS)
    init_codex.add_argument("--force", action="store_true", help=argparse.SUPPRESS)

    search = sub.add_parser("search")
    search.add_argument("query", nargs="?", default="")
    search.add_argument("--type", choices=["WorkBaton", "WorkStash", "WorkThread", "Event"])
    search.add_argument("--limit", type=int, default=10)
    search.add_argument("--project")
    search.add_argument("--tag")
    search.add_argument("--state", choices=["open", "closed", "archived"])
    search.add_argument("--agent")
    search.add_argument("--date-from")
    search.add_argument("--date-to")
    search.add_argument("--slot")
    search.add_argument("--db", type=Path)

    ui = sub.add_parser("ui", help="Open the local browser dashboard.")
    ui.add_argument(
        "--host",
        default="127.0.0.1",
        help="Loopback host for the UI. Only 127.0.0.1 or localhost are allowed.",
    )
    ui.add_argument(
        "--port",
        type=int,
        default=0,
        help="Local port. Use 0 to choose an available port.",
    )
    ui.add_argument("--db", type=Path, help="Local SQLite database path.")
    ui.add_argument("--no-browser", action="store_true", help="Print the token URL without opening a browser.")
    ui.add_argument("--token", help=argparse.SUPPRESS)

    args = parser.parse_args(argv)

    if args.command == "status":
        return _print_json(build_status(args.db))
    if args.command == "doctor":
        report = build_doctor_report(config_path=args.config, db_path=args.db, target=args.target)
        _print_json(report)
        return 0 if report["ok"] else 1
    if args.command == "init" and args.client == "codex":
        if args.cloud:
            parser.error("A2CR cloud/SaaS setup has been discontinued. Run `a2cr init codex --local`.")
        if args.print_config:
            print(render_codex_local_config(args.db), end="")
            return 0
        result = init_codex_local_config(
            path=args.config,
            db_path=args.db,
            dry_run=args.dry_run,
        )
        _print_json(result)
        return 0 if result["status"] != "error" else 1
    elif args.command == "search":
        store = LocalWorkspaceStore(args.db) if args.db else get_store()
        return _print_json(store.search_contexts(
            args.query,
            object_type=args.type,
            limit=args.limit,
            project=args.project,
            tag=args.tag,
            state=args.state,
            agent=args.agent,
            date_from=args.date_from,
            date_to=args.date_to,
            slot=args.slot,
        ))
    if args.command == "ui":
        serve_ui(
            host=args.host,
            port=args.port,
            db_path=args.db,
            open_browser=not args.no_browser,
            token=args.token,
        )
        return 0
    return 1


def _print_json(data: dict) -> int:
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


def build_status(db_path: Path | None = None) -> dict:
    path = (db_path or local_db_path()).expanduser()
    with connect(path) as conn:
        counts = {
            "workbatons": conn.execute("SELECT COUNT(*) AS count FROM workbatons").fetchone()["count"],
            "workstash_entries": conn.execute("SELECT COUNT(*) AS count FROM workstash_entries").fetchone()["count"],
            "workthreads": conn.execute("SELECT COUNT(*) AS count FROM workthreads").fetchone()["count"],
        }
        last_baton = conn.execute("SELECT MAX(updated_at) AS value FROM workbatons").fetchone()["value"]
        schema_version = conn.execute(
            "SELECT value FROM settings WHERE key = 'schema_version'"
        ).fetchone()["value"]
    return {
        "status": "ok",
        "storage_mode": "local",
        "mcp_mode_env": os.environ.get("A2CR_MODE", "").strip().lower() or "unset",
        "database_path": str(path),
        "schema_version": schema_version,
        "counts": counts,
        "last_workbaton_at": last_baton,
    }


def build_doctor_report(
    *,
    config_path: Path | None = None,
    db_path: Path | None = None,
    target: str = "local",
) -> dict:
    checks = [check_python_version()]
    if target in {"local", "all"}:
        checks.extend([
            check_mcp_command(LOCAL_COMMAND),
            check_database(db_path),
            {"name": "codex_local_config", **inspect_codex_config(config_path, profile="local")},
        ])
        checks.append(check_local_mode_selection(checks[-1]))
    error_count = sum(1 for check in checks if check["status"] == "error")
    warning_count = sum(1 for check in checks if check["status"] == "warning")
    return {
        "status": "ok" if not error_count and not warning_count else "warning" if not error_count else "error",
        "ok": error_count == 0,
        "ready": error_count == 0 and warning_count == 0,
        "target": target,
        "storage_mode": "local",
        "database_path": str((db_path or local_db_path()).expanduser()),
        "checks": checks,
    }


def check_python_version() -> dict:
    version = sys.version_info
    ok = (3, 12) <= (version.major, version.minor) < (3, 15)
    return {
        "name": "python",
        "status": "ok" if ok else "error",
        "version": sys.version.split()[0],
        "message": "Python version is supported." if ok else "A2CR requires Python >=3.12,<3.15.",
    }


def check_mcp_command(command_name: str = LOCAL_COMMAND) -> dict:
    command = shutil.which(command_name)
    module_available = importlib.util.find_spec("a2cr_mcp.server") is not None
    if command:
        return {
            "name": f"{command_name}_command",
            "status": "ok",
            "command": command,
            "message": f"`{command_name}` is available on PATH.",
        }
    if module_available:
        return {
            "name": f"{command_name}_command",
            "status": "warning",
            "command": None,
            "message": f"`{command_name}` is not on PATH, but the Python module is importable.",
        }
    return {
        "name": f"{command_name}_command",
        "status": "error",
        "command": None,
        "message": f"`{command_name}` is not available. Install with `python -m pip install a2cr-mcp`.",
    }


def check_database(db_path: Path | None = None) -> dict:
    path = (db_path or local_db_path()).expanduser()
    try:
        with connect(path) as conn:
            schema_version = conn.execute(
                "SELECT value FROM settings WHERE key = 'schema_version'"
            ).fetchone()["value"]
    except OSError as exc:
        return {
            "name": "database",
            "status": "error",
            "path": str(path),
            "message": f"Could not open local database: {exc}",
        }
    return {
        "name": "database",
        "status": "ok",
        "path": str(path),
        "schema_version": schema_version,
        "message": "Local SQLite database is ready.",
    }


def check_local_mode_selection(config_check: dict) -> dict:
    env_mode = os.environ.get("A2CR_MODE")
    if env_mode and env_mode.strip().lower() == "local":
        return {
            "name": "local_mode_selection",
            "status": "ok",
            "message": "Current process has A2CR_MODE=local.",
        }
    if config_check.get("status") == "ok" and config_check.get("server_name") == "a2cr-local":
        return {
            "name": "local_mode_selection",
            "status": "ok",
            "message": "Codex config will start `a2cr-local` through `a2cr-local-mcp`.",
        }
    return {
        "name": "local_mode_selection",
        "status": "warning",
        "message": "Run `a2cr init codex --local` so Codex uses the dedicated `a2cr-local` MCP.",
    }


if __name__ == "__main__":
    raise SystemExit(main())
