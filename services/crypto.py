from cryptography.fernet import Fernet
from services.config import get_config


def _get_fernet() -> Fernet:
    return Fernet(get_config().fernet_key.encode())


def encrypt(plaintext: str) -> str:
    """Encrypt a UTF-8 string and return a base64url token string."""
    return _get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt(token: str) -> str:
    """Decrypt a Fernet token and return the original UTF-8 string."""
    return _get_fernet().decrypt(token.encode("utf-8")).decode("utf-8")
