from __future__ import annotations

import os
import sys
from pathlib import Path


def mode_from_env() -> str:
    return "local"


def local_db_path() -> Path:
    override = os.environ.get("A2CR_LOCAL_DB")
    if override:
        return Path(override).expanduser()
    if os.name == "nt":
        root = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(root) / "A2CR" / "a2cr.db"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "A2CR" / "a2cr.db"
    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home).expanduser() / "a2cr" / "a2cr.db"
    return Path.home() / ".local" / "share" / "a2cr" / "a2cr.db"


def codex_config_path() -> Path:
    override = os.environ.get("A2CR_CODEX_CONFIG")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".codex" / "config.toml"
