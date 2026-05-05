import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from cryptography.fernet import Fernet
from dotenv import load_dotenv

_APPDATA_DIR = Path(os.environ.get("APPDATA", Path.home()))
_DEFAULT_ENV_DIR = _APPDATA_DIR / "a2cr"
_LEGACY_ENV_DIR = _APPDATA_DIR / "ai_clipboard"


def _resolve_env_dir() -> Path:
    configured = os.environ.get("A2CR_HOME") or os.environ.get("AI_CLIPBOARD_HOME")
    if configured:
        return Path(configured)
    if (_LEGACY_ENV_DIR / ".env").exists():
        return _LEGACY_ENV_DIR
    return _DEFAULT_ENV_DIR


_ENV_DIR = _resolve_env_dir()
_ENV_PATH = _ENV_DIR / ".env"


def get_data_dir() -> Path:
    return _ENV_DIR


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
        f"DB_PATH={_ENV_DIR / 'a2cr.db'}\n",
        encoding="utf-8",
    )


@dataclass(frozen=True)
class Config:
    api_key: str
    fernet_key: str
    db_path: str


@dataclass(frozen=True)
class WebConfig:
    database_url: str
    fernet_key: str
    api_key_hash_secret: str
    supabase_jwt_secret: str | None
    supabase_jwks_url: str | None
    supabase_jwt_audience: str
    supabase_jwt_issuer: str | None
    a2cr_service_url: str
    app_env: str
    audit_hash_secret: str


_config: Config | None = None
_web_config: WebConfig | None = None


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
        db_path=os.environ.get("DB_PATH", str(_ENV_DIR / "a2cr.db")),
    )
    return _config


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def get_web_config() -> WebConfig:
    """Return Web SaaS runtime config without generating local secrets."""
    global _web_config
    if _web_config is not None:
        return _web_config

    if os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY must not be present in normal runtime")

    jwt_secret = _required_env("SUPABASE_JWT_SECRET")
    jwks_url = os.environ.get("SUPABASE_JWKS_URL")

    api_key_hash_secret = _required_env("API_KEY_HASH_SECRET")
    _web_config = WebConfig(
        database_url=_required_env("DATABASE_URL"),
        fernet_key=_required_env("FERNET_KEY"),
        api_key_hash_secret=api_key_hash_secret,
        supabase_jwt_secret=jwt_secret,
        supabase_jwks_url=jwks_url,
        supabase_jwt_audience=os.environ.get("SUPABASE_JWT_AUDIENCE", "authenticated"),
        supabase_jwt_issuer=os.environ.get("SUPABASE_JWT_ISSUER"),
        a2cr_service_url=_required_env("A2CR_SERVICE_URL"),
        app_env=_required_env("APP_ENV"),
        audit_hash_secret=os.environ.get("AUDIT_HASH_SECRET", api_key_hash_secret),
    )
    return _web_config


def reset_config() -> None:
    """For testing only."""
    global _config, _web_config
    _config = None
    _web_config = None
