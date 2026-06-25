from __future__ import annotations

import json
import re
import shutil
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import codex_config_path, local_db_path


_SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*(?:#.*)?$")
LOCAL_SERVER_NAME = "a2cr-local"
CLOUD_SERVER_NAME = "a2cr-cloud"
LEGACY_SERVER_NAME = "a2cr"
LOCAL_COMMAND = "a2cr-local-mcp"
CLOUD_COMMAND = "a2cr-cloud-mcp"


def toml_string(value: str | Path) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def render_codex_local_config(db_path: Path | None = None) -> str:
    path = (db_path or local_db_path()).expanduser()
    return (
        f'[mcp_servers."{LOCAL_SERVER_NAME}"]\n'
        f'command = "{LOCAL_COMMAND}"\n'
        "args = []\n\n"
        f'[mcp_servers."{LOCAL_SERVER_NAME}".env]\n'
        f"A2CR_LOCAL_DB = {toml_string(path)}\n"
    )


def render_codex_cloud_config(base_url: str | None = None) -> str:
    return (
        "# A2CR cloud/SaaS MCP setup has been discontinued.\n"
        "# Use the local workspace MCP config instead.\n"
        f"{render_codex_local_config()}"
    )


def inspect_codex_config(path: Path | None = None, *, profile: str = "local") -> dict[str, Any]:
    config_path = (path or codex_config_path()).expanduser()
    if not config_path.exists():
        return {
            "status": "warning",
            "path": str(config_path),
            "profile": profile,
            "message": f"Codex config file does not exist yet. Run `a2cr init codex --{profile}`.",
        }
    try:
        parsed = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        return {
            "status": "error",
            "path": str(config_path),
            "profile": profile,
            "message": f"Codex config is not valid TOML: {exc}",
        }

    if profile == "local":
        return _inspect_codex_local(parsed, config_path)
    if profile == "cloud":
        return {
            "status": "error",
            "path": str(config_path),
            "profile": "cloud",
            "server_name": CLOUD_SERVER_NAME,
            "message": "A2CR cloud/SaaS MCP setup has been discontinued. Use `a2cr init codex --local`.",
        }
    return {
        "status": "validation_error",
        "path": str(config_path),
        "profile": profile,
        "message": "profile must be local or cloud.",
    }


def _inspect_codex_local(parsed: dict[str, Any], config_path: Path) -> dict[str, Any]:
    servers = parsed.get("mcp_servers", {})
    server = servers.get(LOCAL_SERVER_NAME)
    if not isinstance(server, dict):
        legacy = _legacy_local_server(servers)
        if legacy:
            return {
                "status": "warning",
                "path": str(config_path),
                "profile": "local",
                "server_name": LEGACY_SERVER_NAME,
                "command": legacy.get("command"),
                "mode": legacy.get("env", {}).get("A2CR_MODE") if isinstance(legacy.get("env"), dict) else None,
                "message": "Legacy `a2cr` local MCP config exists. Run `a2cr init codex --local` to add `a2cr-local`.",
            }
        return {
            "status": "warning",
            "path": str(config_path),
            "profile": "local",
            "server_name": LOCAL_SERVER_NAME,
            "message": "Codex config has no MCP server named `a2cr-local`.",
        }
    command = server.get("command")
    env = server.get("env") if isinstance(server.get("env"), dict) else {}
    db = env.get("A2CR_LOCAL_DB")
    if command != LOCAL_COMMAND:
        return {
            "status": "warning",
            "path": str(config_path),
            "profile": "local",
            "server_name": LOCAL_SERVER_NAME,
            "command": command,
            "database_path": db,
            "message": "Codex has `a2cr-local`, but it does not use `a2cr-local-mcp`.",
        }
    return {
        "status": "ok",
        "path": str(config_path),
        "profile": "local",
        "server_name": LOCAL_SERVER_NAME,
        "command": command,
        "mode": "local",
        "database_path": db,
        "message": "Codex local MCP config is ready as `a2cr-local`.",
    }


def _inspect_codex_cloud(parsed: dict[str, Any], config_path: Path) -> dict[str, Any]:
    return {
        "status": "error",
        "path": str(config_path),
        "profile": "cloud",
        "server_name": CLOUD_SERVER_NAME,
        "message": "A2CR cloud/SaaS MCP setup has been discontinued. Use `a2cr init codex --local`.",
    }


def init_codex_local_config(
    *,
    path: Path | None = None,
    db_path: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    config_path = (path or codex_config_path()).expanduser()
    target_db = (db_path or local_db_path()).expanduser()
    block = render_codex_local_config(target_db)
    result = _init_codex_config(
        config_path=config_path,
        server_name=LOCAL_SERVER_NAME,
        remove_server_names={LOCAL_SERVER_NAME, CLOUD_SERVER_NAME},
        block=block,
        dry_run=dry_run,
        storage_mode="local",
    )
    result["database_path"] = str(target_db)
    return result


def init_codex_cloud_config(
    *,
    path: Path | None = None,
    base_url: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    return {
        "status": "error",
        "server_name": CLOUD_SERVER_NAME,
        "storage_mode": "local",
        "message": "A2CR cloud/SaaS MCP setup has been discontinued. Use `a2cr init codex --local`.",
    }


def _init_codex_config(
    *,
    config_path: Path,
    server_name: str,
    remove_server_names: set[str] | None = None,
    block: str,
    dry_run: bool,
    storage_mode: str,
) -> dict[str, Any]:
    existing = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    base_text, replaced = remove_existing_server_sections(existing, remove_server_names or {server_name})

    try:
        tomllib.loads(base_text or "")
    except tomllib.TOMLDecodeError as exc:
        return {
            "status": "error",
            "path": str(config_path),
            "server_name": server_name,
            "message": f"Codex config is not valid TOML outside the A2CR section: {exc}",
        }

    next_text = append_config_block(base_text, block)
    action = "replace" if replaced else "append" if existing else "create"
    result: dict[str, Any] = {
        "status": "dry_run" if dry_run else "configured",
        "action": action,
        "path": str(config_path),
        "server_name": server_name,
        "storage_mode": storage_mode,
        "backup_path": None,
        "config_block": block,
    }
    if dry_run:
        result["would_write"] = True
        return result

    backup_path = None
    if config_path.exists():
        backup_path = backup_config(config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(next_text, encoding="utf-8")
    result["backup_path"] = str(backup_path) if backup_path else None
    return result


def append_config_block(base_text: str, block: str) -> str:
    stripped = base_text.rstrip()
    if not stripped:
        return block
    return f"{stripped}\n\n{block}"


def remove_existing_a2cr_sections(text: str) -> tuple[str, bool]:
    return remove_existing_server_sections(text, {LOCAL_SERVER_NAME, CLOUD_SERVER_NAME})


def remove_existing_server_sections(text: str, server_names: set[str]) -> tuple[str, bool]:
    if not text:
        return "", False
    lines = text.splitlines(keepends=True)
    output: list[str] = []
    removed = False
    index = 0
    while index < len(lines):
        match = _SECTION_RE.match(lines[index])
        if match and is_a2cr_codex_header(match.group(1).strip(), server_names):
            removed = True
            index += 1
            while index < len(lines) and not _SECTION_RE.match(lines[index]):
                index += 1
            continue
        output.append(lines[index])
        index += 1
    return "".join(output).rstrip() + ("\n" if output else ""), removed


def is_a2cr_codex_header(header: str, server_names: set[str] | None = None) -> bool:
    names = server_names or {LOCAL_SERVER_NAME, CLOUD_SERVER_NAME}
    headers: set[str] = set()
    for name in names:
        headers.update({
            f'mcp_servers."{name}"',
            f'mcp_servers."{name}".env',
            f"mcp_servers.{name}",
            f"mcp_servers.{name}.env",
        })
    return header in headers


def _legacy_local_server(servers: Any) -> dict[str, Any] | None:
    if not isinstance(servers, dict):
        return None
    server = servers.get(LEGACY_SERVER_NAME)
    if not isinstance(server, dict):
        return None
    env = server.get("env") if isinstance(server.get("env"), dict) else {}
    if server.get("command") == "a2cr-mcp" and env.get("A2CR_MODE") == "local":
        return server
    return None


def backup_config(path: Path) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    candidate = path.with_name(f"{path.name}.a2cr-backup-{stamp}")
    suffix = 1
    while candidate.exists():
        candidate = path.with_name(f"{path.name}.a2cr-backup-{stamp}-{suffix}")
        suffix += 1
    shutil.copy2(path, candidate)
    return candidate
