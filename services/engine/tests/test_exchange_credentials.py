import os
import uuid

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from quantsail_engine.persistence.repository import EngineRepository
from quantsail_engine.persistence.stub_models import ExchangeKey
from quantsail_engine.security.encryption import EncryptionService


def _set_key(monkeypatch: pytest.MonkeyPatch, key_hex: str) -> None:
    monkeypatch.setenv("MASTER_KEY", key_hex)


def test_get_active_exchange_credentials_returns_none(
    in_memory_db, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_key(monkeypatch, "55" * 32)
    repo = EngineRepository(in_memory_db)
    service = EncryptionService()
    result = repo.get_active_exchange_credentials("binance", service)
    assert result is None


def test_get_active_exchange_credentials_returns_decrypted(
    in_memory_db, monkeypatch: pytest.MonkeyPatch
) -> None:
    key_hex = "33" * 32
    _set_key(monkeypatch, key_hex)
    repo = EngineRepository(in_memory_db)
    service = EncryptionService()

    aesgcm = AESGCM(bytes.fromhex(key_hex))
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, b"api-key:secret-key", None)

    key = ExchangeKey(
        id=uuid.uuid4(),
        exchange="binance",
        label="Primary",
        ciphertext=ciphertext,
        nonce=nonce,
        key_version=1,
        is_active=True,
        revoked_at=None,
    )
    in_memory_db.add(key)
    in_memory_db.commit()

    result = repo.get_active_exchange_credentials("binance", service)

    assert result is not None
    assert result.api_key == "api-key"
    assert result.secret_key == "secret-key"


def test_get_active_exchange_credentials_ignores_inactive(
    in_memory_db, monkeypatch: pytest.MonkeyPatch
) -> None:
    key_hex = "44" * 32
    _set_key(monkeypatch, key_hex)
    repo = EngineRepository(in_memory_db)
    service = EncryptionService()

    aesgcm = AESGCM(bytes.fromhex(key_hex))
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, b"api:secret", None)

    key = ExchangeKey(
        id=uuid.uuid4(),
        exchange="binance",
        label="Inactive",
        ciphertext=ciphertext,
        nonce=nonce,
        key_version=1,
        is_active=False,
        revoked_at=None,
    )
    in_memory_db.add(key)
    in_memory_db.commit()

    result = repo.get_active_exchange_credentials("binance", service)

    assert result is None