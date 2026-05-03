from services.crypto import encrypt, decrypt


def test_encrypt_returns_bytes_string():
    result = encrypt("hello world")
    assert isinstance(result, str)
    assert result != "hello world"


def test_decrypt_roundtrip():
    plaintext = '{"goal": "test", "current_state": "ok", "next_action": "go"}'
    encrypted = encrypt(plaintext)
    assert decrypt(encrypted) == plaintext


def test_encrypt_different_each_time():
    plaintext = "same input"
    enc1 = encrypt(plaintext)
    enc2 = encrypt(plaintext)
    assert enc1 != enc2  # Fernet uses random IV


def test_decrypt_wrong_key_raises(monkeypatch):
    import os
    from cryptography.fernet import Fernet
    plaintext = "secret"
    encrypted = encrypt(plaintext)

    # Swap to a different key
    monkeypatch.setenv("FERNET_KEY", Fernet.generate_key().decode())
    import services.config as config_module
    config_module.reset_config()

    import pytest
    with pytest.raises(Exception):
        decrypt(encrypted)
