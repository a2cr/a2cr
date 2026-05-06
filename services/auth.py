from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ec, utils
from cryptography.hazmat.primitives.hashes import SHA256
from sqlalchemy import text
from sqlalchemy.orm import Session

from services.config import WebConfig, get_web_config
from services.exceptions import AppError


class AuthError(AppError):
    def __init__(self):
        super().__init__("invalid_auth", "Invalid authentication credentials", 401)


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: UUID
    auth_method: Literal["jwt", "api_key"]


_jwks_cache: dict[str, dict[str, Any]] = {}


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode((value + padding).encode("ascii"))
    except (binascii.Error, ValueError) as exc:
        raise AuthError() from exc


def _json_from_b64(value: str) -> dict[str, Any]:
    try:
        decoded = _base64url_decode(value)
        data = json.loads(decoded.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuthError() from exc
    if not isinstance(data, dict):
        raise AuthError()
    return data


def _audience_matches(actual: Any, expected: str) -> bool:
    if isinstance(actual, str):
        return actual == expected
    if isinstance(actual, list):
        return expected in actual
    return False


def verify_supabase_jwt(
    token: str,
    *,
    config: WebConfig | None = None,
    now: datetime | None = None,
) -> AuthenticatedUser:
    config = config or get_web_config()
    parts = token.split(".")
    if len(parts) != 3:
        raise AuthError()

    header = _json_from_b64(parts[0])
    payload = _json_from_b64(parts[1])
    _verify_jwt_signature(parts, header, config)

    now_ts = int((now or datetime.now(timezone.utc)).timestamp())
    exp = payload.get("exp")
    if not isinstance(exp, int) or exp <= now_ts:
        raise AuthError()

    nbf = payload.get("nbf")
    if nbf is not None and (not isinstance(nbf, int) or nbf > now_ts):
        raise AuthError()

    if not _audience_matches(payload.get("aud"), config.supabase_jwt_audience):
        raise AuthError()

    if config.supabase_jwt_issuer and payload.get("iss") != config.supabase_jwt_issuer:
        raise AuthError()

    try:
        user_id = UUID(str(payload["sub"]))
    except (KeyError, ValueError) as exc:
        raise AuthError() from exc

    return AuthenticatedUser(user_id=user_id, auth_method="jwt")


def _verify_jwt_signature(parts: list[str], header: dict[str, Any], config: WebConfig) -> None:
    alg = header.get("alg")
    if alg == "HS256" and config.supabase_jwt_secret:
        _verify_hs256_signature(parts, config.supabase_jwt_secret)
        return
    if alg == "ES256" and config.supabase_jwks_url:
        _verify_es256_signature(parts, header, config.supabase_jwks_url)
        return
    raise AuthError()


def _verify_hs256_signature(parts: list[str], secret: str) -> None:
    signed = f"{parts[0]}.{parts[1]}".encode("ascii")
    expected_signature = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).digest()
    actual_signature = _base64url_decode(parts[2])
    if not hmac.compare_digest(actual_signature, expected_signature):
        raise AuthError()


def _load_jwks(jwks_url: str) -> dict[str, Any]:
    cached = _jwks_cache.get(jwks_url)
    if cached is not None:
        return cached
    try:
        response = httpx.get(jwks_url, timeout=5)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        raise AuthError() from exc
    if not isinstance(data, dict) or not isinstance(data.get("keys"), list):
        raise AuthError()
    _jwks_cache[jwks_url] = data
    return data


def _verify_es256_signature(parts: list[str], header: dict[str, Any], jwks_url: str) -> None:
    kid = header.get("kid")
    if not isinstance(kid, str):
        raise AuthError()
    jwks = _load_jwks(jwks_url)
    key = next((item for item in jwks["keys"] if item.get("kid") == kid), None)
    if key is None or key.get("kty") != "EC" or key.get("crv") != "P-256":
        raise AuthError()
    try:
        x = int.from_bytes(_base64url_decode(str(key["x"])), "big")
        y = int.from_bytes(_base64url_decode(str(key["y"])), "big")
        public_key = ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1()).public_key()
        raw_signature = _base64url_decode(parts[2])
    except (KeyError, ValueError) as exc:
        raise AuthError() from exc
    if len(raw_signature) != 64:
        raise AuthError()
    der_signature = utils.encode_dss_signature(
        int.from_bytes(raw_signature[:32], "big"),
        int.from_bytes(raw_signature[32:], "big"),
    )
    try:
        public_key.verify(der_signature, f"{parts[0]}.{parts[1]}".encode("ascii"), ec.ECDSA(SHA256()))
    except InvalidSignature as exc:
        raise AuthError() from exc


def hash_api_key(api_key: str, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), api_key.encode("utf-8"), hashlib.sha256).hexdigest()


def extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise AuthError()
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AuthError()
    return token


def authenticate_api_key(
    session: Session,
    authorization: str | None,
    *,
    ip_hash: str | None = None,
    config: WebConfig | None = None,
) -> AuthenticatedUser:
    config = config or get_web_config()
    api_key = extract_bearer_token(authorization)
    if not api_key.startswith("sk-"):
        raise AuthError()

    key_hash = hash_api_key(api_key, config.api_key_hash_secret)
    result = session.execute(
        text("SELECT app.resolve_api_key(:key_hash, :ip_hash)"),
        {"key_hash": key_hash, "ip_hash": ip_hash},
    )
    user_id = result.scalar_one_or_none()
    if user_id is None:
        raise AuthError()
    return AuthenticatedUser(user_id=UUID(str(user_id)), auth_method="api_key")
