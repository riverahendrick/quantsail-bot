import os

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from quantsail_engine.security.encryption import EncryptionService


def _set_key(monkeypatch: pytest.MonkeyPatch, key_hex: str) -> None:
    monkeypatch.setenv("MASTER_KEY", key_hex)


def test_encryption_service_requires_master_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MASTER_KEY", raising=False)
    with pytest.raises(RuntimeError):
        EncryptionService()


def test_encryption_service_invalid_hex(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_key(monkeypatch, "zz")
    with pytest.raises(RuntimeError):
        EncryptionService()


def test_encryption_service_invalid_length(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_key(monkeypatch, "00" * 16)
    with pytest.raises(RuntimeError):
        EncryptionService()


def test_encryption_service_decrypt_success(monkeypatch: pytest.MonkeyPatch) -> None:
    key_hex = "11" * 32
    _set_key(monkeypatch, key_hex)
    service = EncryptionService()

    aesgcm = AESGCM(bytes.fromhex(key_hex))
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, b"api:secret", None)

    creds = service.decrypt(ciphertext, nonce)

    assert creds.api_key == "api"
    assert creds.secret_key == "secret"


def test_encryption_service_invalid_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    key_hex = "22" * 32
    _set_key(monkeypatch, key_hex)
    service = EncryptionService()

    aesgcm = AESGCM(bytes.fromhex(key_hex))
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, b"invalid", None)

    with pytest.raises(RuntimeError):
        service.decrypt(ciphertext, nonce)
