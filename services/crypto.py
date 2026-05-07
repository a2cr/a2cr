import os

from cryptography.fernet import Fernet


def _get_fernet(fernet_key: str | None = None) -> Fernet:
    key = fernet_key or os.environ.get("FERNET_KEY")
    if not key:
        raise RuntimeError("FERNET_KEY is required")
    return Fernet(key.encode())


def encrypt(plaintext: str, fernet_key: str | None = None) -> str:
    """Encrypt a UTF-8 string and return a base64url token string."""
    return _get_fernet(fernet_key).encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt(token: str, fernet_key: str | None = None) -> str:
    """Decrypt a Fernet token and return the original UTF-8 string."""
    return _get_fernet(fernet_key).decrypt(token.encode("utf-8")).decode("utf-8")
