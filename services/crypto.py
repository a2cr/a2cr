from cryptography.fernet import Fernet
from services.config import get_config


def _get_fernet(fernet_key: str | None = None) -> Fernet:
    return Fernet((fernet_key or get_config().fernet_key).encode())


def encrypt(plaintext: str, fernet_key: str | None = None) -> str:
    """Encrypt a UTF-8 string and return a base64url token string."""
    return _get_fernet(fernet_key).encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt(token: str, fernet_key: str | None = None) -> str:
    """Decrypt a Fernet token and return the original UTF-8 string."""
    return _get_fernet(fernet_key).decrypt(token.encode("utf-8")).decode("utf-8")
