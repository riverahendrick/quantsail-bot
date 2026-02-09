from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from app.db.models import ExchangeKey, User
from app.main import app
from app.public.rate_limit import reset_rate_limiter


class DummyEncryption:
    def encrypt(self, plaintext: str) -> tuple[bytes, bytes]:
        return b"cipher", b"nonce"


def _authorized_client(
    engine: sa.Engine, monkeypatch: pytest.MonkeyPatch, role: str = "OWNER"
) -> TestClient:
    reset_rate_limiter()
    email = f"{role.lower()}@example.com"
    with engine.begin() as conn:
        conn.execute(sa.insert(User).values(id=uuid.uuid4(), email=email, role=role))

    def _verify(_: str) -> dict[str, str]:
        return {"uid": "firebase-uid", "email": email}

    monkeypatch.setattr("app.auth.dependencies.verify_firebase_token", _verify)
    return TestClient(app, headers={"Authorization": "Bearer token"})


def _insert_key(engine: sa.Engine, label: str, active: bool = True) -> uuid.UUID:
    key_id = uuid.uuid4()
    with engine.begin() as conn:
        conn.execute(
            sa.insert(ExchangeKey).values(
                id=key_id,
                exchange="binance",
                label=label,
                ciphertext=b"cipher",
                nonce=b"nonce",
                key_version=1,
                is_active=active,
            )
        )
    return key_id


def test_add_key_deactivates_existing(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _authorized_client(migrated_engine, monkeypatch)
    monkeypatch.setattr("app.api.private.get_encryption_service", lambda: DummyEncryption())

    # First key
    response = client.post(
        "/v1/exchanges/binance/keys",
        json={"label": "Primary", "api_key": "k1", "secret_key": "s1"},
    )
    assert response.status_code == 200
    first_id = response.json()["id"]

    # Second key should deactivate first
    response = client.post(
        "/v1/exchanges/binance/keys",
        json={"label": "Secondary", "api_key": "k2", "secret_key": "s2"},
    )
    assert response.status_code == 200
    second_id = response.json()["id"]

    with migrated_engine.connect() as conn:
        first = (
            conn.execute(sa.select(ExchangeKey).where(ExchangeKey.id == uuid.UUID(first_id)))
            .mappings()
            .one()
        )
        second = (
            conn.execute(sa.select(ExchangeKey).where(ExchangeKey.id == uuid.UUID(second_id)))
            .mappings()
            .one()
        )

    assert first["is_active"] is False
    assert second["is_active"] is True


def test_revoke_key_soft_delete(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _authorized_client(migrated_engine, monkeypatch)
    key_id = _insert_key(migrated_engine, label="Key")

    response = client.delete(f"/v1/exchanges/binance/keys/{key_id}")

    assert response.status_code == 200
    with migrated_engine.connect() as conn:
        row = conn.execute(sa.select(ExchangeKey).where(ExchangeKey.id == key_id)).mappings().one()
    assert row["revoked_at"] is not None
    assert row["is_active"] is False


def test_get_key_status_includes_active_flag(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _authorized_client(migrated_engine, monkeypatch)
    key_id = _insert_key(migrated_engine, label="Key", active=True)

    response = client.get("/v1/exchanges/binance/keys/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["id"] == str(key_id)
    assert payload[0]["is_active"] is True


def test_update_key_label_and_rotate(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _authorized_client(migrated_engine, monkeypatch)
    monkeypatch.setattr("app.api.private.get_encryption_service", lambda: DummyEncryption())

    key_id = _insert_key(migrated_engine, label="Old")

    response = client.patch(
        f"/v1/exchanges/binance/keys/{key_id}",
        json={"label": "New", "api_key": "k3", "secret_key": "s3"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["label"] == "New"

    with migrated_engine.connect() as conn:
        row = conn.execute(sa.select(ExchangeKey).where(ExchangeKey.id == key_id)).mappings().one()
    assert row["key_version"] == 2
    assert row["ciphertext"] == b"cipher"


def test_update_key_no_fields_returns_error(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _authorized_client(migrated_engine, monkeypatch)
    key_id = _insert_key(migrated_engine, label="Key")

    response = client.patch(f"/v1/exchanges/binance/keys/{key_id}", json={})

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_UPDATE"


def test_update_key_requires_api_and_secret(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _authorized_client(migrated_engine, monkeypatch)
    key_id = _insert_key(migrated_engine, label="Key")

    response = client.patch(f"/v1/exchanges/binance/keys/{key_id}", json={"api_key": "only"})

    assert response.status_code == 400


def test_activate_key_switches_active(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _authorized_client(migrated_engine, monkeypatch)

    first_id = _insert_key(migrated_engine, label="Key A", active=True)
    second_id = _insert_key(migrated_engine, label="Key B", active=False)

    response = client.post(f"/v1/exchanges/binance/keys/{second_id}/activate")

    assert response.status_code == 200
    with migrated_engine.connect() as conn:
        first = (
            conn.execute(sa.select(ExchangeKey).where(ExchangeKey.id == first_id)).mappings().one()
        )
        second = (
            conn.execute(sa.select(ExchangeKey).where(ExchangeKey.id == second_id)).mappings().one()
        )
    assert first["is_active"] is False
    assert second["is_active"] is True


def test_activate_key_rejected_when_revoked(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _authorized_client(migrated_engine, monkeypatch)
    key_id = _insert_key(migrated_engine, label="Key", active=False)

    with migrated_engine.begin() as conn:
        conn.execute(
            sa.update(ExchangeKey)
            .where(ExchangeKey.id == key_id)
            .values(revoked_at=datetime.now(timezone.utc), is_active=False)
        )

    response = client.post(f"/v1/exchanges/binance/keys/{key_id}/activate")

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "KEY_REVOKED"


def test_update_key_invalid_id(migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _authorized_client(migrated_engine, monkeypatch)

    response = client.patch("/v1/exchanges/binance/keys/not-a-uuid", json={"label": "X"})

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_ID"


def test_update_key_not_found(migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _authorized_client(migrated_engine, monkeypatch)
    missing_id = uuid.uuid4()

    response = client.patch(f"/v1/exchanges/binance/keys/{missing_id}", json={"label": "X"})

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "NOT_FOUND"


def test_revoke_key_invalid_id(migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _authorized_client(migrated_engine, monkeypatch)

    response = client.delete("/v1/exchanges/binance/keys/not-a-uuid")

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_ID"


def test_activate_key_not_found(
    migrated_engine: sa.Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _authorized_client(migrated_engine, monkeypatch)
    missing_id = uuid.uuid4()

    response = client.post(f"/v1/exchanges/binance/keys/{missing_id}/activate")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "NOT_FOUND"
