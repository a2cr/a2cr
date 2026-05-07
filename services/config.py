import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from cryptography.fernet import Fernet
from dotenv import load_dotenv

_WEB_RUNTIME_ENVS = {"production", "staging"}
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
    public_api_key_prefix: str
    db_pool_size: int = 5
    db_max_overflow: int = 5
    db_pool_timeout_seconds: float = 5.0
    db_pool_recycle_seconds: int = 1800
    db_statement_timeout_ms: int = 8000
    db_lock_timeout_ms: int = 2000
    db_idle_transaction_timeout_ms: int = 10000


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


def _int_env(name: str, default: int) -> int:
    value = os.environ.get(name)
    return int(value) if value else default


def _float_env(name: str, default: float) -> float:
    value = os.environ.get(name)
    return float(value) if value else default


def app_env() -> str:
    return os.environ.get("APP_ENV", "development").strip().lower() or "development"


def is_web_runtime() -> bool:
    return app_env() in _WEB_RUNTIME_ENVS or os.environ.get("A2CR_WEB_RUNTIME") == "1"


def _reject_runtime_service_role_key() -> None:
    if os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY must not be present in normal runtime")


def _origin_from_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _configured_allowed_origins() -> set[str]:
    explicit = os.environ.get("A2CR_ALLOWED_ORIGINS")
    if explicit:
        return {origin.strip().rstrip("/") for origin in explicit.split(",") if origin.strip()}

    public_origin = os.environ.get("A2CR_PUBLIC_ORIGIN")
    derived = _origin_from_url(public_origin) or _origin_from_url(os.environ.get("A2CR_SERVICE_URL"))
    return {derived.rstrip("/")} if derived else set()


def should_enforce_same_origin() -> bool:
    return app_env() in _WEB_RUNTIME_ENVS or os.environ.get("A2CR_ENFORCE_SAME_ORIGIN") == "1"


def is_request_origin_allowed(origin: str | None) -> bool:
    if not origin or not should_enforce_same_origin():
        return True
    return origin.rstrip("/") in _configured_allowed_origins()


def _validate_fernet_key(value: str) -> None:
    try:
        Fernet(value.encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise RuntimeError("FERNET_KEY must be a valid Fernet key") from exc


def _validate_production_secret(name: str, value: str) -> None:
    if app_env() == "production" and len(value) < 32:
        raise RuntimeError(f"{name} must be at least 32 characters in production")


def get_web_config() -> WebConfig:
    """Return Web SaaS runtime config without generating local secrets."""
    global _web_config
    if _web_config is not None:
        return _web_config

    _reject_runtime_service_role_key()

    jwt_secret = os.environ.get("SUPABASE_JWT_SECRET")
    jwks_url = os.environ.get("SUPABASE_JWKS_URL")
    if not jwt_secret and not jwks_url:
        raise RuntimeError("SUPABASE_JWT_SECRET or SUPABASE_JWKS_URL is required")

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
        public_api_key_prefix=os.environ.get("A2CR_API_KEY_PREFIX", "sk-a2cr"),
        db_pool_size=_int_env("A2CR_DB_POOL_SIZE", 5),
        db_max_overflow=_int_env("A2CR_DB_MAX_OVERFLOW", 5),
        db_pool_timeout_seconds=_float_env("A2CR_DB_POOL_TIMEOUT_SECONDS", 5.0),
        db_pool_recycle_seconds=_int_env("A2CR_DB_POOL_RECYCLE_SECONDS", 1800),
        db_statement_timeout_ms=_int_env("A2CR_DB_STATEMENT_TIMEOUT_MS", 8000),
        db_lock_timeout_ms=_int_env("A2CR_DB_LOCK_TIMEOUT_MS", 2000),
        db_idle_transaction_timeout_ms=_int_env("A2CR_DB_IDLE_TRANSACTION_TIMEOUT_MS", 10000),
    )
    return _web_config


def validate_runtime_environment() -> WebConfig | None:
    """Fail fast for unsafe production/runtime environment choices."""
    _reject_runtime_service_role_key()
    if not is_web_runtime():
        return None

    config = get_web_config()
    _validate_fernet_key(config.fernet_key)
    _validate_production_secret("API_KEY_HASH_SECRET", config.api_key_hash_secret)
    _validate_production_secret("AUDIT_HASH_SECRET", config.audit_hash_secret)

    if app_env() == "production":
        parsed_service_url = urlparse(config.a2cr_service_url)
        public_origin = _origin_from_url(config.a2cr_service_url)
        if public_origin is None or not public_origin.startswith("https://"):
            raise RuntimeError("A2CR_SERVICE_URL must be an HTTPS public URL in production")
        if parsed_service_url.hostname in {"localhost", "127.0.0.1"}:
            raise RuntimeError("A2CR_SERVICE_URL must not point to localhost in production")
        for origin in _configured_allowed_origins():
            parsed_origin = urlparse(origin)
            if parsed_origin.scheme != "https" or parsed_origin.hostname in {"localhost", "127.0.0.1"}:
                raise RuntimeError("Allowed production origins must be HTTPS public origins")

    return config


def reset_config() -> None:
    """For testing only."""
    global _config, _web_config
    _config = None
    _web_config = None
