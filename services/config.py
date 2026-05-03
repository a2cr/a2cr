import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from cryptography.fernet import Fernet
from dotenv import load_dotenv

_ENV_DIR = Path(os.environ.get("APPDATA", Path.home())) / "ai_clipboard"
_ENV_PATH = _ENV_DIR / ".env"


def _ensure_env_file() -> None:
    """Generate .env with random keys if it does not exist."""
    if _ENV_PATH.exists():
        return
    _ENV_DIR.mkdir(parents=True, exist_ok=True)
    api_key = "sk-" + secrets.token_hex(32)
    fernet_key = Fernet.generate_key().decode()
    _ENV_PATH.write_text(
        f"API_KEY={api_key}\n"
        f"FERNET_KEY={fernet_key}\n"
        f"DB_PATH={_ENV_DIR / 'ai_clipboard.db'}\n",
        encoding="utf-8",
    )


@dataclass(frozen=True)
class Config:
    api_key: str
    fernet_key: str
    db_path: str


_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is not None:
        return _config

    # In tests, env vars are injected via monkeypatch before this runs.
    # In production, load from .env file.
    if not os.environ.get("API_KEY"):
        _ensure_env_file()
        load_dotenv(_ENV_PATH)

    _config = Config(
        api_key=os.environ["API_KEY"],
        fernet_key=os.environ["FERNET_KEY"],
        db_path=os.environ.get("DB_PATH", str(_ENV_DIR / "ai_clipboard.db")),
    )
    return _config


def reset_config() -> None:
    """For testing only."""
    global _config
    _config = None
