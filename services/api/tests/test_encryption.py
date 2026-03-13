import os
from unittest import mock

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.security.encryption import EncryptionService, get_encryption_service


@pytest.fixture
def valid_key_hex() -> str:
    # 32 bytes = 64 hex characters
    return os.urandom(32).hex()


def test_encryption_service_missing_key() -> None:
    with mock.patch.dict(os.environ, {}, clear=True):
        with pytest.raises(RuntimeError, match="MASTER_KEY environment variable is required"):
            EncryptionService()


def test_encryption_service_invalid_hex() -> None:
    with mock.patch.dict(os.environ, {"MASTER_KEY": "not-a-hex-string"}):
        with pytest.raises(RuntimeError, match="MASTER_KEY must be a valid hex string"):
            EncryptionService()


def test_encryption_service_invalid_length() -> None:
    # 16 bytes = 32 hex characters (not 32 bytes)
    short_key = os.urandom(16).hex()
    with mock.patch.dict(os.environ, {"MASTER_KEY": short_key}):
        with pytest.raises(RuntimeError, match="MASTER_KEY must be 32 bytes"):
            EncryptionService()


def test_encryption_service_valid_key(valid_key_hex: str) -> None:
    with mock.patch.dict(os.environ, {"MASTER_KEY": valid_key_hex}):
        service = EncryptionService()
        assert service.key == bytes.fromhex(valid_key_hex)
        assert isinstance(service.aesgcm, AESGCM)


def test_encrypt_decrypt(valid_key_hex: str) -> None:
    with mock.patch.dict(os.environ, {"MASTER_KEY": valid_key_hex}):
        service = EncryptionService()
        plaintext = "secret-api-key-123"

        ciphertext, nonce = service.encrypt(plaintext)

        # Ciphertext should not contain plaintext
        assert plaintext.encode("utf-8") not in ciphertext
        assert len(nonce) == 12

        decrypted = service.decrypt(ciphertext, nonce)
        assert decrypted == plaintext


def test_get_encryption_service_singleton(valid_key_hex: str) -> None:
    with mock.patch.dict(os.environ, {"MASTER_KEY": valid_key_hex}):
        # Reset the global variable for the test
        import app.security.encryption as enc_module

        enc_module._service = None

        service1 = get_encryption_service()
        service2 = get_encryption_service()

        assert service1 is service2
        assert isinstance(service1, EncryptionService)
